from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import asyncio
from datetime import datetime
import json

from agents.crew import ContentCrew
from agents.scheduler import PostScheduler
from agents.telegram_client import TelegramClient
from agents.image_generator import ImageGenerator
from agents.circlo_client import CircloClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global instances
scheduler = None
telegram_client = None
image_generator = None
circlo_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    global scheduler, telegram_client, image_generator, circlo_client

    # Startup
    print("🚀 Starting Automated Content Generation Agent...")

    # Initialize global instances
    scheduler = PostScheduler()
    telegram_client = TelegramClient()
    image_generator = ImageGenerator()
    circlo_client = CircloClient()

    # Test Telegram connection
    try:
        test_result = await telegram_client.test_connection()
        if test_result['status'] == 'success':
            print("✅ Telegram connection successful")
        else:
            print(f"❌ Telegram connection failed: {test_result['error']}")
    except Exception as e:
        print(f"❌ Error testing Telegram connection: {e}")

    # Test Circlo authentication
    try:
        test_result = await circlo_client.test_connection()
        if test_result['status'] == 'success':
            print("✅ Circlo authentication successful")
            if circlo_client.is_authenticated():
                print(f"✅ Circlo user authenticated: {circlo_client.get_user_data()}")
        else:
            print(f"❌ Circlo authentication failed: {test_result['message']}")
    except Exception as e:
        print(f"❌ Error testing Circlo authentication: {e}")

    yield

    # Shutdown
    print("🛑 Shutting down Automated Content Generation Agent...")
    if scheduler:
        scheduler.shutdown()

app = FastAPI(
    title="Automated Content Generation Agent",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API requests/responses
class CircloMessage(BaseModel):
    """Model for individual message in Circlo history"""
    role: str
    content: str

class CircloUser(BaseModel):
    """Model for Circlo user information"""
    id: str
    name: str
    preferredKeywords: List[str]
    preferredNiches: List[str]

class CircloProfile(BaseModel):
    """Model for Circlo agent profile"""
    id: str
    name: str
    niche: str

class CircloPayload(BaseModel):
    """Model for Circlo webhook payload according to documentation"""
    history: List[CircloMessage]
    message: str
    user: CircloUser
    profile: CircloProfile

class CircloAuthRequest(BaseModel):
    """Model for Circlo authentication request"""
    jwt_code: Optional[str] = None  # If not provided, will use environment variable

class ScheduleRequest(BaseModel):
    """Model for scheduling content posts"""
    command: str  # e.g., "post each 2 minutes for the next one hour"
    user_preferences: Dict[str, Any]
    schedule_id: Optional[str] = None

class UserPreferences(BaseModel):
    """Model for user content preferences"""
    niche: str
    keywords: List[str]
    brand_voice: str = "friendly and informative"
    target_audience: str = "general"
    content_types: List[str] = ["educational", "entertaining"]

class ContentResponse(BaseModel):
    """Model for content generation response"""
    status: str
    schedule_id: Optional[str] = None
    message: str
    content_plan: Optional[List[Dict[str, Any]]] = None
    schedule_params: Optional[Dict[str, Any]] = None

# In-memory storage for active schedules and content
active_schedules = {}
content_cache = {}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Automated Content Generation Agent",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/")
async def root_webhook(payload: dict, background_tasks: BackgroundTasks):
    """
    Handle POST requests to root endpoint (for GetCirclo webhook compatibility)
    This forwards the request to the main Circlo webhook handler
    """
    try:
        # Convert the dict payload to CircloPayload format
        circlo_payload = CircloPayload(**payload)

        # Forward to the existing webhook handler
        return await circlo_webhook(circlo_payload, background_tasks)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error processing webhook: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, 500

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    stats = scheduler.get_scheduler_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_stats": stats,
        "services": {
            "telegram": "connected" if telegram_client else "disconnected",
            "image_generator": "ready" if image_generator else "not_ready",
            "scheduler": "active" if scheduler else "inactive"
        }
    }

@app.post("/circlo-auth")
async def circlo_authenticate(request: CircloAuthRequest):
    """
    Authenticate with Circlo API using JWT token

    Args:
        request: Authentication request containing optional JWT code
    """
    try:
        # If JWT code is provided in request, temporarily override the client's token
        original_jwt = circlo_client.jwt_token
        if request.jwt_code:
            circlo_client.jwt_token = request.jwt_code

        # Perform authentication
        auth_result = await circlo_client.authenticate()

        # Restore original JWT if we temporarily changed it
        if request.jwt_code:
            circlo_client.jwt_token = original_jwt

        if auth_result["success"]:
            return {
                "status": "success",
                "message": "Authentication successful",
                "user_data": auth_result.get("data"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "Authentication failed",
                "error": auth_result.get("error"),
                "timestamp": datetime.now().isoformat()
            }, 400

    except Exception as e:
        return {
            "status": "error",
            "message": "Authentication error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, 500

@app.get("/circlo-status")
async def circlo_status():
    """
    Get current Circlo authentication status
    """
    try:
        if not circlo_client:
            return {
                "status": "error",
                "message": "Circlo client not initialized",
                "authenticated": False,
                "timestamp": datetime.now().isoformat()
            }, 500

        return {
            "status": "success",
            "authenticated": circlo_client.is_authenticated(),
            "user_data": circlo_client.get_user_data(),
            "message": "Circlo client is ready" if circlo_client.is_authenticated() else "Not authenticated",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Status check error",
            "error": str(e),
            "authenticated": False,
            "timestamp": datetime.now().isoformat()
        }, 500

def extract_entities_from_message(message: str) -> Dict[str, Any]:
    """
    Extract entities from user message using pattern matching and LLM
    Messages like: "buatkan postingan rutin per 2 menit satu jam ke depan tentang music texas"
    """
    import re

    # Extract schedule information using regex patterns
    schedule_command = ""
    topic = ""

    # Pattern for frequency and duration in Indonesian
    schedule_patterns = [
        r'(?:buatkan|buat)\s+(?:postingan\s+)?(?:rutin\s+)?per\s+(\d+)\s+(?:menit|jam|hari)\s+(?:\d+\s+)?(?:menit|jam|hari)?\s+ke\s+depan',
        r'post\s+(?:each|every)\s+(\d+)\s+(?:minutes?|hours?|days?)\s+(?:for\s+)?(?:the\s+next\s+)?(\d+\s+(?:minutes?|hours?|days?))?',
        r'(?:setiap|tiap)\s+(\d+)\s+(?:menit|jam|hari)\s+(?:selama\s+)?(\d+\s+(?:menit|jam|hari))?',
    ]

    for pattern in schedule_patterns:
        match = re.search(pattern, message.lower())
        if match:
            if "menit" in message.lower() or "jam" in message.lower():
                # Indonesian pattern
                if "menit" in message.lower() and "jam" in message.lower():
                    frequency_match = re.search(r'per\s+(\d+)\s+menit', message.lower())
                    duration_match = re.search(r'satu\s+jam|1\s+jam', message.lower())
                    if frequency_match:
                        freq = frequency_match.group(1)
                        schedule_command = f"post each {freq} minutes for 1 hour"
                    elif duration_match:
                        schedule_command = "post each 2 minutes for 1 hour"
                else:
                    schedule_command = f"post {message.lower()}"
            else:
                # English pattern
                schedule_command = f"post {match.group(0)}"
            break

    # Default schedule if none found
    if not schedule_command:
        schedule_command = "post each 2 minutes for 1 hour"

    # Extract topic/keywords
    topic_patterns = [
        r'tentang\s+([^,.!?]+)',
        r'about\s+([^,.!?]+)',
        r'mengenai\s+([^,.!?]+)',
    ]

    for pattern in topic_patterns:
        match = re.search(pattern, message.lower())
        if match:
            topic = match.group(1).strip()
            break

    # If no topic found, use profile niche or default
    if not topic:
        topic = "general content"

    return {
        "schedule_command": schedule_command,
        "topic": topic,
        "keywords": topic.split() if topic else ["content", "social media"]
    }

@app.post("/circlo-hook")
async def circlo_webhook(payload: CircloPayload, background_tasks: BackgroundTasks):
    """Handle Circlo webhooks - generate content responses"""
    try:
        print(f"Received Circlo webhook from user {payload.user.name}")
        print(f"Message: {payload.message}")
        print(f"User preferences: {payload.user.preferredKeywords}, {payload.user.preferredNiches}")

        # Extract entities from user message
        entities = extract_entities_from_message(payload.message)
        print(f"Extracted entities: {entities}")

        # Parse schedule command
        schedule_params = scheduler.parse_schedule_command(entities["schedule_command"])
        print(f"Parsed schedule params: {schedule_params}")

        # Generate user preferences combining extracted info with profile
        user_preferences = {
            "niche": entities.get("topic", payload.profile.niche),
            "keywords": entities.get("keywords", payload.user.preferredKeywords),
            "brand_voice": "helpful and creative",
            "target_audience": "general",
            "content_types": payload.user.preferredNiches or ["educational", "entertaining"]
        }

        # Generate response using CrewAI with both user_preferences and schedule_params
        crew = ContentCrew(
            user_preferences=user_preferences,
            schedule_params=schedule_params
        )

        # For now, create a simple response that acknowledges the scheduling request
        response_message = f"Hi {payload.user.name}! I'll help you create content about '{entities.get('topic', payload.profile.niche)}'. I'll schedule posts {entities['schedule_command']}. I'm generating {schedule_params['total_posts']} posts for you!"

        # Return the response in the format Circlo expects
        return {
            "response": response_message
        }

    except Exception as e:
        print(f"Error processing Circlo webhook: {e}")
        # Return an error response in the format Circlo expects
        return {
            "response": f"Sorry, I encountered an error processing your request: {str(e)}"
        }

@app.post("/schedule-posts", response_model=ContentResponse)
async def schedule_posts(request: ScheduleRequest, background_tasks: BackgroundTasks):
    """
    Schedule automated content posting

    Args:
        request: Schedule request with command and preferences
        background_tasks: FastAPI background tasks
    """
    try:
        # Parse the schedule command
        schedule_params = scheduler.parse_schedule_command(request.command)

        if schedule_params['total_posts'] <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid schedule command. Could not determine posting frequency or duration."
            )

        # Generate content using CrewAI
        print(f"Generating content for {schedule_params['total_posts']} posts...")

        crew = ContentCrew(
            user_preferences=request.user_preferences,
            schedule_params=schedule_params
        )

        # Run the crew to generate content strategy
        crew_result = crew.run()

        # Extract the organized content from the crew result
        content_plan = extract_content_from_crew_result(crew_result)

        if not content_plan:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate content from CrewAI workflow"
            )

        # Optimize image prompts and generate images
        print("Optimizing image prompts...")
        optimized_prompts = image_generator.optimize_prompts_for_replicate(content_plan)

        # Generate images in background
        background_tasks.add_task(
            generate_and_schedule_content,
            request.schedule_id,
            content_plan,
            optimized_prompts,
            schedule_params,
            request.user_preferences
        )

        return ContentResponse(
            status="processing",
            schedule_id=request.schedule_id,
            message=f"Started generating {schedule_params['total_posts']} posts. Images are being generated and posts will be scheduled.",
            content_plan=content_plan[:3],  # Return first 3 posts as preview
            schedule_params=schedule_params
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling posts: {str(e)}")

@app.get("/schedule/{schedule_id}/status")
async def get_schedule_status(schedule_id: str):
    """Get status of a specific schedule"""
    schedule_info = scheduler.get_schedule_status(schedule_id)

    if not schedule_info:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "schedule_id": schedule_id,
        "status": schedule_info['status'],
        "created_at": schedule_info['created_at'],
        "total_posts": schedule_info['total_posts'],
        "posts_completed": schedule_info['posts_completed'],
        "posts_failed": schedule_info['posts_failed'],
        "schedule_params": schedule_info['schedule_params']
    }

@app.get("/schedules")
async def get_all_schedules():
    """Get all active schedules"""
    schedules = scheduler.get_all_active_schedules()
    return {
        "schedules": schedules,
        "total_count": len(schedules),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/schedule/{schedule_id}/pause")
async def pause_schedule(schedule_id: str):
    """Pause an active schedule"""
    success = scheduler.pause_schedule(schedule_id)

    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found or could not be paused")

    return {
        "message": f"Schedule {schedule_id} paused successfully",
        "schedule_id": schedule_id,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/schedule/{schedule_id}/resume")
async def resume_schedule(schedule_id: str, background_tasks: BackgroundTasks):
    """Resume a paused schedule"""
    # Note: This would need to store the original callback function
    # For now, we'll return a not implemented response
    raise HTTPException(
        status_code=501,
        detail="Resume functionality requires storing original callback function"
    )

@app.delete("/schedule/{schedule_id}")
async def cancel_schedule(schedule_id: str):
    """Cancel an active schedule"""
    success = scheduler.cancel_schedule(schedule_id)

    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found or could not be cancelled")

    return {
        "message": f"Schedule {schedule_id} cancelled successfully",
        "schedule_id": schedule_id,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/posts/history")
async def get_post_history(schedule_id: Optional[str] = None, limit: int = 100):
    """Get post history, optionally filtered by schedule"""
    history = scheduler.get_post_history(schedule_id, limit)
    return {
        "posts": history,
        "total_count": len(history),
        "schedule_filter": schedule_id,
        "limit": limit,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stats")
async def get_stats():
    """Get overall system statistics"""
    scheduler_stats = scheduler.get_scheduler_stats()

    return {
        "system_stats": scheduler_stats,
        "timestamp": datetime.now().isoformat(),
        "uptime": "N/A"  # Could be implemented with startup time tracking
    }

# Background task functions
async def process_schedule_request(command: str, user_preferences: Dict[str, Any]):
    """Process schedule request from Circlo webhook"""
    try:
        # Create a schedule ID
        schedule_id = f"circlo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Parse schedule command
        schedule_params = scheduler.parse_schedule_command(command)

        # Generate content and schedule
        crew = ContentCrew(
            user_preferences=user_preferences,
            schedule_params=schedule_params
        )

        crew_result = crew.run()
        content_plan = extract_content_from_crew_result(crew_result)

        if content_plan:
            optimized_prompts = image_generator.optimize_prompts_for_replicate(content_plan)
            await generate_and_schedule_content(
                schedule_id,
                content_plan,
                optimized_prompts,
                schedule_params,
                user_preferences
            )

        # Send notification to Telegram
        await telegram_client.send_status_update(
            f"Started new schedule from Circlo webhook:\n• Command: {command}\n• Posts: {schedule_params['total_posts']}"
        )

    except Exception as e:
        await telegram_client.send_error_notification(
            f"Error processing Circlo schedule request: {str(e)}",
            {"command": command, "schedule_id": schedule_id}
        )

async def generate_and_schedule_content(schedule_id: str, content_plan: List[Dict[str, Any]],
                                      optimized_prompts: List[Dict[str, Any]],
                                      schedule_params: Dict[str, Any],
                                      user_preferences: Dict[str, Any]):
    """Generate images and schedule content posting"""
    try:
        print(f"Starting content generation for schedule {schedule_id}")

        # Generate images
        print("Generating images...")
        image_results = image_generator.generate_batch_images(optimized_prompts)

        # Combine content with generated images
        final_content = []
        for i, content in enumerate(content_plan):
            # Find corresponding image result
            image_result = next((img for img in image_results if img['post_index'] == i), None)

            final_content.append({
                **content,
                'image_url': image_result['image_url'] if image_result and image_result['status'] == 'success' else None,
                'image_status': image_result['status'] if image_result else 'failed'
            })

        # Create posting schedule
        posting_schedule_id = scheduler.create_posting_schedule(
            content_plan=final_content,
            schedule_params=schedule_params,
            post_callback=post_to_telegram
        )

        # Store schedule info
        active_schedules[schedule_id] = {
            'posting_schedule_id': posting_schedule_id,
            'schedule_params': schedule_params,
            'user_preferences': user_preferences,
            'content_count': len(final_content),
            'created_at': datetime.now().isoformat()
        }

        print(f"Content generation completed for schedule {schedule_id}")

        # Send notification to Telegram
        await telegram_client.send_status_update(
            f"Content generation completed for schedule {schedule_id}:\n• {len(final_content)} posts ready\n• Images generated: {len([r for r in image_results if r['status'] == 'success'])}"
        )

    except Exception as e:
        print(f"Error in generate_and_schedule_content: {e}")
        await telegram_client.send_error_notification(
            f"Error generating content for schedule {schedule_id}: {str(e)}"
        )

async def post_to_telegram(content: Dict[str, Any]) -> Dict[str, Any]:
    """Post content to Telegram"""
    try:
        caption = content.get('caption', '')
        hashtags = content.get('hashtags', [])
        image_url = content.get('image_url')

        if image_url:
            # Send image post
            result = await telegram_client.send_image_post(image_url, caption, hashtags)
        else:
            # Send text post
            result = await telegram_client.send_text_post(caption, hashtags)

        return result

    except Exception as e:
        print(f"Error posting to Telegram: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def extract_content_from_crew_result(crew_result) -> List[Dict[str, Any]]:
    """Extract content plan from CrewAI result"""
    try:
        # CrewAI result can be complex, try to extract JSON content
        if hasattr(crew_result, 'raw'):
            result_text = crew_result.raw
        elif isinstance(crew_result, str):
            result_text = crew_result
        else:
            result_text = str(crew_result)

        # Try to find JSON content in the result
        import re

        # Look for JSON array in the text
        json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
        if json_match:
            json_content = json_match.group(0)
            content_plan = json.loads(json_content)
            if isinstance(content_plan, list):
                return content_plan

        # If no JSON found, return empty list
        print("Could not extract JSON content from CrewAI result")
        return []

    except Exception as e:
        print(f"Error extracting content from CrewAI result: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)