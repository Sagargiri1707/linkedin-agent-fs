import logging
from typing import Optional
from app.database import get_database
from app.models import Trend, PostDraft, PostStatus
from app.services.external_apis import (
    get_trends_from_perplexity,
    generate_text_with_deepseek,
    generate_image_with_ideogram,
    send_whatsapp_message,
    post_to_linkedin,
    get_stored_linkedin_token
)
from app.config import settings
import datetime
from bson import ObjectId

logger = logging.getLogger(__name__)

async def fetch_and_process_trends_task():
    """
    Scheduled task: Fetches trends from Perplexity, processes, and stores them.
    """
    logger.info("Scheduler: Starting fetch_and_process_trends_task...")
    db = await get_database()
    # Example: Define industries or queries based on user config (not implemented here)
    queries = ["AI in marketing", "Future of remote work"]
    for query in queries:
        try:
            raw_trend_data = await get_trends_from_perplexity(query=query, industry="general") # Placeholder industry
            if raw_trend_data:
                # Process raw_trend_data into your Trend model
                # This is highly dependent on Perplexity's actual API response
                trend = Trend(
                    topic=raw_trend_data.get("mock_trend_data", f"Trend for {query}"),
                    source="perplexity_api",
                    relevance_score=0.8, # Example
                    summary=raw_trend_data.get("summary", "Mock summary."),
                    raw_data=raw_trend_data
                )
                # Avoid duplicates - check if a similar trend already exists
                existing_trend = await db.trends.find_one({"topic": trend.topic, "source": trend.source})
                if not existing_trend:
                    await db.trends.insert_one(trend.model_dump(by_alias=True, exclude_none=True))
                    logger.info(f"New trend stored: {trend.topic}")
                else:
                    logger.info(f"Trend already exists, skipping: {trend.topic}")
        except Exception as e:
            logger.error(f"Error processing trend for query '{query}': {e}", exc_info=True)
    logger.info("Scheduler: Finished fetch_and_process_trends_task.")

async def generate_content_from_trends_task():
    """
    Scheduled task: Finds new trends and generates content drafts.
    """
    logger.info("Scheduler: Starting generate_content_from_trends_task...")
    db = await get_database()
    # Find trends that haven't been processed recently (e.g., last_processed_at is null or old)
    # For simplicity, let's just find one unprocessed trend
    one_hour_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    new_trend_doc = await db.trends.find_one(
        {"last_processed_at": {"$lt": one_hour_ago}} # Or {"$exists": False} for never processed
    )

    if new_trend_doc:
        trend = Trend(**new_trend_doc)
        logger.info(f"Processing trend for content generation: {trend.topic}")
        await process_new_trend_for_content_generation(trend)
        # Mark as processed
        await db.trends.update_one(
            {"_id": trend.id},
            {"$set": {"last_processed_at": datetime.datetime.now(datetime.timezone.utc)}}
        )
    else:
        logger.info("No new trends found for content generation at this time.")
    logger.info("Scheduler: Finished generate_content_from_trends_task.")

async def process_new_trend_for_content_generation(trend: Trend):
    """
    Generates content (text and image) for a given trend and saves it as a draft.
    """
    db = await get_database()
    try:
        # 1. Generate Text using DeepSeek
        # You'd load voice profile examples from the user's "voice data sheet"
        # For now, using a placeholder.
        voice_examples = [
            "Example Post 1: AI is transforming industries at an unprecedented pace. #AI #Innovation",
            "Example Post 2: Embracing remote work? Here are my top 3 productivity hacks. #RemoteWork #Productivity"
        ]
        text_prompt = f"Write a LinkedIn post about the trend: {trend.topic}. Summary: {trend.summary or 'N/A'}"
        generated_text = await generate_text_with_deepseek(prompt=text_prompt, voice_profile_examples=voice_examples)

        if not generated_text:
            logger.error(f"Failed to generate text for trend: {trend.topic}")
            return

        # 2. Generate Image Prompt (optional, can be derived from text or trend)
        image_gen_prompt = f"A professional and engaging visual representing the concept of '{trend.topic}', suitable for a LinkedIn post. Clean, modern, abstract or conceptual."

        # 3. Generate Image using Ideogram
        ideogram_result = await generate_image_with_ideogram(prompt=image_gen_prompt)
        generated_image_url = None
        ideogram_job_id = None
        if ideogram_result:
            generated_image_url = ideogram_result.get("image_url")
            ideogram_job_id = ideogram_result.get("job_id")

        # 4. Create and Save PostDraft
        post_draft = PostDraft(
            trend_id=trend.id,
            headline_suggestion=f"Insights on: {trend.topic}",
            generated_text=generated_text,
            image_prompt=image_gen_prompt,
            generated_image_url=generated_image_url,
            ideogram_job_id=ideogram_job_id,
            status=PostStatus.PENDING_APPROVAL # Ready for approval
        )
        insert_result = await db.post_drafts.insert_one(post_draft.model_dump(by_alias=True, exclude_none=True))
        logger.info(f"New post draft created for trend '{trend.topic}' with ID: {insert_result.inserted_id}")

    except Exception as e:
        logger.error(f"Error during content generation for trend '{trend.topic}': {e}", exc_info=True)

async def send_pending_approvals_task():
    """
    Scheduled task: Finds drafts pending approval and sends them via WhatsApp.
    """
    logger.info("Scheduler: Starting send_pending_approvals_task...")
    db = await get_database()
    pending_drafts_cursor = db.post_drafts.find({"status": PostStatus.PENDING_APPROVAL, "approval_message_sid": {"$exists": False}})
    async for draft_doc in pending_drafts_cursor:
        draft = PostDraft(**draft_doc)
        logger.info(f"Found draft pending approval: {draft.id} - '{draft.headline_suggestion}'")
        
        message_body = f"LinkedIn Draft for Approval:\n\nHeadline: {draft.headline_suggestion}\n\nText: {draft.generated_text[:200]}...\n\n"
        if draft.generated_image_url:
            message_body += f"Image: {draft.generated_image_url}\n\n"
        message_body += f"Reply with 'APPROVE {draft.id}' or 'REJECT {draft.id}'."
        
        # In a real app, USER_WHATSAPP_NUMBER would come from user config
        message_sid = send_whatsapp_message(
            to_number=settings.USER_WHATSAPP_NUMBER,
            message_body=message_body
            # media_url=str(draft.generated_image_url) if draft.generated_image_url else None # Twilio needs publicly accessible URLs for media
        )
        if message_sid:
            await db.post_drafts.update_one(
                {"_id": draft.id},
                {"$set": {"approval_message_sid": message_sid, "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
            )
            logger.info(f"Approval request sent for draft {draft.id}, SID: {message_sid}")
        else:
            logger.error(f"Failed to send approval request for draft {draft.id}")
    logger.info("Scheduler: Finished send_pending_approvals_task.")

async def handle_whatsapp_approval(from_number: str, message_body: str, message_sid: str):
    """
    Handles incoming WhatsApp messages, specifically for approving or rejecting drafts.
    Triggered by the Twilio webhook.
    """
    logger.info(f"Handling WhatsApp approval: From={from_number}, Body='{message_body}', SID={message_sid}")
    db = await get_database()
    
    # Basic parsing, improve this for robustness
    parts = message_body.upper().split()
    if len(parts) != 2:
        logger.warning(f"Could not parse approval command: {message_body}")
        # Optionally send a reply back to user about format
        return

    command, draft_id_str = parts[0], parts[1]

    try:
        draft_obj_id = ObjectId(draft_id_str)
    except Exception:
        logger.warning(f"Invalid Draft ID format: {draft_id_str}")
        # Optionally send a reply back
        return

    draft_doc = await db.post_drafts.find_one({"_id": draft_obj_id, "status": PostStatus.PENDING_APPROVAL})
    if not draft_doc:
        logger.warning(f"No pending draft found with ID {draft_id_str} or it's not pending approval.")
        # Optionally send a reply back
        return

    draft = PostDraft(**draft_doc)
    new_status = None
    reply_message = ""

    if command == "APPROVE":
        new_status = PostStatus.APPROVED
        # You might want to set a scheduled_publish_time here based on optimal timing logic
        # For now, just marking as approved. The publish_approved_posts_task will pick it up.
        reply_message = f"Draft '{draft.headline_suggestion}' (ID: {draft_id_str}) has been APPROVED."
        logger.info(f"Draft {draft.id} approved by user.")
    elif command == "REJECT":
        new_status = PostStatus.REJECTED
        reply_message = f"Draft '{draft.headline_suggestion}' (ID: {draft_id_str}) has been REJECTED."
        logger.info(f"Draft {draft.id} rejected by user.")
    else:
        logger.warning(f"Unknown command '{command}' for draft {draft.id}")
        reply_message = f"Sorry, I didn't understand '{command}'. Please use APPROVE or REJECT."
        send_whatsapp_message(to_number=from_number, message_body=reply_message)
        return

    if new_status:
        await db.post_drafts.update_one(
            {"_id": draft.id},
            {"$set": {"status": new_status, "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
        )
        send_whatsapp_message(to_number=from_number, message_body=reply_message)

async def publish_approved_posts_task():
    """
    Scheduled task: Finds approved posts and publishes them to LinkedIn.
    """
    logger.info("Scheduler: Starting publish_approved_posts_task...")
    db = await get_database()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Find posts that are approved AND ( (scheduled_publish_time is past) OR (no scheduled_publish_time meaning post immediately) )
    query = {
        "status": PostStatus.APPROVED,
        "linkedin_post_id": {"$exists": False}  # Not yet published
    }
    
    # Add scheduled time condition if needed
    scheduled_query = {"$or": [
        {"scheduled_publish_time": {"$lte": now}},
        {"scheduled_publish_time": {"$exists": False}}
    ]}
    
    # Combine queries
    query.update(scheduled_query)
    
    approved_drafts_cursor = db.post_drafts.find(query)
    
    # Get the LinkedIn token (no need to pass any access token directly)
    token_data = await get_stored_linkedin_token()
    if not token_data or "access_token" not in token_data:
        logger.error("Cannot publish posts: LinkedIn access token not available or invalid.")
        return

    async for draft_doc in approved_drafts_cursor:
        draft = PostDraft(**draft_doc)
        logger.info(f"Attempting to publish approved draft: {draft.id} - '{draft.headline_suggestion}'")
        try:
            # Post to LinkedIn without directly passing an access token
            # The post_to_linkedin function now handles token retrieval itself
            linkedin_post_id = await post_to_linkedin(
                content_text=draft.generated_text,
                image_url=str(draft.generated_image_url) if draft.generated_image_url else None
            )
            
            if linkedin_post_id:
                await db.post_drafts.update_one(
                    {"_id": draft.id},
                    {"$set": {
                        "status": PostStatus.PUBLISHED,
                        "linkedin_post_id": linkedin_post_id,
                        "updated_at": datetime.datetime.now(datetime.timezone.utc)
                    }}
                )
                logger.info(f"Successfully published draft {draft.id} to LinkedIn, post ID: {linkedin_post_id}")
                
                # Notify the user via WhatsApp (optional)
                notification = f"🎉 Your post '{draft.headline_suggestion}' has been published to LinkedIn successfully!"
                send_whatsapp_message(to_number=settings.USER_WHATSAPP_NUMBER, message_body=notification)
            else:
                logger.error(f"Failed to publish draft {draft.id} to LinkedIn: Post ID not returned")
                await db.post_drafts.update_one(
                    {"_id": draft.id},
                    {"$set": {
                        "status": PostStatus.ERROR,
                        "error_message": "Failed to post to LinkedIn: No post ID returned",
                        "updated_at": datetime.datetime.now(datetime.timezone.utc)
                    }}
                )
        except Exception as e:
            logger.error(f"Error publishing draft {draft.id} to LinkedIn: {e}", exc_info=True)
            await db.post_drafts.update_one(
                {"_id": draft.id},
                {"$set": {
                    "status": PostStatus.ERROR,
                    "error_message": f"Error: {str(e)}",
                    "updated_at": datetime.datetime.now(datetime.timezone.utc)
                }}
            )
    logger.info("Scheduler: Finished publish_approved_posts_task.")

async def track_engagement_task():
    """
    Scheduled task: Tracks engagement metrics for published posts.
    """
    logger.info("Scheduler: Starting track_engagement_task...")
    db = await get_database()
    
    # Get published posts to track engagement
    published_posts_cursor = db.post_drafts.find({
        "status": PostStatus.PUBLISHED,
        "linkedin_post_id": {"$exists": True, "$ne": None}
    })
    
    token_data = await get_stored_linkedin_token()
    if not token_data or "access_token" not in token_data:
        logger.error("Cannot track engagement: LinkedIn access token not available or invalid.")
        return
    
    access_token = token_data["access_token"]
    
    async for post_doc in published_posts_cursor:
        post = PostDraft(**post_doc)
        if not post.linkedin_post_id:
            continue
            
        # This is a placeholder as we would need to implement this function
        # based on LinkedIn's Social Engagement API
        # For now, we'll log that we would track engagement
        logger.info(f"Would track engagement for LinkedIn post: {post.linkedin_post_id}")
        
        # In a real implementation, you would:
        # 1. Call LinkedIn's API to get engagement metrics
        # 2. Store those metrics in your database
        # 3. Possibly generate insights or notifications based on engagement trends
        
    logger.info("Scheduler: Finished track_engagement_task.")

async def generate_reports_task():
    """
    Scheduled task: Generates performance reports.
    """
    logger.info("Scheduler: Starting generate_reports_task...")
    # Fetch analytics data from DB, compile report, maybe send via WhatsApp/Email
    logger.warning("generate_reports_task is a placeholder.")
    logger.info("Scheduler: Finished generate_reports_task.") 