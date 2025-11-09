#!/usr/bin/env python3
"""
Test script for Circlo posting functionality
"""

import asyncio
import json
from agents.circlo_client import CircloClient

async def test_circlo_posting():
    """Test Circlo posting with the example data format"""
    print("🧪 Testing Circlo Posting Functionality")
    print("=" * 50)

    # Initialize Circlo client
    circlo_client = CircloClient()

    # Test data matching the example JSON structure from the question
    test_content = {
        "caption": "Check out this amazing tech review! 🚀",
        "hashtags": ["#tech", "#review", "#gadgets"],
        "keywords": ["tech", "review", "gadgets"],
        "image_url": "https://replicate.delivery/pbxt/test/output.jpg"
    }

    test_user_preferences = {
        "niche": "Tech Reviewer",
        "profile_type": "general"
    }

    print("📝 Test Content:")
    print(f"   Caption: {test_content['caption']}")
    print(f"   Hashtags: {test_content['hashtags']}")
    print(f"   Keywords: {test_content['keywords']}")
    print(f"   Image URL: {test_content['image_url']}")
    print(f"   Niche: {test_user_preferences['niche']}")
    print(f"   Profile: {test_user_preferences['profile_type']}")
    print()

    # Test formatting
    print("🔧 Testing content formatting...")
    formatted_payload = circlo_client.format_content_for_circlo(test_content, test_user_preferences)

    print("✅ Formatted Circlo Payload:")
    print(json.dumps(formatted_payload, indent=2))
    print()

    # Test the connection first
    print("🔗 Testing Circlo API connection...")
    connection_test = await circlo_client.test_connection()

    if connection_test["status"] == "success":
        print("✅ Connection successful!")
        print()

        # Test actual posting (commented out to avoid making real posts)
        print("📤 Testing Circlo post (simulated)...")
        print("⚠️  Note: Actual posting is commented out to avoid test posts")
        print()
        print("To enable actual posting:")
        print("1. Set ENABLE_CIRCLO_POSTING=true in your environment")
        print("2. Uncomment the posting code below")
        print("3. Ensure your Circlo JWT is valid")

        # Uncomment to test actual posting:
        # result = await circlo_client.post_content_to_circlo(test_content, test_user_preferences)
        # print("📊 Posting Result:")
        # print(json.dumps(result, indent=2))

    else:
        print(f"❌ Connection failed: {connection_test['message']}")
        print("Please check your Circlo configuration and JWT token.")

def test_manual_formatting():
    """Test the formatting logic manually"""
    print("\n🛠️  Manual Formatting Test")
    print("=" * 30)

    circlo_client = CircloClient()

    # Test different scenarios
    test_cases = [
        {
            "name": "Image post with full data",
            "content": {
                "caption": "Amazing tech discovery! 🔥",
                "hashtags": ["#tech", "#innovation", "#future"],
                "keywords": ["technology", "innovation"],
                "image_url": "https://example.com/image.jpg"
            },
            "preferences": {
                "niche": "Technology",
                "profile_type": "tech"
            }
        },
        {
            "name": "Text post only",
            "content": {
                "caption": "Just sharing some thoughts...",
                "hashtags": ["#thoughts", "#personal"],
                "keywords": []
            },
            "preferences": {
                "niche": "Lifestyle",
                "profile_type": "general"
            }
        },
        {
            "name": "Minimal data",
            "content": {
                "caption": "Quick update"
            },
            "preferences": {
                "niche": "General"
            }
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['name']}")
        formatted = circlo_client.format_content_for_circlo(
            test_case["content"],
            test_case["preferences"]
        )
        print(json.dumps(formatted, indent=2))

if __name__ == "__main__":
    print("🚀 Circlo Integration Test")
    print("=" * 40)
    print("This script tests the Circlo posting functionality")
    print("with the exact JSON format you specified.")
    print()

    # Run manual formatting test
    test_manual_formatting()

    # Run async test
    asyncio.run(test_circlo_posting())

    print("\n🎯 Test completed!")
    print("\n📚 Usage Instructions:")
    print("1. Set ENABLE_CIRCLO_POSTING=true in your .env file")
    print("2. Ensure CIRCLO_JWT is set with a valid token")
    print("3. Use the /platforms/circlo/enable endpoint to enable Circlo posting")
    print("4. Use /test-circlo-post endpoint to test with sample data")
    print("5. Generate content will now post to both Telegram and Circlo (when enabled)")