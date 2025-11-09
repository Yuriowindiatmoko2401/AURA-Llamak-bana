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
from utils.debug_logger import debug_logger, PipelineStep

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

# Platform configuration
POSTING_PLATFORMS = {
    "telegram": True,
    "circlo": os.getenv("ENABLE_CIRCLO_POSTING", "false").lower() == "true"
}

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
            "circlo": "ready" if circlo_client else "not_ready",
            "image_generator": "ready" if image_generator else "not_ready",
            "scheduler": "active" if scheduler else "inactive"
        },
        "platforms": POSTING_PLATFORMS
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
                        schedule_command = "post each 4 minutes for 1 hour"
                else:
                    schedule_command = f"post {message.lower()}"
            else:
                # English pattern
                schedule_command = f"post {match.group(0)}"
            break

    # Default schedule if none found
    if not schedule_command:
        schedule_command = "post each 4 minutes for 1 hour"

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
    # Create unique session ID for this request
    session_id = f"circlo_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{payload.user.id}"

    # Start debugging session
    debug_logger.start_session(
        session_id=session_id,
        user_name=payload.user.name,
        message=payload.message
    )

    try:
        # Step 1: Entity Extraction
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.ENTITY_EXTRACTION,
            status="started",
            details={"message": payload.message}
        )

        entities = extract_entities_from_message(payload.message)
        debug_logger.log_extraction_result(session_id, entities)

        # Step 2: Schedule Parsing
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.SCHEDULE_PARSING,
            status="started",
            details={"command": entities["schedule_command"]}
        )

        schedule_params = scheduler.parse_schedule_command(entities["schedule_command"])
        debug_logger.log_schedule_parsing(session_id, schedule_params)

        # Step 3: Generate user preferences
        user_preferences = {
            "niche": entities.get("topic", payload.profile.niche),
            "keywords": entities.get("keywords", payload.user.preferredKeywords),
            "brand_voice": "helpful and creative",
            "target_audience": "general",
            "content_types": payload.user.preferredNiches or ["educational", "entertaining"]
        }

        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.CONTENT_CREW_INIT,
            status="started",
            details={
                "niche": user_preferences["niche"],
                "keywords_count": len(user_preferences["keywords"]),
                "total_posts": schedule_params.get("total_posts", 0)
            }
        )

        # Step 4: Initialize Content Crew
        crew = ContentCrew(
            user_preferences=user_preferences,
            schedule_params=schedule_params
        )

        # Step 5: Generate response message
        response_message = f"Hi {payload.user.name}! I'll help you create content about '{entities.get('topic', payload.profile.niche)}'. I'll schedule posts {entities['schedule_command']}. I'm generating {schedule_params['total_posts']} posts for you!"

        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.CONTENT_GENERATION,
            status="completed",
            details={
                "response_generated": True,
                "topic": entities.get('topic', payload.profile.niche),
                "total_posts": schedule_params['total_posts']
            }
        )

        # Schedule background content generation
        background_tasks.add_task(
            process_schedule_request,
            entities["schedule_command"],
            user_preferences,
            session_id
        )

        debug_logger.complete_session(session_id, "completed")

        # Return the response in the format Circlo expects
        return {
            "response": response_message,
            "session_id": session_id
        }

    except Exception as e:
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.CONTENT_GENERATION,
            status="error",
            error=str(e)
        )
        debug_logger.complete_session(session_id, "failed")

        # Return an error response in the format Circlo expects
        return {
            "response": f"Sorry, I encountered an error processing your request: {str(e)}",
            "session_id": session_id
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
            print("CrewAI failed to generate valid content, using fallback mechanism...")
            # Generate fallback content
            content_plan = generate_fallback_content(request.user_preferences, schedule_params)

        if not content_plan:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate content from CrewAI workflow and fallback mechanism"
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

@app.get("/debug/sessions")
async def get_debug_sessions():
    """Get all debug session summaries"""
    sessions = {}
    for session_id in debug_logger.active_sessions.keys():
        session_summary = debug_logger.get_session_summary(session_id)
        if session_summary:
            sessions[session_id] = session_summary

    return {
        "sessions": sessions,
        "total_sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/debug/session/{session_id}")
async def get_debug_session(session_id: str):
    """Get detailed debug session information"""
    session_summary = debug_logger.get_session_summary(session_id)

    if not session_summary:
        raise HTTPException(status_code=404, detail="Session not found")

    return session_summary

@app.delete("/debug/sessions")
async def clear_debug_sessions():
    """Clear all debug sessions"""
    debug_logger.active_sessions.clear()
    return {
        "message": "All debug sessions cleared",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/platforms")
async def get_platforms():
    """Get available posting platforms and their status"""
    return {
        "platforms": POSTING_PLATFORMS,
        "circlo_enabled": POSTING_PLATFORMS.get("circlo", False),
        "telegram_enabled": POSTING_PLATFORMS.get("telegram", False),
        "message": "Enable Circlo posting by setting ENABLE_CIRCLO_POSTING=true in environment variables",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/platforms/circlo/enable")
async def enable_circlo_posting():
    """Enable Circlo posting platform"""
    global POSTING_PLATFORMS
    POSTING_PLATFORMS["circlo"] = True
    os.environ["ENABLE_CIRCLO_POSTING"] = "true"

    return {
        "message": "Circlo posting enabled successfully",
        "platforms": POSTING_PLATFORMS,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/platforms/circlo/disable")
async def disable_circlo_posting():
    """Disable Circlo posting platform"""
    global POSTING_PLATFORMS
    POSTING_PLATFORMS["circlo"] = False
    os.environ["ENABLE_CIRCLO_POSTING"] = "false"

    return {
        "message": "Circlo posting disabled successfully",
        "platforms": POSTING_PLATFORMS,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/test-circlo-post")
async def test_circlo_post():
    """Test posting to Circlo with sample data"""
    if not POSTING_PLATFORMS.get("circlo", False):
        return {
            "status": "error",
            "message": "Circlo posting is not enabled. Enable it first via /platforms/circlo/enable"
        }, 400

    sample_content = {
        "caption": "Check out this amazing tech review! 🚀",
        "hashtags": ["#tech", "#review", "#gadgets"],
        "keywords": ["tech", "review", "gadgets"],
        "image_url": "https://replicate.delivery/pbxt/test/output.jpg"
    }

    sample_user_preferences = {
        "niche": "Tech Reviewer",
        "profile_type": "general"
    }

    try:
        result = await circlo_client.post_content_to_circlo(sample_content, sample_user_preferences)
        return {
            "status": "success",
            "message": "Circlo post test completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Circlo post test failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, 500

@app.post("/post-direct")
async def post_direct_content(request: dict):
    """Post content directly to Circlo without scheduling - posts everything sequentially"""
    if not POSTING_PLATFORMS.get("circlo", False):
        return {
            "status": "error",
            "message": "Circlo posting is not enabled. Enable it first via /platforms/circlo/enable"
        }, 400

    try:
        content_plan = request.get("content_plan", [])
        user_preferences = request.get("user_preferences", {"niche": "general", "profile_type": "general"})
        delay_between_posts = request.get("delay_seconds", 30)  # Default 30 seconds between posts

        if not content_plan:
            return {
                "status": "error",
                "message": "No content plan provided"
            }, 400

        print(f"🚀 Starting direct sequential posting of {len(content_plan)} posts...")
        print(f"⏱️  Delay between posts: {delay_between_posts} seconds")

        results = []
        successful_posts = 0
        failed_posts = 0

        for i, content in enumerate(content_plan):
            print(f"\n📤 Posting {i+1}/{len(content_plan)}: {content.get('caption', '')[:50]}...")

            try:
                # Post to Circlo
                result = await circlo_client.post_content_to_circlo(content, user_preferences)

                if result.get("status") == "success":
                    successful_posts += 1
                    print(f"✅ Post {i+1} successful!")
                    results.append({
                        "post_number": i + 1,
                        "status": "success",
                        "result": result,
                        "caption_preview": content.get('caption', '')[:50]
                    })
                else:
                    failed_posts += 1
                    print(f"❌ Post {i+1} failed: {result.get('error')}")
                    results.append({
                        "post_number": i + 1,
                        "status": "failed",
                        "error": result.get('error'),
                        "caption_preview": content.get('caption', '')[:50]
                    })

            except Exception as e:
                failed_posts += 1
                error_msg = f"Error posting {i+1}: {str(e)}"
                print(f"❌ {error_msg}")
                results.append({
                    "post_number": i + 1,
                    "status": "error",
                    "error": error_msg,
                    "caption_preview": content.get('caption', '')[:50]
                })

            # Add delay between posts (except for the last one)
            if i < len(content_plan) - 1 and delay_between_posts > 0:
                print(f"⏳ Waiting {delay_between_posts} seconds before next post...")
                await asyncio.sleep(delay_between_posts)

        print(f"\n🎉 Direct posting completed!")
        print(f"✅ Successful: {successful_posts}")
        print(f"❌ Failed: {failed_posts}")
        print(f"📊 Success rate: {(successful_posts / len(content_plan) * 100):.1f}%")

        return {
            "status": "completed",
            "total_posts": len(content_plan),
            "successful_posts": successful_posts,
            "failed_posts": failed_posts,
            "success_rate": successful_posts / len(content_plan) * 100,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Direct posting failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, 500

# Background task functions
async def process_schedule_request(command: str, user_preferences: Dict[str, Any], session_id: str = None):
    """Process schedule request from Circlo webhook"""
    if not session_id:
        session_id = f"bg_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        # Create a schedule ID
        schedule_id = f"circlo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.SCHEDULING_INIT,
            status="started",
            details={
                "command": command,
                "schedule_id": schedule_id
            }
        )

        # Parse schedule command
        schedule_params = scheduler.parse_schedule_command(command)
        debug_logger.log_schedule_parsing(session_id, schedule_params)

        # Generate content and schedule
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.CONTENT_CREW_INIT,
            status="started",
            details={"background_process": True}
        )

        crew = ContentCrew(
            user_preferences=user_preferences,
            schedule_params=schedule_params
        )

        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.CONTENT_GENERATION,
            status="started",
            details={"crew_initialized": True}
        )

        crew_result = crew.run()
        content_plan = extract_content_from_crew_result(crew_result)

        debug_logger.log_content_generation(session_id, crew_result, len(content_plan) if content_plan else 0)

        if not content_plan:
            print("CrewAI failed to generate valid content, using fallback mechanism...")
            debug_logger.log_step(
                session_id=session_id,
                step=PipelineStep.CONTENT_EXTRACTION,
                status="warning",
                error="CrewAI content extraction failed, using fallback"
            )
            # Generate fallback content
            content_plan = generate_fallback_content(user_preferences, schedule_params)

        if content_plan:
            debug_logger.log_step(
                session_id=session_id,
                step=PipelineStep.IMAGE_PROMPT_OPTIMIZATION,
                status="started",
                details={"content_count": len(content_plan)}
            )

            optimized_prompts = image_generator.optimize_prompts_for_replicate(content_plan)

            await generate_and_schedule_content(
                schedule_id,
                content_plan,
                optimized_prompts,
                schedule_params,
                user_preferences,
                session_id
            )
        else:
            debug_logger.log_step(
                session_id=session_id,
                step=PipelineStep.CONTENT_EXTRACTION,
                status="error",
                error="No content plan generated from CrewAI or fallback"
            )

        # Send notification to Telegram
        await telegram_client.send_status_update(
            f"Started new schedule from Circlo webhook:\n• Command: {command}\n• Posts: {schedule_params['total_posts']}"
        )

        debug_logger.complete_session(session_id, "completed")

    except Exception as e:
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.CONTENT_GENERATION,
            status="error",
            error=str(e)
        )
        debug_logger.complete_session(session_id, "failed")

        await telegram_client.send_error_notification(
            f"Error processing Circlo schedule request: {str(e)}",
            {"command": command, "schedule_id": schedule_id, "session_id": session_id}
        )

async def generate_and_schedule_content(schedule_id: str, content_plan: List[Dict[str, Any]],
                                      optimized_prompts: List[Dict[str, Any]],
                                      schedule_params: Dict[str, Any],
                                      user_preferences: Dict[str, Any],
                                      session_id: str = None):
    """Generate images and schedule content posting"""
    if not session_id:
        session_id = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.IMAGE_GENERATION,
            status="started",
            details={
                "schedule_id": schedule_id,
                "content_count": len(content_plan),
                "prompts_count": len(optimized_prompts)
            }
        )

        # Generate images
        image_results = image_generator.generate_batch_images(optimized_prompts)
        debug_logger.log_image_generation(session_id, image_results)

        # Combine content with generated images
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.CONTENT_EXTRACTION,
            status="started",
            details={"combining_content_with_images": True}
        )

        final_content = []
        for i, content in enumerate(content_plan):
            # Find corresponding image result
            image_result = next((img for img in image_results if img['post_index'] == i), None)

            final_content.append({
                **content,
                'image_url': image_result['image_url'] if image_result and image_result['status'] == 'success' else None,
                'image_status': image_result['status'] if image_result else 'failed'
            })

        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.POST_SCHEDULING,
            status="started",
            details={
                "final_content_count": len(final_content),
                "images_successful": len([r for r in image_results if r['status'] == 'success'])
            }
        )

        # Create posting schedule with multi-platform support
        posting_schedule_id = scheduler.create_posting_schedule(
            content_plan=final_content,
            schedule_params=schedule_params,
            post_callback=lambda content: post_to_multiple_platforms(content, user_preferences)
        )

        debug_logger.log_scheduling(session_id, posting_schedule_id, len(final_content))

        # Store schedule info
        active_schedules[schedule_id] = {
            'posting_schedule_id': posting_schedule_id,
            'schedule_params': schedule_params,
            'user_preferences': user_preferences,
            'content_count': len(final_content),
            'created_at': datetime.now().isoformat()
        }

        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.COMPLETION,
            status="completed",
            details={
                "schedule_id": schedule_id,
                "content_ready": True,
                "images_ready": len([r for r in image_results if r['status'] == 'success'])
            }
        )

        # Send notification to Telegram
        await telegram_client.send_status_update(
            f"Content generation completed for schedule {schedule_id}:\n• {len(final_content)} posts ready\n• Images generated: {len([r for r in image_results if r['status'] == 'success'])}"
        )

        debug_logger.complete_session(session_id, "completed")

    except Exception as e:
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.IMAGE_GENERATION,
            status="error",
            error=str(e)
        )
        debug_logger.complete_session(session_id, "failed")

        await telegram_client.send_error_notification(
            f"Error generating content for schedule {schedule_id}: {str(e)}"
        )

async def post_to_multiple_platforms(content: Dict[str, Any], user_preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Post content to multiple enabled platforms"""
    session_id = f"multi_platform_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    results = {
        "session_id": session_id,
        "platforms": {},
        "overall_status": "success",
        "timestamp": datetime.now().isoformat()
    }

    try:
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.TELEGRAM_POSTING,  # Using existing step for now
            status="started",
            details={
                "enabled_platforms": [platform for platform, enabled in POSTING_PLATFORMS.items() if enabled],
                "has_caption": bool(content.get('caption')),
                "hashtags_count": len(content.get('hashtags', [])),
                "has_image": bool(content.get('image_url'))
            }
        )

        # Post to Telegram if enabled
        if POSTING_PLATFORMS.get("telegram", False):
            try:
                telegram_result = await post_to_telegram(content)
                results["platforms"]["telegram"] = telegram_result
                if telegram_result.get('status') == 'error':
                    results["overall_status"] = "partial_failure"
            except Exception as e:
                results["platforms"]["telegram"] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                results["overall_status"] = "partial_failure"

        # Post to Circlo if enabled
        if POSTING_PLATFORMS.get("circlo", False):
            try:
                circlo_result = await circlo_client.post_content_to_circlo(content, user_preferences)
                results["platforms"]["circlo"] = circlo_result
                if circlo_result.get('status') == 'error':
                    results["overall_status"] = "partial_failure"
            except Exception as e:
                results["platforms"]["circlo"] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                results["overall_status"] = "partial_failure"

        debug_logger.complete_session(session_id, "completed" if results["overall_status"] == "success" else "partial_failure")
        return results

    except Exception as e:
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.TELEGRAM_POSTING,
            status="error",
            error=str(e)
        )
        debug_logger.complete_session(session_id, "failed")

        results["overall_status"] = "error"
        results["error"] = str(e)
        return results

async def post_to_telegram(content: Dict[str, Any]) -> Dict[str, Any]:
    """Post content to Telegram"""
    session_id = f"telegram_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        caption = content.get('caption', '')
        hashtags = content.get('hashtags', [])
        image_url = content.get('image_url')

        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.TELEGRAM_POSTING,
            status="started",
            details={
                "has_caption": bool(caption),
                "hashtags_count": len(hashtags),
                "has_image": bool(image_url)
            }
        )

        if image_url:
            # Send image post
            result = await telegram_client.send_image_post(image_url, caption, hashtags)
        else:
            # Send text post
            result = await telegram_client.send_text_post(caption, hashtags)

        debug_logger.log_telegram_post(session_id, result)
        debug_logger.complete_session(session_id, "completed")

        return result

    except Exception as e:
        debug_logger.log_step(
            session_id=session_id,
            step=PipelineStep.TELEGRAM_POSTING,
            status="error",
            error=str(e)
        )
        debug_logger.complete_session(session_id, "failed")

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

        # Look for JSON array in the text - more robust pattern
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', result_text, re.DOTALL)
        if json_match:
            json_content = json_match.group(0)

            # Preprocess JSON to handle common escape sequence issues
            json_content = fix_json_escape_sequences(json_content)

            try:
                content_plan = json.loads(json_content)
                if isinstance(content_plan, list):
                    print(f"Successfully extracted {len(content_plan)} items from CrewAI result")
                    return content_plan
            except json.JSONDecodeError as e:
                print(f"JSON parsing error after preprocessing: {e}")
                print(f"Problematic JSON content: {json_content[:500]}...")

                # Try alternative approach: extract individual JSON objects
                return extract_individual_json_objects(result_text)

        # If no JSON array found, try to extract individual objects
        return extract_individual_json_objects(result_text)

    except Exception as e:
        print(f"Error extracting content from CrewAI result: {e}")
        return []

def fix_json_escape_sequences(json_str: str) -> str:
    """Fix common JSON escape sequence issues"""
    # Fix invalid escape sequences by properly escaping backslashes
    # Remove or fix common problematic escape patterns
    import re

    # Fix invalid \ escapes (except for valid ones like \n, \t, \", \\)
    # This pattern finds backslashes that are not part of valid escape sequences
    def fix_invalid_escapes(match):
        char = match.group(1)
        if char in ['n', 't', 'r', 'b', 'f', '"', '\\', '/', 'u']:
            return f'\\{char}'  # Keep valid escapes
        else:
            return char  # Remove invalid backslash

    # Apply the fix
    fixed_json = re.sub(r'\\([^ntrbf"\\/u])', fix_invalid_escapes, json_str)

    # Fix double-escaped quotes that should be single-escaped
    fixed_json = re.sub(r'\\\\"', '\\"', fixed_json)

    # Fix other common issues
    fixed_json = fixed_json.replace('\\\\', '\\')  # Reduce double backslashes to single

    return fixed_json

def extract_individual_json_objects(text: str) -> List[Dict[str, Any]]:
    """Extract individual JSON objects when array parsing fails"""
    import re

    # Find all JSON objects in the text
    object_pattern = r'\{\s*"[^"]*"\s*:\s*[^{}]*\}'
    matches = re.findall(object_pattern, text, re.DOTALL)

    extracted_objects = []
    for match in matches:
        try:
            # Fix escape sequences in each object
            fixed_match = fix_json_escape_sequences(match)
            obj = json.loads(fixed_match)
            if isinstance(obj, dict):
                extracted_objects.append(obj)
        except json.JSONDecodeError:
            # Skip malformed objects
            continue

    if extracted_objects:
        print(f"Extracted {len(extracted_objects)} individual JSON objects")
        return extracted_objects

    print("Could not extract any valid JSON content from CrewAI result")
    return []

def generate_fallback_content(user_preferences: Dict[str, Any], schedule_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate fallback content when CrewAI fails"""
    try:
        niche = user_preferences.get('niche', 'general content')
        keywords = user_preferences.get('keywords', [])
        total_posts = schedule_params.get('total_posts', 3)

        # Generate simple but engaging content templates
        content_templates = [
            {
                "caption": f"Excited to share more insights about {niche}! 🔥 What are your thoughts on this topic?",
                "hashtags": [f"#{niche.replace(' ', '')}", "#insights", "#trending"] + [f"#{kw}" for kw in keywords[:3]],
                "keywords": keywords[:3] if keywords else [niche],
                "image_prompt": f"Professional and modern style image representing {niche} concept, clean design, trending aesthetic",
                "engagement_elements": ["question", "call_to_action"]
            },
            {
                "caption": f"Did you know? {niche.title()} is changing the game! 🚀 Here's what you need to know...",
                "hashtags": [f"#{niche.replace(' ', '')}", "#didyouknow", "#innovation"] + [f"#{kw}" for kw in keywords[:2]],
                "keywords": keywords[:2] if keywords else [niche, "innovation"],
                "image_prompt": f"Informative and engaging visual about {niche}, educational style, modern design elements",
                "engagement_elements": ["educational", "engaging_question"]
            },
            {
                "caption": f"Sharing some valuable insights about {niche} that might surprise you! 💡",
                "hashtags": [f"#{niche.replace(' ', '')}", "#valuable", "#knowledge"] + [f"#{kw}" for kw in keywords[:2]],
                "keywords": keywords[:2] if keywords else [niche, "knowledge"],
                "image_prompt": f"Inspirational and motivational image related to {niche}, warm colors, professional photography style",
                "engagement_elements": ["inspirational", "value_proposition"]
            },
            {
                "caption": f"Let's talk about the future of {niche}! 🎯 What trends are you seeing?",
                "hashtags": [f"#{niche.replace(' ', '')}", "#future", "#trends"] + [f"#{kw}" for kw in keywords[:3]],
                "keywords": keywords[:3] if keywords else [niche, "future", "trends"],
                "image_prompt": f"Futuristic and forward-thinking image about {niche}, technology and innovation theme, vibrant colors",
                "engagement_elements": ["forward_looking", "trend_discussion"]
            },
            {
                "caption": f"Here's a fresh perspective on {niche} that you might not have considered! 🌟",
                "hashtags": [f"#{niche.replace(' ', '')}", "#perspective", "#fresh"] + [f"#{kw}" for kw in keywords[:2]],
                "keywords": keywords[:2] if keywords else [niche, "perspective"],
                "image_prompt": f"Creative and artistic representation of {niche} concept, unique perspective, modern art style",
                "engagement_elements": ["creative", "thought_provoking"]
            }
        ]

        # Generate content for the required number of posts
        content_plan = []
        for i in range(min(total_posts, len(content_templates))):
            template = content_templates[i % len(content_templates)].copy()

            # Customize the template with specific keywords if available
            if keywords:
                keyword_variations = [
                    f"exploring {keywords[0]}",
                    f"insights about {keywords[1] if len(keywords) > 1 else keywords[0]}",
                    f"the world of {keywords[2] if len(keywords) > 2 else keywords[0]}",
                    f"discover {keywords[0]}",
                    f"learn about {keywords[1] if len(keywords) > 1 else keywords[0]}"
                ]

                variation = keyword_variations[i % len(keyword_variations)]
                template["caption"] = template["caption"].replace(niche, variation).replace(f"{niche.title()}", variation.title())

            # Add post number and customize further
            template["post_number"] = i + 1

            # Ensure hashtags are clean (no spaces, special characters)
            template["hashtags"] = [
                f"#{tag.lstrip('#').replace(' ', '').replace('-', '').replace('_', '')}"
                for tag in template["hashtags"]
            ]

            content_plan.append(template)

        print(f"Generated {len(content_plan)} fallback content items for niche: {niche}")
        return content_plan

    except Exception as e:
        print(f"Error generating fallback content: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)