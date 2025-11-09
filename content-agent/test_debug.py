#!/usr/bin/env python3
"""
Test script to demonstrate the debugging functionality of the content generation pipeline.
This script simulates webhook requests and shows the detailed debugging output.
"""

import json
import requests
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"

def test_webhook_with_debugging():
    """Test the Circlo webhook with detailed debugging output"""

    print("🚀 Testing Content Generation Pipeline Debugging")
    print("=" * 60)

    # Test payload matching the diagram flow
    test_payload = {
        "history": [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"}
        ],
        "message": "buatkan postingan rutin per 2 menit satu jam ke depan tentang music texas",
        "user": {
            "id": "test_user_123",
            "name": "Test User",
            "preferredKeywords": ["music", "texas", "country"],
            "preferredNiches": ["educational", "entertaining"]
        },
        "profile": {
            "id": "music_agent",
            "name": "Music Content Agent",
            "niche": "music"
        }
    }

    print(f"📤 Sending webhook request...")
    print(f"👤 User: {test_payload['user']['name']}")
    print(f"💬 Message: {test_payload['message']}")
    print(f"🎵 Niche: {test_payload['profile']['niche']}")
    print()

    try:
        # Send webhook request
        response = requests.post(
            f"{BASE_URL}/circlo-hook",
            json=test_payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Webhook request successful!")
            print(f"📝 Response: {result.get('response', 'No response')}")
            print(f"🆔 Session ID: {result.get('session_id', 'No session ID')}")
            print()

            session_id = result.get('session_id')
            if session_id:
                # Monitor the debug session
                monitor_debug_session(session_id)

        else:
            print(f"❌ Webhook request failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

def monitor_debug_session(session_id):
    """Monitor a debug session and show progress"""

    print(f"🔍 Monitoring debug session: {session_id}")
    print("=" * 40)

    # Poll for session updates
    for i in range(20):  # Monitor for up to ~2 minutes
        try:
            response = requests.get(f"{BASE_URL}/debug/session/{session_id}")

            if response.status_code == 200:
                session_data = response.json()

                print(f"\n📊 Session Status Update (Check #{i + 1}):")
                print(f"🎯 Status: {session_data.get('status', 'unknown')}")
                print(f"👤 User: {session_data.get('user_name', 'unknown')}")
                print(f"⏱️  Start Time: {session_data.get('start_time', 'unknown')}")
                print(f"📈 Steps Completed: {len(session_data.get('steps_completed', []))}")

                # Show recent steps
                steps = session_data.get('steps_completed', [])
                if steps:
                    print("\n🔄 Recent Steps:")
                    for step in steps[-3:]:  # Show last 3 steps
                        emoji = get_step_emoji(step.get('step', ''))
                        status_icon = "✅" if step.get('status') == 'completed' else "❌" if step.get('status') == 'error' else "🔄"
                        print(f"   {emoji} {status_icon} {step.get('step', '').upper()}: {step.get('status', 'unknown')}")

                        if step.get('details'):
                            for key, value in step.get('details', {}).items():
                                print(f"      • {key}: {value}")

                        if step.get('error'):
                            print(f"      ❌ Error: {step.get('error')}")

                # Check if session is complete
                if session_data.get('status') in ['completed', 'failed']:
                    print(f"\n🎉 Session completed with status: {session_data.get('status')}")
                    break

            else:
                print(f"❌ Could not get session data: {response.status_code}")

        except Exception as e:
            print(f"❌ Error monitoring session: {e}")

        if i < 19:  # Don't sleep after the last iteration
            time.sleep(6)  # Wait 6 seconds between checks

def get_step_emoji(step_name):
    """Get emoji for step name"""
    emojis = {
        "webhook_received": "🔔",
        "entity_extraction": "🔍",
        "schedule_parsing": "📅",
        "content_crew_init": "👥",
        "content_generation": "✍️",
        "content_extraction": "📝",
        "image_prompt_optimization": "🎨",
        "image_generation": "🖼️",
        "scheduling_init": "⏰",
        "post_scheduling": "📋",
        "telegram_posting": "📤",
        "completion": "🎉"
    }
    return emojis.get(step_name, "🔄")

def show_all_sessions():
    """Show all debug sessions"""

    print("\n📚 All Debug Sessions:")
    print("=" * 30)

    try:
        response = requests.get(f"{BASE_URL}/debug/sessions")

        if response.status_code == 200:
            data = response.json()
            sessions = data.get('sessions', {})

            print(f"Total sessions: {data.get('total_sessions', 0)}")

            for session_id, session in sessions.items():
                status_icon = "✅" if session.get('status') == 'completed' else "❌" if session.get('status') == 'failed' else "🔄"
                print(f"{status_icon} {session_id}: {session.get('status', 'unknown')} ({session.get('user_name', 'unknown')})")

        else:
            print(f"❌ Could not get sessions: {response.status_code}")

    except Exception as e:
        print(f"❌ Error getting sessions: {e}")

def main():
    """Main test function"""

    print("🐛 Content Generation Pipeline Debug Test")
    print("=" * 50)
    print("This script will test the debugging functionality of your")
    print("content generation pipeline by simulating a Circlo webhook.")
    print()

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy!")
            print()
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
    except:
        print("❌ Server is not running. Please start the server first:")
        print("   cd content-agent && python main.py")
        return

    # Run the test
    test_webhook_with_debugging()

    # Show all sessions at the end
    show_all_sessions()

    print("\n🎯 Debug test completed!")
    print("You can check the debug endpoints manually:")
    print(f"  • All sessions: {BASE_URL}/debug/sessions")
    print(f"  • Health check: {BASE_URL}/health")
    print(f"  • Clear sessions: DELETE {BASE_URL}/debug/sessions")

if __name__ == "__main__":
    main()