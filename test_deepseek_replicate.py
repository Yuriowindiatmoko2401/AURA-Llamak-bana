#!/usr/bin/env python3
"""
Test script to verify DeepSeek integration with Replicate API
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), 'content-agent', '.env'))

# Add the content-agent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'content-agent'))

from agents.llm_wrappers import DeepseekLLM

def test_deepseek_integration():
    """Test DeepSeek LLM integration with Replicate"""

    # Get API key from environment
    api_key = os.getenv("REPLICATE_API_KEY") or os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        print("❌ Error: No API key found. Set REPLICATE_API_KEY or DEEPSEEK_API_KEY environment variable.")
        return False

    print("🔄 Initializing DeepSeek LLM with Replicate...")

    try:
        # Initialize the DeepSeek LLM
        llm = DeepseekLLM(api_key=api_key)
        print("✅ DeepSeek LLM initialized successfully")

        # Test with a simple prompt
        test_prompt = "Hello! Can you tell me a brief fun fact about AI?"
        print(f"🧪 Testing with prompt: '{test_prompt}'")

        response = llm._call(test_prompt)

        if response.startswith("Error:"):
            print(f"❌ LLM Call Failed: {response}")
            return False

        print("✅ DeepSeek LLM call successful!")
        print(f"📝 Response: {response[:200]}...")  # Show first 200 chars

        return True

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Testing DeepSeek integration with Replicate API")
    print("=" * 50)

    success = test_deepseek_integration()

    if success:
        print("\n🎉 DeepSeek integration test PASSED!")
    else:
        print("\n💥 DeepSeek integration test FAILED!")
        sys.exit(1)