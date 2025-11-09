#!/usr/bin/env python3
"""
Test script to verify Gemini API quota fix implementation
Tests both the updated model and fallback mechanism
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import our updated LLM wrappers
from agents.llm_wrappers import GeminiLLM, get_fallback_llm

async def test_gemini_direct():
    """Test direct Gemini API call with new model"""
    print("🧪 Testing direct Gemini API call...")

    try:
        llm = GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"))

        # Simple test prompt
        prompt = "Create a short social media post about AI technology (max 50 words)."

        result = llm._call(prompt)
        print(f"✅ Gemini API Success: {result[:100]}...")
        return True

    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return False

async def test_fallback_mechanism():
    """Test the fallback LLM mechanism"""
    print("\n🔄 Testing fallback LLM mechanism...")

    try:
        # Enable fallback mode
        os.environ["ENABLE_FALLBACK_LLM"] = "true"

        fallback_llm = get_fallback_llm()

        # Simple test prompt
        prompt = "Create a short social media post about technology (max 50 words)."

        result = fallback_llm._call(prompt)
        print(f"✅ Fallback LLM Success: {result[:100]}...")
        return True

    except Exception as e:
        print(f"❌ Fallback LLM Error: {e}")
        return False

async def test_content_planner():
    """Test the content planner with fallback enabled"""
    print("\n📋 Testing content planner with fallback...")

    try:
        from agents.content_planner import ContentPlanner

        # Enable fallback mode
        os.environ["ENABLE_FALLBACK_LLM"] = "true"

        planner = ContentPlanner()

        # Test content plan creation
        user_preferences = {
            "niche": "AI technology",
            "keywords": ["artificial intelligence", "machine learning", "automation"],
            "brand_voice": "professional and informative",
            "target_audience": "tech enthusiasts"
        }

        # Test with minimal trends
        trends = [{"topic": "AI trends 2024", "keywords": ["AI", "future"]}]

        content_plan = planner.create_content_plan(trends, user_preferences, num_posts=2)

        if content_plan and len(content_plan) > 0:
            print(f"✅ Content planner created {len(content_plan)} content items")
            print(f"Sample: {content_plan[0].get('caption', 'No caption')[:100]}...")
            return True
        else:
            print("❌ Content planner returned empty results")
            return False

    except Exception as e:
        print(f"❌ Content planner Error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Gemini API Quota Fixes\n")

    # Check environment variables
    required_vars = ["GEMINI_API_KEY", "ZAI_API_KEY", "DEEPSEEK_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {missing_vars}")
        print("Some tests may fail.\n")

    tests = [
        ("Direct Gemini API", test_gemini_direct),
        ("Fallback LLM", test_fallback_mechanism),
        ("Content Planner", test_content_planner),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nTotal: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n🎉 All tests passed! The Gemini API quota fix is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")

    return passed == len(results)

if __name__ == "__main__":
    asyncio.run(main())