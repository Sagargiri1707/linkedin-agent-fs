from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.config import settings
# Import your service functions that the scheduler will call
from app.services.linkedin_agent_service import (
    fetch_and_process_trends_task,
    generate_content_from_trends_task,
    send_pending_approvals_task,
    publish_approved_posts_task,
    track_engagement_task,
    generate_reports_task
)

logger = logging.getLogger(__name__)

# For a personal project, MemoryJobStore is simpler if persistence across restarts isn't critical.
# If you want jobs to persist if the app restarts, use MongoDBJobStore.
# jobstores = {
#    'default': MongoDBJobStore(database=settings.MONGO_DATABASE_NAME,
#                               collection='scheduled_jobs',
#                               client_options={"host": settings.MONGO_CONNECTION_STRING})
# }
jobstores = {
    'default': MemoryJobStore()
}

scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC") # Use UTC for consistency

def add_jobs():
    """
    Adds all scheduled jobs to the scheduler.
    This is where you define what runs and when.
    """
    logger.info("Adding scheduled jobs...")

    # Example Jobs (customize triggers and functions as needed):

    # 1. Fetch and Process Trends
    scheduler.add_job(
        fetch_and_process_trends_task,
        trigger=CronTrigger(hour="*/4", minute="0", day_of_week="*"), # Every 4 hours
        id="fetch_trends_job",
        name="Fetch and Process Trends",
        replace_existing=True
    )

    # 2. Generate Content from New Trends
    scheduler.add_job(
        generate_content_from_trends_task,
        trigger=IntervalTrigger(hours=4, minutes=15), # Every 4h 15m (staggered from fetch)
        id="generate_content_job",
        name="Generate Content from Trends",
        replace_existing=True
    )

    # 3. Send Pending Approvals via WhatsApp
    scheduler.add_job(
        send_pending_approvals_task,
        trigger=IntervalTrigger(minutes=30), # Check for pending approvals every 30 mins
        id="send_approvals_job",
        name="Send Pending Approvals via WhatsApp",
        replace_existing=True
    )

    # 4. Publish Approved Posts to LinkedIn
    scheduler.add_job(
        publish_approved_posts_task,
        trigger=CronTrigger(hour="9,12,15,18", minute="5", day_of_week="mon-fri"), # Specific times on weekdays
        id="publish_posts_job",
        name="Publish Approved Posts to LinkedIn",
        replace_existing=True
    )

    # 5. Track Engagement for Published Posts
    scheduler.add_job(
        track_engagement_task,
        trigger=CronTrigger(hour="10,16", minute="0", day_of_week="*"), # Twice a day
        id="track_engagement_job",
        name="Track Engagement for Published Posts",
        replace_existing=True
    )

    # 6. Generate Performance Reports
    scheduler.add_job(
        generate_reports_task,
        trigger=CronTrigger(day_of_week="sun", hour="20", minute="0"), # Sunday evenings
        id="generate_reports_job",
        name="Generate Performance Reports",
        replace_existing=True
    )

    logger.info("Scheduled jobs added.")

def start_scheduler():
    if not scheduler.running:
        add_jobs()
        scheduler.start()
        logger.info("APScheduler started successfully.")
    else:
        logger.info("APScheduler is already running.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler shut down successfully.") 