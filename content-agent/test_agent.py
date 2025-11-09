#!/usr/bin/env python3
"""
Test script for the Automated Content Generation Agent
"""

import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our agents
from agents.scheduler import PostScheduler
from agents.crew import ContentCrew
from agents.image_generator import ImageGenerator
from agents.telegram_client import TelegramClient
from agents.trend_researcher import TrendResearcher
from agents.content_planner import ContentPlanner

async def test_components():
    """Test individual components"""
    print("🧪 Testing Components...")

    # Test 1: Environment Variables
    print("\n1. Testing Environment Variables...")
    required_vars = ["CORE_AGENT_TYPE", "GEMINI_API_KEY", "ZAI_API_KEY", "REPLICATE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return False
    else:
        print("✅ All required environment variables are set")

    # Test 2: Scheduler
    print("\n2. Testing Scheduler...")
    try:
        scheduler = PostScheduler()
        test_command = "post each 1 minutes for the next 5 minutes"
        schedule_params = scheduler.parse_schedule_command(test_command)
        print(f"✅ Scheduler parsed command: {test_command}")
        print(f"   → Total posts: {schedule_params['total_posts']}")
        print(f"   → Frequency: {schedule_params['frequency_minutes']} minutes")
        print(f"   → Duration: {schedule_params['total_hours']} hours")
        scheduler.shutdown()
    except Exception as e:
        print(f"❌ Scheduler test failed: {e}")
        return False

    # Test 3: LLM Connection
    print("\n3. Testing LLM Connection...")
    try:
        if os.getenv("CORE_AGENT_TYPE") == "gemini":
            from agents.llm_wrappers import GeminiLLM
            llm = GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"))
        elif os.getenv("CORE_AGENT_TYPE") == "zai":
            from agents.llm_wrappers import ZAILLM
            llm = ZAILLM(api_key=os.getenv("ZAI_API_KEY"))
        else:
            raise ValueError(f"Unsupported CORE_AGENT_TYPE: {os.getenv('CORE_AGENT_TYPE')}")

        test_prompt = "Generate a simple greeting for a social media post."
        response = llm._call(test_prompt)
        print(f"✅ LLM connection successful")
        print(f"   → Response: {response[:100]}...")
    except Exception as e:
        print(f"❌ LLM connection failed: {e}")
        return False

    # Test 4: Telegram Connection
    print("\n4. Testing Telegram Connection...")
    try:
        telegram_client = TelegramClient()
        result = await telegram_client.test_connection()
        if result['status'] == 'success':
            print("✅ Telegram connection successful")
            print(f"   → Bot: @{result['bot_info'].username}")
        else:
            print(f"❌ Telegram connection failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Telegram test failed: {e}")
        return False

    # Test 5: Trend Researcher
    print("\n5. Testing Trend Researcher...")
    try:
        trend_researcher = TrendResearcher()
        trends = trend_researcher.research_trends("AI technology", ["machine learning", "chatgpt", "automation"])
        print(f"✅ Trend research successful")
        print(f"   → Found {len(trends)} trends")
        if trends:
            print(f"   → Sample trend: {trends[0].get('title', 'N/A')}")
    except Exception as e:
        print(f"❌ Trend research test failed: {e}")
        return False

    print("\n🎉 All component tests passed!")
    return True

async def test_mini_workflow():
    """Test a mini version of the complete workflow"""
    print("\n🔄 Testing Mini Workflow...")

    try:
        # Define test user preferences
        user_preferences = {
            "niche": "AI technology",
            "keywords": ["machine learning", "automation", "future tech"],
            "brand_voice": "informative and engaging",
            "target_audience": "tech enthusiasts"
        }

        # Test schedule command
        test_command = "post each 30 seconds for the next 2 minutes"

        print(f"📝 Test command: {test_command}")
        print(f"🎯 Niche: {user_preferences['niche']}")

        # Step 1: Parse schedule
        scheduler = PostScheduler()
        schedule_params = scheduler.parse_schedule_command(test_command)
        print(f"✅ Schedule parsed: {schedule_params['total_posts']} posts")

        # Step 2: Research trends
        trend_researcher = TrendResearcher()
        trends = trend_researcher.research_trends(
            user_preferences['niche'],
            user_preferences['keywords']
        )
        print(f"✅ Trends researched: {len(trends)} trends found")

        # Step 3: Create content plan (smaller for testing)
        content_planner = ContentPlanner()
        content_plan = content_planner.create_content_plan(
            trends[:2],  # Use only first 2 trends for testing
            user_preferences,
            num_posts=3   # Create only 3 posts for testing
        )
        print(f"✅ Content planned: {len(content_plan)} posts created")

        # Step 4: Optimize image prompts
        image_generator = ImageGenerator()
        optimized_prompts = image_generator.optimize_prompts_for_replicate(content_plan[:2])  # Test with 2 posts
        print(f"✅ Image prompts optimized: {len(optimized_prompts)} prompts")

        # Step 5: Generate one test image (optional - costs money)
        print("⚠️  Image generation skipped to avoid API costs")

        # Step 6: Test Telegram message formatting
        telegram_client = TelegramClient()
        if content_plan:
            test_content = content_plan[0]
            print(f"✅ Content formatting test successful")
            print(f"   → Caption length: {len(test_content.get('caption', ''))}")
            print(f"   → Hashtags: {len(test_content.get('hashtags', []))}")

        scheduler.shutdown()
        print("\n🎉 Mini workflow test completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Mini workflow test failed: {e}")
        return False

def print_setup_instructions():
    """Print setup instructions for the user"""
    print("""
🔧 SETUP INSTRUCTIONS:

1. Install dependencies:
   cd content-agent
   pip install -r requirements.txt

2. Configure environment variables in .env:
   - CORE_AGENT_TYPE=gemini  # or zai
   - GEMINI_API_KEY=your_gemini_api_key
   - ZAI_API_KEY=your_zai_api_key
   - REPLICATE_API_KEY=your_replicate_api_key
   - TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   - TELEGRAM_CHAT_ID=your_telegram_chat_id

3. Get Telegram Bot Token:
   - Talk to @BotFather on Telegram
   - Create a new bot with /newbot
   - Copy the bot token

4. Get Telegram Chat ID:
   - Start a chat with your bot
   - Send a message
   - Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   - Find your chat ID in the response

5. Get API Keys:
   - Gemini: https://makersuite.google.com/app/apikey
   - Replicate: https://replicate.com/account
   - ZAI: https://open.bigmodel.cn/

6. Run the test:
   python test_agent.py

7. Start the server:
   python main.py
   # Server will run on http://localhost:8000

8. API Endpoints:
   - GET  /           - Root endpoint
   - GET  /health     - Health check
   - POST /schedule-posts - Schedule content posting
   - GET  /schedules  - View active schedules
   - GET  /stats      - System statistics

9. Example API call to schedule posts:
   curl -X POST "http://localhost:8000/schedule-posts" \\
        -H "Content-Type: application/json" \\
        -d '{
          "command": "post each 5 minutes for the next 30 minutes",
          "user_preferences": {
            "niche": "AI technology",
            "keywords": ["machine learning", "automation"],
            "brand_voice": "informative"
          }
        }'
""")

async def main():
    """Main test function"""
    print("🤖 Automated Content Generation Agent - Test Suite")
    print("=" * 50)

    # Check if we're in the right directory
    if not os.path.exists(".env"):
        print("❌ .env file not found!")
        print_setup_instructions()
        return

    print(f"📁 Working directory: {os.getcwd()}")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run tests
    components_ok = await test_components()

    if components_ok:
        workflow_ok = await test_mini_workflow()

        if workflow_ok:
            print("\n🎊 ALL TESTS PASSED! Your agent is ready to use.")
            print("\nNext steps:")
            print("1. Start the server: python main.py")
            print("2. Make API calls to schedule content")
            print("3. Monitor posts in your Telegram chat")
        else:
            print("\n⚠️  Component tests passed but workflow test failed.")
            print("Check your API keys and connections.")
    else:
        print("\n❌ Some component tests failed.")
        print("Please fix the issues before using the agent.")

    print_setup_instructions()

if __name__ == "__main__":
    asyncio.run(main())