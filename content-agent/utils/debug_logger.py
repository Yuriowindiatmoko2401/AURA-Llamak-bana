"""
Debug Logger for tracking content generation pipeline progress
Provides detailed step-by-step logging with timestamps and status tracking
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class PipelineStep(Enum):
    """Pipeline steps for content generation"""
    WEBHOOK_RECEIVED = "webhook_received"
    ENTITY_EXTRACTION = "entity_extraction"
    SCHEDULE_PARSING = "schedule_parsing"
    CONTENT_CREW_INIT = "content_crew_init"
    CONTENT_GENERATION = "content_generation"
    CONTENT_EXTRACTION = "content_extraction"
    IMAGE_PROMPT_OPTIMIZATION = "image_prompt_optimization"
    IMAGE_GENERATION = "image_generation"
    SCHEDULING_INIT = "scheduling_init"
    POST_SCHEDULING = "post_scheduling"
    TELEGRAM_POSTING = "telegram_posting"
    COMPLETION = "completion"

class DebugLogger:
    """Enhanced debug logger for pipeline progress tracking"""

    def __init__(self, name: str = "content_pipeline"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Create console handler with formatting
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Track pipeline sessions
        self.active_sessions = {}

    def start_session(self, session_id: str, user_name: str = "Unknown", message: str = ""):
        """Start a new pipeline session"""
        session_data = {
            "session_id": session_id,
            "user_name": user_name,
            "message": message,
            "start_time": datetime.now().isoformat(),
            "steps_completed": [],
            "current_step": None,
            "status": "started"
        }

        self.active_sessions[session_id] = session_data

        self.log_step(
            session_id=session_id,
            step=PipelineStep.WEBHOOK_RECEIVED,
            status="started",
            details={
                "user": user_name,
                "message": message,
                "session_id": session_id
            }
        )

        return session_id

    def log_step(self, session_id: str, step: PipelineStep, status: str = "started",
                 details: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """Log a pipeline step with detailed information"""

        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "session_id": session_id,
            "step": step.value,
            "status": status,
            "details": details or {},
            "error": error
        }

        # Update session if it exists
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["steps_completed"].append(log_entry)
            session["current_step"] = step.value
            session["last_updated"] = timestamp

            if status == "error":
                session["status"] = "failed"
            elif status == "completed":
                session["status"] = "completed"

        # Create formatted log message
        emoji = self._get_step_emoji(step)
        status_icon = "✅" if status == "completed" else "❌" if status == "error" else "🔄"

        message = f"{emoji} {status_icon} Step: {step.value.upper()}"
        if details:
            message += f" | Details: {json.dumps(details, default=str)}"
        if error:
            message += f" | Error: {error}"

        if status == "error":
            self.logger.error(message)
        elif status == "completed":
            self.logger.info(message)
        else:
            self.logger.info(message)

    def log_extraction_result(self, session_id: str, entities: Dict[str, Any]):
        """Log entity extraction results"""
        self.log_step(
            session_id=session_id,
            step=PipelineStep.ENTITY_EXTRACTION,
            status="completed",
            details={
                "schedule_command": entities.get("schedule_command"),
                "topic": entities.get("topic"),
                "keywords": entities.get("keywords")
            }
        )

    def log_schedule_parsing(self, session_id: str, schedule_params: Dict[str, Any]):
        """Log schedule parsing results"""
        self.log_step(
            session_id=session_id,
            step=PipelineStep.SCHEDULE_PARSING,
            status="completed",
            details={
                "total_posts": schedule_params.get("total_posts"),
                "frequency_minutes": schedule_params.get("frequency_minutes"),
                "duration_minutes": schedule_params.get("duration_minutes")
            }
        )

    def log_content_generation(self, session_id: str, crew_result: Any, content_count: int):
        """Log content generation results"""
        self.log_step(
            session_id=session_id,
            step=PipelineStep.CONTENT_GENERATION,
            status="completed",
            details={
                "content_count": content_count,
                "result_type": type(crew_result).__name__
            }
        )

    def log_image_generation(self, session_id: str, image_results: list):
        """Log image generation results"""
        successful_images = len([r for r in image_results if r.get("status") == "success"])
        self.log_step(
            session_id=session_id,
            step=PipelineStep.IMAGE_GENERATION,
            status="completed",
            details={
                "total_images": len(image_results),
                "successful_images": successful_images,
                "failed_images": len(image_results) - successful_images
            }
        )

    def log_scheduling(self, session_id: str, posting_schedule_id: str, content_count: int):
        """Log post scheduling results"""
        self.log_step(
            session_id=session_id,
            step=PipelineStep.POST_SCHEDULING,
            status="completed",
            details={
                "posting_schedule_id": posting_schedule_id,
                "content_count": content_count
            }
        )

    def log_telegram_post(self, session_id: str, post_result: Dict[str, Any]):
        """Log Telegram posting results"""
        status = "completed" if post_result.get("status") == "success" else "error"
        self.log_step(
            session_id=session_id,
            step=PipelineStep.TELEGRAM_POSTING,
            status=status,
            details={
                "post_status": post_result.get("status"),
                "has_image": "image_url" in post_result
            },
            error=post_result.get("error") if status == "error" else None
        )

    def complete_session(self, session_id: str, final_status: str = "completed"):
        """Mark a session as completed"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["status"] = final_status
            session["end_time"] = datetime.now().isoformat()

            self.log_step(
                session_id=session_id,
                step=PipelineStep.COMPLETION,
                status=final_status,
                details={
                    "total_steps": len(session["steps_completed"]),
                    "session_duration": self._calculate_duration(session["start_time"], session["end_time"])
                }
            )

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of a session"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        return {
            "session_id": session_id,
            "user_name": session["user_name"],
            "status": session["status"],
            "start_time": session["start_time"],
            "end_time": session.get("end_time"),
            "steps_completed": session["steps_completed"],
            "total_steps": len(session["steps_completed"])
        }

    def _get_step_emoji(self, step: PipelineStep) -> str:
        """Get emoji for each step"""
        emojis = {
            PipelineStep.WEBHOOK_RECEIVED: "🔔",
            PipelineStep.ENTITY_EXTRACTION: "🔍",
            PipelineStep.SCHEDULE_PARSING: "📅",
            PipelineStep.CONTENT_CREW_INIT: "👥",
            PipelineStep.CONTENT_GENERATION: "✍️",
            PipelineStep.CONTENT_EXTRACTION: "📝",
            PipelineStep.IMAGE_PROMPT_OPTIMIZATION: "🎨",
            PipelineStep.IMAGE_GENERATION: "🖼️",
            PipelineStep.SCHEDULING_INIT: "⏰",
            PipelineStep.POST_SCHEDULING: "📋",
            PipelineStep.TELEGRAM_POSTING: "📤",
            PipelineStep.COMPLETION: "🎉"
        }
        return emojis.get(step, "🔄")

    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        """Calculate duration between two timestamps"""
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            duration = end - start
            return str(duration)
        except:
            return "Unknown"

# Global debug logger instance
debug_logger = DebugLogger()