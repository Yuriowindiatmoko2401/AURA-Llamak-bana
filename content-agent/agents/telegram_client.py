try:
    from telegram import Bot, InputFile
    from telegram.request import BaseRequest, HTTPXRequest
except ImportError:
    # Fallback for older versions
    from telegram import Bot, InputFile
import os
import requests
from typing import Dict, Any, Optional, List
import io
from datetime import datetime
import asyncio

class TelegramClient:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment variables")

        # Initialize bot without session to avoid async issues
        self.bot = None
        self._chat_id = int(self.chat_id) if self.chat_id.lstrip('-').isdigit() else self.chat_id

    async def _get_bot(self):
        """Get bot instance asynchronously"""
        if self.bot is None:
            # Simple bot initialization - works with updated python-telegram-bot
            self.bot = Bot(token=self.bot_token)
        return self.bot

    def _validate_chat_id(self):
        """Validate that chat_id is not trying to message another bot"""
        if isinstance(self._chat_id, int) and self._chat_id < 0:
            # Negative chat IDs are channels/groups, check if it's a bot
            chat_id_str = str(abs(self._chat_id))
            if chat_id_str.startswith('1') and len(chat_id_str) >= 9:
                print(f"⚠️  Warning: Chat ID {self._chat_id} appears to be a bot. Bots cannot message other bots.")
                return False
        return True

    async def send_text_post(self, caption: str, hashtags: List[str]) -> Dict[str, Any]:
        """
        Send a text-only post to Telegram

        Args:
            caption: The post caption
            hashtags: List of hashtags to include

        Returns:
            Result dictionary with status and message info
        """
        try:
            # Validate chat ID
            if not self._validate_chat_id():
                return {
                    'status': 'error',
                    'error': 'Invalid chat ID: bots cannot send messages to other bots',
                    'timestamp': datetime.now().isoformat(),
                    'content_type': 'text'
                }

            # Get bot instance
            bot = await self._get_bot()

            # Combine caption and hashtags
            hashtags_text = '\n\n' + ' '.join(hashtags) if hashtags else ''
            full_text = caption + hashtags_text

            # Truncate if too long (Telegram limit is 4096 characters)
            if len(full_text) > 4096:
                full_text = full_text[:4090] + "..."

            message = await bot.send_message(
                chat_id=self._chat_id,
                text=full_text,
                parse_mode='HTML',
                disable_web_page_preview=False
            )

            return {
                'status': 'success',
                'message_id': message.message_id,
                'timestamp': datetime.now().isoformat(),
                'content_type': 'text',
                'caption_length': len(caption),
                'hashtag_count': len(hashtags)
            }

        except Exception as e:
            error_msg = str(e)
            if "Forbidden: bots can't send messages to bots" in error_msg:
                error_msg = "Error: Your chat_id appears to be a bot. Please use a user chat_id, group chat_id, or channel username instead."
            return {
                'status': 'error',
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'content_type': 'text'
            }

    async def send_image_post(self, image_url: str, caption: str, hashtags: List[str]) -> Dict[str, Any]:
        """
        Send an image post with caption to Telegram

        Args:
            image_url: URL of the image to send
            caption: The post caption
            hashtags: List of hashtags to include

        Returns:
            Result dictionary with status and message info
        """
        try:
            # Validate chat ID
            if not self._validate_chat_id():
                return {
                    'status': 'error',
                    'error': 'Invalid chat ID: bots cannot send messages to other bots',
                    'timestamp': datetime.now().isoformat(),
                    'content_type': 'photo'
                }

            # Get bot instance
            bot = await self._get_bot()

            # Download the image
            image_data = self._download_image(image_url)
            if not image_data:
                raise Exception("Failed to download image")

            # Combine caption and hashtags
            hashtags_text = '\n\n' + ' '.join(hashtags) if hashtags else ''
            full_caption = caption + hashtags_text

            # Truncate caption if too long (Telegram limit for captions is 1024 characters)
            if len(full_caption) > 1024:
                full_caption = full_caption[:1018] + "..."

            # Send photo with caption
            message = await bot.send_photo(
                chat_id=self._chat_id,
                photo=image_data,
                caption=full_caption,
                parse_mode='HTML'
            )

            return {
                'status': 'success',
                'message_id': message.message_id,
                'timestamp': datetime.now().isoformat(),
                'content_type': 'photo',
                'image_url': image_url,
                'caption_length': len(caption),
                'hashtag_count': len(hashtags)
            }

        except Exception as e:
            error_msg = str(e)
            if "Forbidden: bots can't send messages to bots" in error_msg:
                error_msg = "Error: Your chat_id appears to be a bot. Please use a user chat_id, group chat_id, or channel username instead."
            return {
                'status': 'error',
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'content_type': 'photo',
                'image_url': image_url
            }

    async def send_media_group(self, media_items: List[Dict[str, Any]], caption: str) -> Dict[str, Any]:
        """
        Send a group of media items (photos/videos) with caption

        Args:
            media_items: List of media items with 'type' and 'url' keys
            caption: Caption for the media group

        Returns:
            Result dictionary with status and message info
        """
        try:
            media_group = []

            for item in media_items[:10]:  # Telegram limit is 10 items per group
                if item.get('type') == 'photo':
                    image_data = self._download_image(item['url'])
                    if image_data:
                        media_group.append(telegram.InputMediaPhoto(
                            media=image_data,
                            caption=''  # Individual captions not supported in groups
                        ))

            if not media_group:
                raise Exception("No valid media items to send")

            # Set caption on first media item
            if media_group and caption:
                media_group[0].caption = caption[:1024]  # Telegram caption limit

            messages = await self.bot.send_media_group(
                chat_id=self.chat_id,
                media=media_group
            )

            return {
                'status': 'success',
                'message_ids': [msg.message_id for msg in messages],
                'timestamp': datetime.now().isoformat(),
                'content_type': 'media_group',
                'items_sent': len(media_group),
                'caption_length': len(caption) if caption else 0
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'content_type': 'media_group'
            }

    async def send_poll(self, question: str, options: List[str], caption: str = "") -> Dict[str, Any]:
        """
        Send a poll to Telegram

        Args:
            question: Poll question
            options: List of poll options
            caption: Optional caption for the poll

        Returns:
            Result dictionary with status and poll info
        """
        try:
            full_text = caption + '\n\n' if caption else ''

            message = await self.bot.send_poll(
                chat_id=self.chat_id,
                question=question,
                options=options,
                is_anonymous=False,
                allows_multiple_answers=False
            )

            # Send caption as separate message if provided
            if caption:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=full_text,
                    parse_mode='HTML'
                )

            return {
                'status': 'success',
                'message_id': message.message_id,
                'timestamp': datetime.now().isoformat(),
                'content_type': 'poll',
                'question': question,
                'options_count': len(options)
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'content_type': 'poll'
            }

    def _download_image(self, image_url: str) -> Optional[io.BytesIO]:
        """Download image from URL and return as BytesIO object"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            image_data = io.BytesIO(response.content)
            image_data.name = 'image.jpg'  # Set a filename

            return image_data

        except Exception as e:
            print(f"Error downloading image from {image_url}: {e}")
            return None

    async def send_completion_notification(self, schedule_id: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a completion notification after a posting schedule finishes

        Args:
            schedule_id: ID of the completed schedule
            stats: Statistics about the completed schedule

        Returns:
            Result dictionary with status
        """
        try:
            # Get bot instance
            bot = await self._get_bot()

            completion_message = f"""
🎉 <b>Content Schedule Completed!</b>

📊 <b>Statistics:</b>
• Schedule ID: {schedule_id}
• Total Posts: {stats.get('total_posts', 0)}
• Successful: {stats.get('successful_posts', 0)}
• Failed: {stats.get('failed_posts', 0)}
• Success Rate: {stats.get('success_rate', 0):.1f}%

⏰ <b>Completed at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✨ Ready for the next schedule!
            """.strip()

            message = await bot.send_message(
                chat_id=self._chat_id,
                text=completion_message,
                parse_mode='HTML'
            )

            return {
                'status': 'success',
                'message_id': message.message_id,
                'timestamp': datetime.now().isoformat(),
                'notification_type': 'completion',
                'schedule_id': schedule_id
            }

        except Exception as e:
            error_msg = str(e)
            if "Forbidden: bots can't send messages to bots" in error_msg:
                error_msg = "Error: Your chat_id appears to be a bot. Please use a user chat_id, group chat_id, or channel username."
            return {
                'status': 'error',
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'notification_type': 'completion'
            }

    async def send_error_notification(self, error_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send an error notification

        Args:
            error_message: Error description
            context: Additional context about the error

        Returns:
            Result dictionary with status
        """
        try:
            # Get bot instance
            bot = await self._get_bot()

            context_text = ""
            if context:
                context_text = "\n".join([f"• {k}: {v}" for k, v in context.items()])

            error_msg = f"""
⚠️ <b>Error Notification</b>

🔴 <b>Error:</b> {error_message}

{context_text}

⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()

            message = await bot.send_message(
                chat_id=self._chat_id,
                text=error_msg,
                parse_mode='HTML'
            )

            return {
                'status': 'success',
                'message_id': message.message_id,
                'timestamp': datetime.now().isoformat(),
                'notification_type': 'error'
            }

        except Exception as e:
            error_msg = str(e)
            if "Forbidden: bots can't send messages to bots" in error_msg:
                error_msg = "Error: Your chat_id appears to be a bot. Please use a user chat_id, group chat_id, or channel username."
            return {
                'status': 'error',
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'notification_type': 'error'
            }

    async def send_status_update(self, status_text: str) -> Dict[str, Any]:
        """
        Send a status update message

        Args:
            status_text: Status information to send

        Returns:
            Result dictionary with status
        """
        try:
            # Get bot instance
            bot = await self._get_bot()

            message = await bot.send_message(
                chat_id=self._chat_id,
                text=f"📊 <b>Status Update</b>\n\n{status_text}",
                parse_mode='HTML'
            )

            return {
                'status': 'success',
                'message_id': message.message_id,
                'timestamp': datetime.now().isoformat(),
                'notification_type': 'status'
            }

        except Exception as e:
            error_msg = str(e)
            if "Forbidden: bots can't send messages to bots" in error_msg:
                error_msg = "Error: Your chat_id appears to be a bot. Please use a user chat_id, group chat_id, or channel username."
            return {
                'status': 'error',
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'notification_type': 'status'
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Test the Telegram bot connection"""
        try:
            # Validate chat ID
            if not self._validate_chat_id():
                return {
                    'status': 'error',
                    'error': 'Invalid chat ID: bots cannot send messages to other bots. Please use a user chat_id, group chat_id, or channel username.',
                    'timestamp': datetime.now().isoformat(),
                    'suggestion': 'Get your chat_id by messaging @userinfobot on Telegram'
                }

            # Get bot instance
            bot = await self._get_bot()

            message = await bot.send_message(
                chat_id=self._chat_id,
                text="🤖 <b>Bot Connection Test Successful!</b>\n\nThe automated content generation agent is ready to start posting.",
                parse_mode='HTML'
            )

            bot_info = await bot.get_me()

            return {
                'status': 'success',
                'message_id': message.message_id,
                'timestamp': datetime.now().isoformat(),
                'bot_info': {
                    'id': bot_info.id,
                    'username': bot_info.username,
                    'first_name': bot_info.first_name
                },
                'chat_info': {
                    'chat_id': self._chat_id,
                    'chat_type': 'user' if isinstance(self._chat_id, int) and self._chat_id > 0 else 'channel/group'
                }
            }

        except Exception as e:
            error_msg = str(e)
            if "Forbidden: bots can't send messages to bots" in error_msg:
                error_msg = "Error: Your chat_id appears to be a bot. Please use a user chat_id, group chat_id, or channel username."
            elif "chat not found" in error_msg.lower():
                error_msg = f"Chat {self._chat_id} not found. Make sure the bot has access to this chat."

            return {
                'status': 'error',
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'suggestion': 'Get your correct chat_id by messaging @userinfobot on Telegram'
            }

    def get_chat_info(self) -> Dict[str, Any]:
        """Get information about the configured chat"""
        try:
            chat = self.bot.get_chat(self.chat_id)
            return {
                'status': 'success',
                'chat_id': self.chat_id,
                'chat_type': chat.type,
                'chat_title': chat.title or 'Private Chat',
                'chat_username': chat.username
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'chat_id': self.chat_id
            }