#!/usr/bin/env python3
"""
Test script to verify Deepseek integration works end-to-end
"""

import os
import sys
sys.path.append('content-agent')

def test_deepseek_integration():
    """Test Deepseek integration with CrewAI"""
    print("🧪 Testing Deepseek Integration...")

    # Set environment
    os.environ['CORE_AGENT_TYPE'] = 'deepseek'
    # Make sure REPLICATE_API_KEY is set in your environment
    if 'REPLICATE_API_KEY' not in os.environ:
        print("❌ REPLICATE_API_KEY environment variable not set!")
        print("Please set it with: export REPLICATE_API_KEY=your_token_here")
        return False

    try:
        # Test 1: Direct LLM test
        print("\n1. Testing DeepseekLLM directly...")
        from agents.llm_wrappers import DeepseekLLM

        llm = DeepseekLLM(api_key=os.environ['REPLICATE_API_KEY'])
        response = llm._call("Say 'Hello Deepseek test successful'")
        print(f"✅ Direct LLM test: {response[:50]}...")

        # Test 2: Crew initialization test
        print("\n2. Testing CrewAI initialization...")
        from agents.crew import ContentCrew

        user_preferences = {
            'niche': 'AI technology',
            'keywords': ['AI', 'machine learning'],
            'brand_voice': 'professional',
            'target_audience': 'tech enthusiasts'
        }

        schedule_params = {
            'frequency': 'daily',
            'duration': '1 day'
        }

        crew = ContentCrew(user_preferences, schedule_params)
        print("✅ CrewAI initialized successfully")
        print(f"   LLM type: {type(crew.llm)}")
        print(f"   Model: {crew.llm.model_identifier}")

        # Test 3: Single agent test (without full execution)
        print("\n3. Testing single agent...")
        agent = crew.trend_researcher
        print(f"✅ Agent initialized: {agent.role}")
        print(f"   LLM type: {type(agent.llm)}")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_deepseek_integration()

    if success:
        print("\n🎉 All tests passed! Deepseek integration is working.")
        print("\nThe 404 error should now be resolved. You can run your CrewAI tasks with:")
        print("CORE_AGENT_TYPE=deepseek python your_script.py")
    else:
        print("\n❌ Tests failed. Please check the errors above.")