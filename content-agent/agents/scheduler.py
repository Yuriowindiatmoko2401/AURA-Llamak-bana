from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
import json
import time
import uuid
from enum import Enum

class PostStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PostScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.active_schedules = {}  # Track active posting schedules
        self.post_history = []      # Track completed posts
        self.schedule_queue = []     # Queue for posts waiting to be scheduled

    def parse_schedule_command(self, command: str) -> Dict[str, Any]:
        """
        Parse natural language schedule command like:
        "post each 2 minutes for the next one hour"
        "post daily for 7 days"
        "post every 4 hours for 2 days"

        Args:
            command: Natural language schedule command

        Returns:
            Dictionary with parsed schedule parameters
        """
        command_lower = command.lower()

        # Extract frequency
        frequency_minutes = self._extract_frequency(command_lower)
        frequency_hours = self._extract_frequency_in_hours(command_lower)

        # Extract duration
        duration_hours = self._extract_duration_in_hours(command_lower)
        duration_days = self._extract_duration_in_days(command_lower)

        # Calculate total duration in hours
        total_hours = duration_hours + (duration_days * 24)

        # Calculate number of posts
        if frequency_minutes > 0:
            total_posts = int((total_hours * 60) / frequency_minutes)
        elif frequency_hours > 0:
            total_posts = int(total_hours / frequency_hours)
        else:
            total_posts = 1  # Default to single post

        # Calculate end time
        end_time = datetime.now() + timedelta(hours=total_hours)

        return {
            'frequency_minutes': frequency_minutes,
            'frequency_hours': frequency_hours,
            'total_hours': total_hours,
            'total_posts': total_posts,
            'end_time': end_time.isoformat(),
            'original_command': command,
            'status': 'parsed'
        }

    def _extract_frequency(self, command: str) -> int:
        """Extract frequency in minutes from command"""
        import re

        # Look for patterns like "each 2 minutes", "every 30 minutes", "every 1 min"
        minute_patterns = [
            r'(?:each|every)\s+(\d+)\s+(?:minutes?|mins?)',
            r'(\d+)\s+(?:minutes?|mins?)\s+(?:interval|frequency)',
        ]

        for pattern in minute_patterns:
            match = re.search(pattern, command)
            if match:
                return int(match.group(1))

        # Default values based on common phrases
        if 'hourly' in command:
            return 60
        elif 'daily' in command:
            return 1440  # 24 hours in minutes
        elif 'weekly' in command:
            return 10080  # 7 days in minutes

        return 0  # No minute frequency found

    def _extract_frequency_in_hours(self, command: str) -> int:
        """Extract frequency in hours from command"""
        import re

        hour_patterns = [
            r'(?:each|every)\s+(\d+)\s+hours?',
            r'(\d+)\s+hours?\s+(?:interval|frequency)',
        ]

        for pattern in hour_patterns:
            match = re.search(pattern, command)
            if match:
                return int(match.group(1))

        return 0  # No hour frequency found

    def _extract_duration_in_hours(self, command: str) -> int:
        """Extract duration in hours from command"""
        import re

        hour_patterns = [
            r'(?:for|next)\s+(\d+)\s+hours?',
            r'(\d+)\s+hours?\s+(?:duration|period)',
        ]

        for pattern in hour_patterns:
            match = re.search(pattern, command)
            if match:
                return int(match.group(1))

        return 0

    def _extract_duration_in_days(self, command: str) -> int:
        """Extract duration in days from command"""
        import re

        day_patterns = [
            r'(?:for|next)\s+(\d+)\s+days?',
            r'(\d+)\s+days?\s+(?:duration|period)',
        ]

        for pattern in day_patterns:
            match = re.search(pattern, command)
            if match:
                return int(match.group(1))

        return 0

    def create_posting_schedule(self, content_plan: List[Dict[str, Any]],
                              schedule_params: Dict[str, Any],
                              post_callback: Callable) -> str:
        """
        Create a new posting schedule

        Args:
            content_plan: List of content to post
            schedule_params: Schedule parameters from parse_schedule_command
            post_callback: Function to call for each post

        Returns:
            Schedule ID for tracking
        """
        schedule_id = str(uuid.uuid4())

        # Create schedule info
        schedule_info = {
            'id': schedule_id,
            'created_at': datetime.now().isoformat(),
            'schedule_params': schedule_params,
            'content_plan': content_plan,
            'total_posts': schedule_params['total_posts'],
            'posts_completed': 0,
            'posts_failed': 0,
            'status': 'active',
            'next_post_index': 0
        }

        # Store schedule info
        self.active_schedules[schedule_id] = schedule_info

        # Calculate interval in seconds
        if schedule_params['frequency_minutes'] > 0:
            interval_seconds = schedule_params['frequency_minutes'] * 60
        else:
            interval_seconds = schedule_params['frequency_hours'] * 3600

        # Schedule the posts
        for i in range(schedule_params['total_posts']):
            post_time = datetime.now() + timedelta(seconds=i * interval_seconds)
            content = content_plan[i % len(content_plan)]

            job_id = f"{schedule_id}_post_{i}"

            self.scheduler.add_job(
                func=self._execute_post,
                trigger=DateTrigger(run_date=post_time),
                args=[schedule_id, job_id, content, post_callback],
                id=job_id,
                max_instances=1,
                coalesce=True
            )

        # Schedule cleanup job
        cleanup_time = datetime.now() + timedelta(hours=schedule_params['total_hours'] + 1)
        self.scheduler.add_job(
            func=self._cleanup_schedule,
            trigger=DateTrigger(run_date=cleanup_time),
            args=[schedule_id],
            id=f"{schedule_id}_cleanup",
            max_instances=1
        )

        print(f"Created posting schedule {schedule_id} for {schedule_params['total_posts']} posts")
        return schedule_id

    def _execute_post(self, schedule_id: str, job_id: str, content: Dict[str, Any],
                     post_callback: Callable):
        """Execute a single post"""
        try:
            print(f"Executing post {job_id} for schedule {schedule_id}")

            # Update schedule status
            if schedule_id in self.active_schedules:
                self.active_schedules[schedule_id]['posts_completed'] += 1
                self.active_schedules[schedule_id]['next_post_index'] += 1

            # Create post record
            post_record = {
                'schedule_id': schedule_id,
                'job_id': job_id,
                'content': content,
                'posted_at': datetime.now().isoformat(),
                'status': PostStatus.COMPLETED.value
            }

            # Execute the post callback
            result = post_callback(content)

            # Update post record with result
            post_record['result'] = result
            self.post_history.append(post_record)

            print(f"Post {job_id} completed successfully")

        except Exception as e:
            print(f"Error executing post {job_id}: {e}")

            # Update failure count
            if schedule_id in self.active_schedules:
                self.active_schedules[schedule_id]['posts_failed'] += 1

            # Record failure
            post_record = {
                'schedule_id': schedule_id,
                'job_id': job_id,
                'content': content,
                'posted_at': datetime.now().isoformat(),
                'status': PostStatus.FAILED.value,
                'error': str(e)
            }
            self.post_history.append(post_record)

    def _cleanup_schedule(self, schedule_id: str):
        """Clean up completed schedule"""
        if schedule_id in self.active_schedules:
            schedule_info = self.active_schedules[schedule_id]
            schedule_info['status'] = 'completed'
            schedule_info['completed_at'] = datetime.now().isoformat()

            # Remove from active schedules after some time
            print(f"Schedule {schedule_id} completed. Posts: {schedule_info['posts_completed']}, Failed: {schedule_info['posts_failed']}")

    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause an active schedule"""
        try:
            # Remove all jobs for this schedule
            jobs_to_remove = [job.id for job in self.scheduler.get_jobs() if job.id.startswith(schedule_id) and not job.id.endswith('_cleanup')]
            for job_id in jobs_to_remove:
                self.scheduler.remove_job(job_id)

            # Update status
            if schedule_id in self.active_schedules:
                self.active_schedules[schedule_id]['status'] = 'paused'

            print(f"Paused schedule {schedule_id}")
            return True

        except Exception as e:
            print(f"Error pausing schedule {schedule_id}: {e}")
            return False

    def resume_schedule(self, schedule_id: str, post_callback: Callable) -> bool:
        """Resume a paused schedule"""
        if schedule_id not in self.active_schedules:
            return False

        schedule_info = self.active_schedules[schedule_id]
        if schedule_info['status'] != 'paused':
            return False

        # Calculate remaining posts
        remaining_posts = schedule_info['total_posts'] - schedule_info['posts_completed']
        if remaining_posts <= 0:
            return False

        # Resume from where we left off
        next_index = schedule_info['next_post_index']
        remaining_content = schedule_info['content_plan'][next_index:]

        # Create new parameters for remaining posts
        schedule_params = schedule_info['schedule_params'].copy()
        schedule_params['total_posts'] = remaining_posts

        # Remove old schedule and create new one
        del self.active_schedules[schedule_id]
        new_schedule_id = self.create_posting_schedule(remaining_content, schedule_params, post_callback)

        print(f"Resumed schedule {schedule_id} as {new_schedule_id}")
        return True

    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel an active schedule"""
        try:
            # Remove all jobs for this schedule
            jobs_to_remove = [job.id for job in self.scheduler.get_jobs() if job.id.startswith(schedule_id)]
            for job_id in jobs_to_remove:
                self.scheduler.remove_job(job_id)

            # Update status
            if schedule_id in self.active_schedules:
                self.active_schedules[schedule_id]['status'] = 'cancelled'
                self.active_schedules[schedule_id]['cancelled_at'] = datetime.now().isoformat()

            print(f"Cancelled schedule {schedule_id}")
            return True

        except Exception as e:
            print(f"Error cancelling schedule {schedule_id}: {e}")
            return False

    def get_schedule_status(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific schedule"""
        return self.active_schedules.get(schedule_id)

    def get_all_active_schedules(self) -> List[Dict[str, Any]]:
        """Get all active schedules"""
        return list(self.active_schedules.values())

    def get_post_history(self, schedule_id: Optional[str] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """Get post history, optionally filtered by schedule"""
        history = self.post_history

        if schedule_id:
            history = [post for post in history if post['schedule_id'] == schedule_id]

        # Return most recent posts first
        return sorted(history, key=lambda x: x['posted_at'], reverse=True)[:limit]

    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get overall scheduler statistics"""
        total_posts = len(self.post_history)
        successful_posts = len([p for p in self.post_history if p['status'] == PostStatus.COMPLETED.value])
        failed_posts = len([p for p in self.post_history if p['status'] == PostStatus.FAILED.value])

        active_schedules = len([s for s in self.active_schedules.values() if s['status'] == 'active'])
        paused_schedules = len([s for s in self.active_schedules.values() if s['status'] == 'paused'])

        return {
            'total_posts_posted': total_posts,
            'successful_posts': successful_posts,
            'failed_posts': failed_posts,
            'success_rate': (successful_posts / total_posts * 100) if total_posts > 0 else 0,
            'active_schedules': active_schedules,
            'paused_schedules': paused_schedules,
            'total_schedules': len(self.active_schedules)
        }

    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        print("Scheduler shutdown complete")