import json
from typing import List, Dict, Any, Optional
import os
from agents.llm_wrappers import GeminiLLM, ZAILLM
from datetime import datetime, timedelta

class ContentPlanner:
    def __init__(self):
        self.llm = self._get_llm()

    def _get_llm(self):
        if os.getenv("CORE_AGENT_TYPE") == "gemini":
            return GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"))
        elif os.getenv("CORE_AGENT_TYPE") == "zai":
            return ZAILLM(api_key=os.getenv("ZAI_API_KEY"))
        else:
            raise ValueError("Unsupported CORE_AGENT_TYPE. Use 'gemini' or 'zai'.")

    def create_content_plan(self, trends: List[Dict[str, Any]], user_preferences: Dict[str, Any],
                          num_posts: int = 10) -> List[Dict[str, Any]]:
        """
        Create a comprehensive content plan based on trends and user preferences

        Args:
            trends: List of trending topics from trend researcher
            user_preferences: User's niche, keywords, and preferences
            num_posts: Number of posts to plan

        Returns:
            List of content plans with captions, hashtags, and image concepts
        """
        trends_summary = json.dumps(trends, indent=2)

        prompt = f"""
        As a content strategy specialist, create a detailed content plan based on these trends and user preferences.

        TRENDS DATA:
        {trends_summary}

        USER PREFERENCES:
        - Niche: {user_preferences.get('niche', 'general')}
        - Keywords: {user_preferences.get('keywords', [])}
        - Brand voice: {user_preferences.get('brand_voice', 'friendly and informative')}
        - Target audience: {user_preferences.get('target_audience', 'general')}

        Create {num_posts} diverse content posts. For each post, provide:
        1. An engaging caption (100-200 characters)
        2. 5-10 relevant hashtags (mix of popular and niche-specific)
        3. Keywords for SEO optimization
        4. A detailed concept for the accompanying image
        5. Content type (educational, entertaining, promotional, interactive)
        6. Call-to-action suggestion
        7. Best time to post (morning/afternoon/evening)

        Format your response as a JSON array with this structure:
        {{
            "caption": "Engaging caption text",
            "hashtags": ["#hashtag1", "#hashtag2"],
            "keywords": ["keyword1", "keyword2"],
            "image_concept": "Detailed description of the image to generate",
            "content_type": "educational/entertaining/promotional/interactive",
            "call_to_action": "CTA text",
            "best_time": "morning/afternoon/evening"
        }}
        """

        try:
            response = self.llm._call(prompt)
            content_plan = json.loads(response)
            return content_plan if isinstance(content_plan, list) else self._create_fallback_plan(num_posts)
        except json.JSONDecodeError:
            return self._create_fallback_plan(num_posts)
        except Exception as e:
            print(f"Error in content planning: {e}")
            return self._create_fallback_plan(num_posts)

    def _create_fallback_plan(self, num_posts: int) -> List[Dict[str, Any]]:
        """Create a fallback content plan if LLM fails"""
        plans = []
        for i in range(num_posts):
            plans.append({
                "caption": f"Discover something amazing today! 🚀 #innovation #discovery",
                "hashtags": ["#trending", "#innovation", "#daily", "#explore"],
                "keywords": ["innovation", "technology", "discovery"],
                "image_concept": "Modern, minimalist design showing innovation and progress",
                "content_type": "inspirational",
                "call_to_action": "What do you think? Share your thoughts! 👇",
                "best_time": "evening"
            })
        return plans

    def optimize_caption(self, caption: str, platform: str = "telegram") -> str:
        """Optimize caption for specific platform"""
        if platform.lower() == "telegram":
            # Telegram supports longer captions and rich formatting
            if len(caption) > 4096:  # Telegram limit
                caption = caption[:4090] + "..."
        elif platform.lower() == "instagram":
            # Instagram optimal length is around 125 characters
            if len(caption) > 2200:  # Instagram limit
                caption = caption[:2195] + "..."

        return caption

    def generate_hashtag_combinations(self, base_hashtags: List[str], niche: str) -> List[str]:
        """Generate hashtag combinations for better reach"""
        prompt = f"""
        Generate 15 optimized hashtags for content about: {niche}

        Base hashtags to build upon: {', '.join(base_hashtags)}

        Create a mix of:
        - High-volume popular hashtags
        - Medium-volume niche hashtags
        - Low-volume specific hashtags
        - Trending hashtags
        - Community hashtags

        Format as a JSON array of strings (without # symbols, they'll be added automatically).
        """

        try:
            response = self.llm._call(prompt)
            hashtags = json.loads(response)
            if isinstance(hashtags, list):
                return [f"#{tag.replace('#', '').replace(' ', '')}" for tag in hashtags[:15]]
        except:
            pass

        # Fallback hashtags
        return [f"#{niche.replace(' ', '')}", "#trending", "#viral", "#fyp", "#explore", "#daily"]

    def create_content_calendar(self, content_plan: List[Dict[str, Any]],
                             schedule_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a content calendar based on schedule parameters"""
        frequency = schedule_params.get('frequency', 'daily')
        duration = schedule_params.get('duration', '7 days')

        # Calculate number of posts needed
        if frequency == 'hourly':
            posts_per_day = 24
        elif frequency == 'twice_daily':
            posts_per_day = 2
        elif frequency == 'daily':
            posts_per_day = 1
        else:
            posts_per_day = 1

        days = int(duration.split()[0]) if duration.split()[0].isdigit() else 7
        total_posts = min(len(content_plan), posts_per_day * days)

        # Assign posts to specific dates/times
        calendar = []
        start_date = datetime.now()

        for i in range(total_posts):
            post_date = start_date + timedelta(hours=i * (24 // posts_per_day))
            calendar.append({
                **content_plan[i % len(content_plan)],
                'scheduled_date': post_date.isoformat(),
                'post_number': i + 1
            })

        return calendar

    def analyze_content_performance(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze potential performance of a content piece"""
        caption_length = len(content.get('caption', ''))
        hashtag_count = len(content.get('hashtags', []))

        # Simple heuristics for performance prediction
        engagement_score = 0

        # Caption length optimization
        if 100 <= caption_length <= 200:
            engagement_score += 3
        elif 50 <= caption_length <= 300:
            engagement_score += 2

        # Hashtag optimization
        if 5 <= hashtag_count <= 10:
            engagement_score += 2
        elif 3 <= hashtag_count <= 15:
            engagement_score += 1

        # Content type bonus
        content_type = content.get('content_type', '').lower()
        if content_type in ['interactive', 'educational']:
            engagement_score += 2
        elif content_type in ['entertaining']:
            engagement_score += 1

        return {
            'engagement_score': min(engagement_score, 10),
            'caption_optimized': 100 <= caption_length <= 200,
            'hashtags_optimized': 5 <= hashtag_count <= 10,
            'recommendations': self._get_performance_recommendations(content, engagement_score)
        }

    def _get_performance_recommendations(self, content: Dict[str, Any], score: int) -> List[str]:
        """Get recommendations to improve content performance"""
        recommendations = []

        caption_length = len(content.get('caption', ''))
        hashtag_count = len(content.get('hashtags', []))

        if caption_length < 100:
            recommendations.append("Consider making the caption more detailed (100-200 characters)")
        elif caption_length > 200:
            recommendations.append("Consider shortening the caption for better engagement")

        if hashtag_count < 5:
            recommendations.append("Add more relevant hashtags (5-10 optimal)")
        elif hashtag_count > 10:
            recommendations.append("Consider reducing the number of hashtags")

        if score < 5:
            recommendations.append("Review content for better engagement potential")

        return recommendations