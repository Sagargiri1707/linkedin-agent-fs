# app/scheduler.py
# Configures APScheduler for background tasks.

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
# from apscheduler.jobstores.mongodb import MongoDBJobStore # Option for persistent jobs
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging
import datetime # Import datetime

from app.config import settings
# We will import the actual task functions from linkedin_agent_service later.
# For now, we'll define placeholders here or assume they exist.
# from app.services.linkedin_agent_service import (
#    fetch_and_process_trends_task,
#    generate_content_from_trends_task,
#    send_pending_approvals_task,
#    publish_approved_posts_task,
#    track_engagement_task,
#    generate_reports_task,
#    refresh_linkedin_token_if_needed_task
# )

logger = logging.getLogger(__name__)

# --- Placeholder Task Functions ---
# These will be replaced by actual implementations in app.services.linkedin_agent_service
async def placeholder_task(task_name: str):
    logger.info(f"Scheduler: Running placeholder task: {task_name} at {datetime.datetime.now()}")
    # In a real scenario, this would call a function from a service module.

async def fetch_and_process_trends_task():
    await placeholder_task("Fetch and Process Trends")

async def generate_content_from_trends_task():
    await placeholder_task("Generate Content from Trends")

async def send_pending_approvals_task():
    await placeholder_task("Send Pending Approvals via WhatsApp")

async def publish_approved_posts_task():
    await placeholder_task("Publish Approved Posts to LinkedIn")

async def track_engagement_task():
    await placeholder_task("Track Engagement for Published Posts")

async def generate_reports_task():
    await placeholder_task("Generate Performance Reports")

async def refresh_linkedin_token_if_needed_task():
    await placeholder_task("Refresh LinkedIn Access Token if Needed")
# --- End Placeholder Task Functions ---


# Configure Job Stores
# For a personal project, MemoryJobStore is often sufficient if jobs don't need to survive app restarts.
# If persistence is needed (e.g., scheduler remembers jobs even if the app crashes),
# MongoDBJobStore can be used, but it requires the MongoDB client to be running when the scheduler starts.
jobstores = {
    'default': MemoryJobStore()
    # Example for MongoDBJobStore (uncomment and ensure DB is running if you use this):
    # 'default': MongoDBJobStore(
    #     database=settings.MONGO_DATABASE_NAME, # Loaded from config
    #     collection='app_scheduled_jobs',       # Name of the collection to store jobs
    #     client_options={"host": settings.MONGO_CONNECTION_STRING} # Motor client options
    # )
}

# Initialize the scheduler
# timezone="UTC" is recommended for consistency, especially if dealing with users/servers in different timezones.
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")

def add_jobs_to_scheduler():
    """
    Adds all defined jobs to the APScheduler instance.
    This function is called when the scheduler starts.
    Customize triggers (CronTrigger, IntervalTrigger, DateTrigger) as needed.
    """
    logger.info("Adding scheduled jobs to APScheduler...")

    # Job 1: Fetch and Process Trends (e.g., every 4 hours)
    scheduler.add_job(
        fetch_and_process_trends_task,
        trigger=CronTrigger(hour="*/4", minute="5", jitter=120), # Every 4 hours, at 5 past the hour, with up to 120s jitter
        id="fetch_trends_job",
        name="Fetch and Process New Trends",
        replace_existing=True # Replaces the job if one with the same ID already exists
    )

    # Job 2: Generate Content from New Trends (e.g., every 4 hours, offset from fetching)
    scheduler.add_job(
        generate_content_from_trends_task,
        trigger=CronTrigger(hour="*/4", minute="20", jitter=120), # Staggered after trend fetching
        id="generate_content_job",
        name="Generate Content from Identified Trends",
        replace_existing=True
    )

    # Job 3: Send Pending Approvals via WhatsApp (e.g., every 30 minutes)
    # More frequent for responsiveness, but be mindful of API limits and user experience.
    scheduler.add_job(
        send_pending_approvals_task,
        trigger=IntervalTrigger(minutes=30, jitter=60),
        id="send_approvals_job",
        name="Send Pending Content Approvals via WhatsApp",
        replace_existing=True
    )

    # Job 4: Publish Approved Posts to LinkedIn (e.g., specific times on weekdays)
    # Example: Mon-Fri at 9:00 AM, 1:00 PM, 5:00 PM UTC
    scheduler.add_job(
        publish_approved_posts_task,
        trigger=CronTrigger(day_of_week="mon-fri", hour="9,13,17", minute="0", jitter=300),
        id="publish_posts_job",
        name="Publish Approved Posts to LinkedIn",
        replace_existing=True
    )

    # Job 5: Track Engagement for Published Posts (e.g., twice a day)
    scheduler.add_job(
        track_engagement_task,
        trigger=CronTrigger(hour="10,18", minute="30", jitter=120), # e.g., 10:30 AM and 6:30 PM UTC
        id="track_engagement_job",
        name="Track Engagement for Published LinkedIn Posts",
        replace_existing=True
    )

    # Job 6: Generate Performance Reports (e.g., Sunday evening)
    scheduler.add_job(
        generate_reports_task,
        trigger=CronTrigger(day_of_week="sun", hour="20", minute="0", jitter=120), # Sunday at 8:00 PM UTC
        id="generate_reports_job",
        name="Generate Weekly Performance Reports",
        replace_existing=True
    )

    # Job 7: Refresh LinkedIn Token if Needed (e.g., every 12 hours)
    # The token refresh logic in get_stored_linkedin_token might handle this implicitly,
    # but an explicit check can be good.
    scheduler.add_job(
        refresh_linkedin_token_if_needed_task,
        trigger=IntervalTrigger(hours=12, jitter=300),
        id="refresh_linkedin_token_job",
        name="Refresh LinkedIn Access Token if Needed",
        replace_existing=True
    )

    logger.info(f"Scheduled jobs added. Total jobs: {len(scheduler.get_jobs())}")
    # For debugging, you can print the jobs:
    # for job in scheduler.get_jobs():
    #     logger.debug(f"Job: {job.id}, Next Run: {job.next_run_time}")


def start_scheduler():
    """Starts the APScheduler if it's not already running."""
    if not scheduler.running:
        add_jobs_to_scheduler() # Add jobs before starting
        try:
            scheduler.start()
            logger.info("APScheduler started successfully.")
        except Exception as e:
            logger.error(f"Failed to start APScheduler: {e}", exc_info=True)
            # Handle specific exceptions if needed, e.g., related to MongoDBJobStore connection
    else:
        logger.info("APScheduler is already running.")

def shutdown_scheduler(wait: bool = True):
    """Shuts down the APScheduler."""
    if scheduler.running:
        try:
            scheduler.shutdown(wait=wait) # `wait=True` waits for running jobs to complete
            logger.info("APScheduler shut down successfully.")
        except Exception as e:
            logger.error(f"Error during APScheduler shutdown: {e}", exc_info=True)

# Example of how to list jobs (for debugging)
# def list_scheduled_jobs():
#     if scheduler.running:
#         print("Currently scheduled jobs:")
#         for job in scheduler.get_jobs():
#             print(f"  ID: {job.id}, Name: {job.name}, Trigger: {job.trigger}, Next Run: {job.next_run_time}")
#     else:
#         print("Scheduler is not running.")
