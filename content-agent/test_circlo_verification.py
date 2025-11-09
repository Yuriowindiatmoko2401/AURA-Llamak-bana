#!/usr/bin/env python3
"""
Test script to verify Circlo API posting functionality
"""

import asyncio
import os
import sys
from agents.circlo_client import CircloClient

async def test_circlo_posting():
    """Test actual posting to Circlo API"""

    print("🧪 Testing Circlo API posting...")

    # Initialize Circlo client
    client = CircloClient()

    # Test connection first
    print("\n1. Testing connection to Circlo API...")
    connection_test = await client.test_connection()
    print(f"   Connection test result: {connection_test}")

    if connection_test.get('status') != 'success':
        print("❌ Connection test failed - cannot proceed with posting test")
        return False

    # Create sample content for testing
    sample_content = {
        'caption': 'Test post from content agent 🔥 - this is a verification post to check if our integration works properly! #test #automation #contentagent',
        'hashtags': ['#test', '#automation', '#contentagent', '#ai', '#verification'],
        'keywords': ['test', 'automation', 'ai', 'verification'],
        'image_url': 'https://replicate.delivery/xezq/pxGUAMd98fVKe0OiZ4oEHlN2UfdmaAk0imag57OBb9niECPrA/tmpn80nwj98.png'  # Use the successful image from logs
    }

    sample_user_preferences = {
        'niche': 'general',
        'profile_type': 'general'
    }

    print(f"\n2. Testing content posting with sample data:")
    print(f"   Caption: {sample_content['caption'][:50]}...")
    print(f"   Image URL: {sample_content['image_url']}")
    print(f"   Keywords: {sample_content['keywords']}")

    # Test the actual posting
    try:
        result = await client.post_content_to_circlo(sample_content, sample_user_preferences)

        print(f"\n3. Posting result:")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Timestamp: {result.get('timestamp')}")

        if result.get('status') == 'success':
            print("✅ SUCCESS: Post was successfully submitted to Circlo!")
            print(f"   Circlo response data: {result.get('circlo_data')}")
            return True
        else:
            print(f"❌ FAILED: Post submission failed with error: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ EXCEPTION: Error during posting: {str(e)}")
        return False

async def test_circlo_authentication():
    """Test Circlo Bearer token authentication"""

    print("\n🔐 Testing Circlo Bearer token authentication...")

    client = CircloClient()

    # Test authentication (now just validates token is present)
    auth_result = await client.authenticate()

    print(f"   Auth result: {auth_result}")

    if auth_result.get('success'):
        print("✅ Bearer token authentication ready!")
        print(f"   Token status: {auth_result.get('data')}")
        return True
    else:
        print(f"❌ Authentication failed: {auth_result.get('error')}")
        return False

async def main():
    """Main test function"""

    print("=" * 60)
    print("CIRCLO API VERIFICATION TEST")
    print("=" * 60)

    # Check environment variables
    print("\n🔧 Checking environment setup...")
    jwt_token = os.getenv("CIRCLO_JWT")
    circlo_posting = os.getenv("ENABLE_CIRCLO_POSTING", "false").lower() == "true"

    print(f"   CIRCLO_JWT: {'✅ Set' if jwt_token else '❌ Not set'}")
    print(f"   ENABLE_CIRCLO_POSTING: {'✅ Enabled' if circlo_posting else '❌ Disabled'}")

    if not jwt_token:
        print("\n❌ CIRCLO_JWT is not set - cannot proceed with tests")
        sys.exit(1)

    # Test authentication
    auth_success = await test_circlo_authentication()

    if not auth_success:
        print("\n❌ Authentication failed - but proceeding with direct posting test...")

    # Test posting
    posting_success = await test_circlo_posting()

    print("\n" + "=" * 60)
    print("TEST SUMMARY:")
    print(f"   Authentication: {'✅ SUCCESS' if auth_success else '❌ FAILED'}")
    print(f"   Direct Posting: {'✅ SUCCESS' if posting_success else '❌ FAILED'}")

    if posting_success:
        print("\n🎉 CONCLUSION: Circlo posting appears to be working!")
        print("   If posts are not appearing on getcirclo.com, it could be:")
        print("   - Processing delay on Circlo's side")
        print("   - Content review/ moderation queue")
        print("   - API posts go to a different section than manual posts")
        print("   - The JWT token may have different permissions")
    else:
        print("\n❌ CONCLUSION: Circlo posting is NOT working properly")
        print("   Check the error messages above for troubleshooting")

    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())