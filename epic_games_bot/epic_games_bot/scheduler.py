"""
Scheduler module for Epic Games Freebie Auto-Claimer Bot.
Handles scheduling of periodic tasks.
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

class Scheduler:
    """Task scheduler for Epic Games Freebie Auto-Claimer Bot."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler()
        logger.info("Scheduler initialized")
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")
    
    def add_daily_job(self, job_func, hour=12, minute=0, name=None):
        """Add a job to run daily at specified time.
        
        Args:
            job_func: Function to call
            hour: Hour to run job (0-23)
            minute: Minute to run job (0-59)
            name: Job name
        
        Returns:
            Job ID
        """
        trigger = CronTrigger(hour=hour, minute=minute)
        job_id = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            name=name or job_func.__name__
        ).id
        
        logger.info(f"Added daily job '{name or job_func.__name__}' to run at {hour:02d}:{minute:02d}")
        return job_id
    
    def add_interval_job(self, job_func, hours=24, minutes=0, seconds=0, name=None):
        """Add a job to run at specified interval.
        
        Args:
            job_func: Function to call
            hours: Hours between runs
            minutes: Minutes between runs
            seconds: Seconds between runs
            name: Job name
        
        Returns:
            Job ID
        """
        trigger = IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds)
        job_id = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            name=name or job_func.__name__
        ).id
        
        interval_str = ""
        if hours > 0:
            interval_str += f"{hours} hour(s) "
        if minutes > 0:
            interval_str += f"{minutes} minute(s) "
        if seconds > 0:
            interval_str += f"{seconds} second(s)"
        
        logger.info(f"Added interval job '{name or job_func.__name__}' to run every {interval_str.strip()}")
        return job_id
    
    def add_immediate_job(self, job_func, name=None):
        """Add a job to run immediately and only once.
        
        Args:
            job_func: Function to call
            name: Job name
        
        Returns:
            Job ID
        """
        job_id = self.scheduler.add_job(
            job_func,
            name=name or job_func.__name__
        ).id
        
        logger.info(f"Added immediate job '{name or job_func.__name__}'")
        return job_id
    
    def remove_job(self, job_id):
        """Remove a job by ID.
        
        Args:
            job_id: Job ID to remove
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id}")
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
    
    def get_next_run_time(self, job_id):
        """Get the next run time for a job.
        
        Args:
            job_id: Job ID
        
        Returns:
            Next run time as datetime or None
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                return job.next_run_time
            return None
        except Exception as e:
            logger.error(f"Failed to get next run time for job {job_id}: {e}")
            return None
