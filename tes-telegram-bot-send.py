#!/usr/bin/env python3
import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot
import telegram

# Load environment variables
load_dotenv('content-agent/.env')

async def send_hello_message():
    """Send a simple Hello World message via Telegram bot"""

    # Get bot token and chat ID from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables")
        print("Please set up your .env file with your bot token from @BotFather")
        return

    if not chat_id:
        print("Error: TELEGRAM_CHAT_ID not found in environment variables")
        print("Please set up your .env file with your chat ID from @userinfobot")
        return

    try:
        # Initialize the bot
        bot = Bot(token=bot_token)

        # Send hello message
        message = "Hello World! \n\nThis is a test message from your Telegram bot!\n\n( Bot is working perfectly! ("

        print(f"Sending message to chat ID: {chat_id}")
        await bot.send_message(chat_id=chat_id, text=message)
        print("Message sent successfully!")

    except Exception as e:
        print(f"Error sending message: {e}")
        print("Please check your bot token and chat ID are correct")

if __name__ == "__main__":
    print("Starting Telegram Bot Test...")
    asyncio.run(send_hello_message())