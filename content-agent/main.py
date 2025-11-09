from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Automated Content Generation Agent", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
scheduler = PostScheduler()
telegram_client = TelegramClient()
image_generator = ImageGenerator()

# Pydantic models for API requests/responses
class CircloPayload(BaseModel):
    """Model for Circlo webhook payload"""
    event_type: str
    user_id: str
    data: Dict[str, Any]

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

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    print("🚀 Starting Automated Content Generation Agent...")

    # Test Telegram connection
    try:
        test_result = await telegram_client.test_connection()
        if test_result['status'] == 'success':
            print("✅ Telegram connection successful")
        else:
            print(f"❌ Telegram connection failed: {test_result['error']}")
    except Exception as e:
        print(f"❌ Error testing Telegram connection: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    print("🛑 Shutting down Automated Content Generation Agent...")
    scheduler.shutdown()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Automated Content Generation Agent",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

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

@app.post("/circlo-hook")
async def circlo_webhook(payload: CircloPayload, background_tasks: BackgroundTasks):
    """Handle Circlo webhooks"""
    try:
        print(f"Received Circlo webhook: {payload.event_type}")

        # Process different event types
        if payload.event_type == "schedule_request":
            # Extract schedule command from payload
            command = payload.data.get("command", "")
            user_preferences = payload.data.get("user_preferences", {})

            # Schedule content generation
            background_tasks.add_task(
                process_schedule_request,
                command,
                user_preferences
            )

            return {
                "status": "accepted",
                "message": "Schedule request received and processing started",
                "event_type": payload.event_type,
                "timestamp": datetime.now().isoformat()
            }

        else:
            return {
                "status": "ignored",
                "message": f"Unsupported event type: {payload.event_type}",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

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