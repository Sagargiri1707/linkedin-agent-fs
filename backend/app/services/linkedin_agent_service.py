# app/services/linkedin_agent_service.py
# Contains the core business logic for the LinkedIn automation agent.
# Orchestrates calls to external APIs and interacts with the database.

import logging
from typing import Optional, List, Dict, Any # Ensure Any is imported
from app.database import get_database
from app.models import Trend, PostDraft, PostStatus, LinkedInToken # Import all necessary models
from app.services.external_apis import (
    get_trends_from_perplexity,
    generate_text_with_deepseek,
    generate_image_with_ideogram,
    send_whatsapp_message,
    post_content_to_linkedin, # Updated to post_content_to_linkedin
    get_stored_linkedin_token,
    refresh_linkedin_token, # Explicit refresh if needed, though get_stored_linkedin_token handles it
    get_linkedin_engagement,
    register_linkedin_image_asset, # For image uploads
    upload_linkedin_image # For image uploads
)
from app.config import settings
import datetime
from bson import ObjectId # For converting string IDs to ObjectId if necessary

logger = logging.getLogger(__name__)

# Define a default user ID for this personal project context
DEFAULT_USER_ID = "default_personal_user"

async def fetch_and_process_trends_task():
    """
    Scheduled task: Fetches trends from Perplexity, processes, and stores them.
    """
    logger.info("Scheduler Task: Starting fetch_and_process_trends_task...")
    db = await get_database()
    # Example: Define industries or queries based on user config (not implemented here, using defaults)
    # In a real app, these might come from a user settings collection in the DB.
    queries_and_industries = [
        {"query": "AI in content marketing", "industry": "Marketing"},
        {"query": "Future of remote collaboration tools", "industry": "Technology"},
        {"query": "Sustainable energy breakthroughs", "industry": "Energy"}
    ]

    for item in queries_and_industries:
        query = item["query"]
        industry = item["industry"]
        try:
            logger.info(f"Fetching trends for query: '{query}', industry: '{industry}'")
            raw_trend_data = await get_trends_from_perplexity(query=query, industry=industry)
            
            if raw_trend_data and raw_trend_data.get("summary"): # Check if we got a summary
                # Process raw_trend_data into your Trend model
                trend = Trend(
                    topic=f"Trend for '{query}': {raw_trend_data.get('summary', 'N/A')[:100]}...", # Make topic more descriptive
                    source="perplexity_api",
                    relevance_score=raw_trend_data.get("relevance_score", 0.8), # Example, if Perplexity provided it
                    summary=raw_trend_data.get("summary"),
                    raw_data=raw_trend_data # Store the full response for potential future use
                )
                # Avoid duplicates - check if a similar trend (e.g., by summary) already exists
                existing_trend = await db.trends.find_one({"summary": trend.summary, "source": trend.source})
                if not existing_trend:
                    insert_result = await db.trends.insert_one(trend.model_dump(by_alias=True, exclude_none=True))
                    logger.info(f"New trend stored: {trend.topic} (ID: {insert_result.inserted_id})")
                else:
                    logger.info(f"Trend based on summary already exists, skipping: {trend.topic}")
            else:
                logger.warning(f"No valid trend data or summary received from Perplexity for query: '{query}'")

        except Exception as e:
            logger.error(f"Error processing trend for query '{query}', industry '{industry}': {e}", exc_info=True)
    logger.info("Scheduler Task: Finished fetch_and_process_trends_task.")


async def generate_content_from_trends_task():
    """
    Scheduled task: Finds new/unprocessed trends and generates content drafts (text and image).
    """
    logger.info("Scheduler Task: Starting generate_content_from_trends_task...")
    db = await get_database()
    
    # Find trends that haven't been processed recently (e.g., last_processed_at is null or older than X hours)
    # Process a limited number of trends per run to avoid overwhelming APIs or running too long.
    processing_limit = 3 # Max trends to process in one go
    cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6) # Process if older than 6 hours

    unprocessed_trends_cursor = db.trends.find({
        "$or": [
            {"last_processed_at": {"$lt": cutoff_time}},
            {"last_processed_at": {"$exists": False}}
        ]
    }).limit(processing_limit)

    trends_found = 0
    async for trend_doc in unprocessed_trends_cursor:
        trends_found += 1
        trend = Trend(**trend_doc)
        logger.info(f"Processing trend ID {trend.id} ('{trend.topic}') for content generation.")
        
        await _process_single_trend_for_content(trend) # Helper function
        
        # Mark as processed (or update last_processed_at)
        await db.trends.update_one(
            {"_id": trend.id},
            {"$set": {"last_processed_at": datetime.datetime.now(datetime.timezone.utc)}}
        )
    
    if trends_found == 0:
        logger.info("No new or old unprocessed trends found for content generation at this time.")
    logger.info("Scheduler Task: Finished generate_content_from_trends_task.")

async def _process_single_trend_for_content(trend: Trend):
    """
    Helper function: Generates content (text and image) for a single trend and saves it as a draft.
    """
    db = await get_database()
    try:
        # 1. Load Voice Profile Examples (placeholder - load from config/DB in real app)
        # This should be configurable per user if the app supports multiple users.
        voice_examples = [
            "Example Post 1: AI is transforming industries at an unprecedented pace. Key takeaway: Adapt or be left behind. #AI #Innovation #FutureTech",
            "Example Post 2: Embracing remote work? Here are my top 3 productivity hacks for staying focused and delivering results. What are yours? #RemoteWork #Productivity #WorkFromHome"
        ]
        
        # 2. Generate Text using DeepSeek
        text_prompt = (
            f"Craft an engaging and insightful LinkedIn post about the following trend: '{trend.topic}'.\n"
            f"Key summary points: {trend.summary}\n"
            f"The post should be suitable for a professional audience, offer a unique perspective or actionable advice if possible, "
            f"and include 2-3 relevant hashtags."
        )
        generated_text = await generate_text_with_deepseek(prompt=text_prompt, voice_profile_examples=voice_examples)

        if not generated_text:
            logger.error(f"Failed to generate text for trend: {trend.topic} (ID: {trend.id})")
            return # Skip this trend if text generation fails

        # 3. Generate Image Prompt (can be derived from text or trend)
        image_gen_prompt = f"A professional, modern, and visually appealing image representing the concept of '{trend.topic}'. Suitable for a LinkedIn post. Abstract or conceptual art is preferred. Avoid text in the image unless explicitly part of the concept."

        # 4. Generate Image using Ideogram
        ideogram_result = await generate_image_with_ideogram(prompt=image_gen_prompt, aspect_ratio="16:9") # Common LinkedIn aspect ratio
        
        generated_image_url_str: Optional[str] = None
        if ideogram_result and ideogram_result.get("image_url"):
            generated_image_url_str = str(ideogram_result.get("image_url"))

        # 5. Create and Save PostDraft
        post_draft_data = {
            "trend_id": trend.id,
            "headline_suggestion": f"Exploring the Impact of: {trend.topic[:150]}", # Generate a more catchy headline if needed
            "generated_text": generated_text,
            "image_prompt": image_gen_prompt,
            "generated_image_url": generated_image_url_str, # Store as string
            "ideogram_job_id": ideogram_result.get("job_id") if ideogram_result else None,
            "status": PostStatus.PENDING_APPROVAL, # Ready for WhatsApp approval
            "voice_profile_used": "default_personal_voice" # Example
        }
        post_draft = PostDraft(**post_draft_data) # Validate with Pydantic model
        insert_result = await db.post_drafts.insert_one(post_draft.model_dump(by_alias=True, exclude_none=True))
        logger.info(f"New post draft created for trend '{trend.topic}' (Trend ID: {trend.id}) with Draft ID: {insert_result.inserted_id}")

    except Exception as e:
        logger.error(f"Error during content generation for trend '{trend.topic}' (ID: {trend.id}): {e}", exc_info=True)


async def send_pending_approvals_task():
    """
    Scheduled task: Finds drafts pending approval and sends them via WhatsApp.
    """
    logger.info("Scheduler Task: Starting send_pending_approvals_task...")
    db = await get_database()
    
    # Find drafts that are PENDING_APPROVAL and haven't had an approval message sent yet
    pending_drafts_cursor = db.post_drafts.find({
        "status": PostStatus.PENDING_APPROVAL, 
        "approval_message_sid": {"$exists": False} # Only process if SID is not set
    }).limit(5) # Send a few at a time to avoid flooding

    drafts_processed = 0
    async for draft_doc in pending_drafts_cursor:
        drafts_processed += 1
        draft = PostDraft(**draft_doc)
        logger.info(f"Found draft pending approval: ID {draft.id} - '{draft.headline_suggestion}'")
        
        message_body = (
            f"📝 LinkedIn Draft for Approval (ID: {draft.id}):\n\n"
            f"💡 Headline: {draft.headline_suggestion}\n\n"
            f"✍️ Text: {draft.generated_text[:300]}...\n\n" # Truncate for WhatsApp preview
        )
        
        media_url_to_send: Optional[str] = None
        if draft.generated_image_url:
            media_url_to_send = str(draft.generated_image_url) # Ensure it's a string
            message_body += f"🖼️ Image Preview: {media_url_to_send}\n\n"
        
        message_body += f"➡️ Reply with 'APPROVE {draft.id}' or 'REJECT {draft.id}'."
        
        message_sid = send_whatsapp_message(
            to_number=settings.USER_WHATSAPP_NUMBER, # From .env
            message_body=message_body,
            media_url=media_url_to_send if media_url_to_send else None # Twilio needs publicly accessible URLs for media
        )
        
        if message_sid:
            await db.post_drafts.update_one(
                {"_id": draft.id},
                {"$set": {"approval_message_sid": message_sid, "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
            )
            logger.info(f"Approval request sent for draft {draft.id}, Twilio SID: {message_sid}")
        else:
            logger.error(f"Failed to send WhatsApp approval request for draft {draft.id}. Will retry later.")
            # Consider adding a retry counter or error flag to the draft
    
    if drafts_processed == 0:
        logger.info("No drafts currently pending WhatsApp approval notification.")
    logger.info("Scheduler Task: Finished send_pending_approvals_task.")


async def handle_whatsapp_approval(from_number: str, message_body: str, incoming_message_sid: str):
    """
    Handles incoming WhatsApp messages from the user, specifically for approving or rejecting drafts.
    This function is triggered by the Twilio webhook in main.py.
    """
    logger.info(f"Handling WhatsApp approval command: From='{from_number}', Body='{message_body}', SID='{incoming_message_sid}'")
    db = await get_database()
    
    # Basic parsing: expecting "COMMAND DRAFT_ID" (e.g., "APPROVE 60c72b2f9b1e8b3b2c8d4b1f")
    parts = message_body.upper().strip().split()
    if len(parts) != 2:
        logger.warning(f"Could not parse approval command: '{message_body}'. Expected 'COMMAND DRAFT_ID'.")
        reply_text = "😕 Invalid command format. Please use 'APPROVE DRAFT_ID' or 'REJECT DRAFT_ID'."
        send_whatsapp_message(to_number=from_number, message_body=reply_text)
        return

    command, draft_id_str = parts[0], parts[1]

    try:
        # Validate if draft_id_str is a valid ObjectId string
        if not ObjectId.is_valid(draft_id_str):
            raise ValueError("Invalid ObjectId format")
        draft_obj_id = ObjectId(draft_id_str)
    except Exception:
        logger.warning(f"Invalid Draft ID format received: {draft_id_str}")
        reply_text = f"⚠️ Invalid Draft ID format: '{draft_id_str}'. Please check the ID from the approval request."
        send_whatsapp_message(to_number=from_number, message_body=reply_text)
        return

    # Find the draft by its ObjectId
    draft_doc = await db.post_drafts.find_one({"_id": draft_obj_id})
    if not draft_doc:
        logger.warning(f"No draft found with ID {draft_id_str}.")
        reply_text = f"🤷 Sorry, I couldn't find a draft with ID {draft_id_str}. It might have been processed already."
        send_whatsapp_message(to_number=from_number, message_body=reply_text)
        return
    
    draft = PostDraft(**draft_doc)
    
    # Check if the draft is actually pending approval
    if draft.status != PostStatus.PENDING_APPROVAL:
        logger.warning(f"Draft {draft.id} is not pending approval. Current status: {draft.status}.")
        reply_text = f"ℹ️ Draft {draft.id} ('{draft.headline_suggestion}') is no longer pending approval. Its current status is: {draft.status.value}."
        send_whatsapp_message(to_number=from_number, message_body=reply_text)
        return

    new_status: Optional[PostStatus] = None
    reply_message_to_user = ""
    update_fields: Dict[str, Any] = {"updated_at": datetime.datetime.now(datetime.timezone.utc)}


    if command == "APPROVE":
        new_status = PostStatus.APPROVED
        # Basic scheduling: set to publish in a few minutes for testing, or implement smarter logic based on optimal times
        # The publish_approved_posts_task will pick it up based on its own schedule or if scheduled_publish_time is past.
        update_fields["scheduled_publish_time"] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10) # Example: schedule for 10 mins later
        reply_message_to_user = f"✅ Approved! Draft '{draft.headline_suggestion}' (ID: {draft_id_str}) is now scheduled for posting."
        logger.info(f"Draft {draft.id} approved by user {from_number}.")
    elif command == "REJECT":
        new_status = PostStatus.REJECTED
        reply_message_to_user = f"❌ Rejected. Draft '{draft.headline_suggestion}' (ID: {draft_id_str}) will not be posted."
        logger.info(f"Draft {draft.id} rejected by user {from_number}.")
    else:
        logger.warning(f"Unknown command '{command}' received for draft {draft.id} from {from_number}")
        reply_message_to_user = f"😕 Sorry, I didn't understand '{command}'. Please use 'APPROVE {draft_id_str}' or 'REJECT {draft_id_str}'."
        send_whatsapp_message(to_number=from_number, message_body=reply_message_to_user)
        return # No status update needed

    if new_status:
        update_fields["status"] = new_status
        await db.post_drafts.update_one(
            {"_id": draft.id},
            {"$set": update_fields}
        )
        send_whatsapp_message(to_number=from_number, message_body=reply_message_to_user)


async def publish_approved_posts_task():
    """
    Scheduled task: Finds approved and scheduled posts and publishes them to LinkedIn.
    """
    logger.info("Scheduler Task: Starting publish_approved_posts_task...")
    db = await get_database()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Find posts that are APPROVED and their scheduled_publish_time is now or in the past
    # and have not yet been published (linkedin_post_id is not set).
    approved_drafts_cursor = db.post_drafts.find({
        "status": PostStatus.APPROVED,
        "scheduled_publish_time": {"$lte": now},
        "linkedin_post_id": {"$exists": False} # Only publish if not already published
    }).limit(3) # Publish a few at a time

    linkedin_token_obj: Optional[LinkedInToken] = await get_stored_linkedin_token(DEFAULT_USER_ID)
    if not linkedin_token_obj or not linkedin_token_obj.access_token:
        logger.error("Cannot publish posts: LinkedIn access token not available or expired for user {DEFAULT_USER_ID}.")
        return # Cannot proceed without a valid token
    
    access_token = linkedin_token_obj.access_token
    author_urn = linkedin_token_obj.user_urn # Get URN from stored token, essential for posting

    drafts_published_count = 0
    async for draft_doc in approved_drafts_cursor:
        draft = PostDraft(**draft_doc)
        logger.info(f"Attempting to publish approved draft ID: {draft.id} - '{draft.headline_suggestion}'")
        
        image_asset_urn_for_post: Optional[str] = None
        # Placeholder for actual image upload flow:
        # If you have a generated_image_url and want to upload it as a native image:
        # 1. Download the image from draft.generated_image_url (if it's a URL)
        # 2. Call register_linkedin_image_asset(access_token, author_urn)
        # 3. If successful, call upload_linkedin_image(upload_url, image_bytes_or_path, access_token)
        # 4. Use the returned asset URN for image_asset_urn_for_post
        # For now, we'll assume image_asset_urn is not available or we use article_link if draft.generated_image_url exists.
        
        article_link_for_post: Optional[str] = None
        if draft.generated_image_url: # Using image URL as an article link for simplicity
            article_link_for_post = str(draft.generated_image_url)
            logger.info(f"Using generated image URL as article link for post {draft.id}: {article_link_for_post}")


        try:
            linkedin_post_urn = await post_content_to_linkedin(
                access_token=access_token,
                author_urn=author_urn,
                content_text=draft.generated_text,
                image_asset_urn=image_asset_urn_for_post, # Pass actual asset URN if image uploaded
                article_link=article_link_for_post # Or pass article link
            )
            
            if linkedin_post_urn:
                await db.post_drafts.update_one(
                    {"_id": draft.id},
                    {"$set": {
                        "status": PostStatus.PUBLISHED,
                        "linkedin_post_id": linkedin_post_urn, # Store the returned URN of the post
                        "linkedin_author_urn": author_urn,
                        "updated_at": datetime.datetime.now(datetime.timezone.utc), # Record actual publish time
                        "error_message": None # Clear any previous error
                    }}
                )
                drafts_published_count +=1
                logger.info(f"Successfully published draft {draft.id} to LinkedIn. Post URN: {linkedin_post_urn}")
                # Notify user of successful post
                send_whatsapp_message(settings.USER_WHATSAPP_NUMBER, f"🚀 Successfully published to LinkedIn: '{draft.headline_suggestion}' (Post URN: {linkedin_post_urn})")
            else: # API call was made but no URN returned, implies failure at LinkedIn's end or our parsing
                error_msg = "Failed to publish to LinkedIn (API returned no URN or an error occurred)"
                await db.post_drafts.update_one(
                    {"_id": draft.id},
                    {"$set": {"status": PostStatus.ERROR, "error_message": error_msg, "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
                )
                logger.error(f"{error_msg} for draft {draft.id}.")
        except Exception as e:
            logger.error(f"Exception during publishing draft {draft.id}: {e}", exc_info=True)
            await db.post_drafts.update_one(
                {"_id": draft.id},
                {"$set": {"status": PostStatus.ERROR, "error_message": str(e), "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
            )
    if drafts_published_count == 0 and await db.post_drafts.count_documents({"status": PostStatus.APPROVED, "scheduled_publish_time": {"$lte": now}, "linkedin_post_id": {"$exists": False}}) > 0:
        logger.info("No drafts were published in this run, but there are approved drafts scheduled for now or past.")
    elif drafts_published_count > 0:
        logger.info(f"Published {drafts_published_count} drafts in this run.")
    else:
        logger.info("No approved drafts ready for publishing at this time.")
    logger.info("Scheduler Task: Finished publish_approved_posts_task.")


async def track_engagement_task():
    """
    Scheduled task: Fetches engagement for recently published posts.
    """
    logger.info("Scheduler Task: Starting track_engagement_task...")
    db = await get_database()
    linkedin_token_obj = await get_stored_linkedin_token(DEFAULT_USER_ID)
    
    if not linkedin_token_obj or not linkedin_token_obj.access_token:
        logger.error("Cannot track engagement: LinkedIn access token not available for user {DEFAULT_USER_ID}.")
        return

    # Find posts published in the last 7 days that have a linkedin_post_id
    # and haven't been checked for engagement recently (e.g., in last 6 hours)
    seven_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    six_hours_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6)

    published_posts_cursor = db.post_drafts.find({
        "status": PostStatus.PUBLISHED,
        "linkedin_post_id": {"$exists": True, "$ne": None},
        "updated_at": {"$gte": seven_days_ago}, # Consider posts published recently
        "$or": [ # And either never checked or not checked recently
            {"engagement_last_checked": {"$lt": six_hours_ago}},
            {"engagement_last_checked": {"$exists": False}}
        ]
    }).limit(10) # Check a few posts at a time

    posts_checked = 0
    async for post_doc in published_posts_cursor:
        posts_checked += 1
        post = PostDraft(**post_doc)
        if post.linkedin_post_id: # Should always be true due to query
            logger.info(f"Tracking engagement for LinkedIn post URN: {post.linkedin_post_id}")
            engagement_data = await get_linkedin_engagement(linkedin_token_obj.access_token, post.linkedin_post_id)
            
            if engagement_data:
                await db.post_drafts.update_one(
                    {"_id": post.id},
                    {"$set": {
                        "engagement_stats": engagement_data.get("raw_data"), # Store the raw API response or parsed stats
                        "engagement_last_checked": datetime.datetime.now(datetime.timezone.utc)
                    }}
                )
                logger.info(f"Engagement for post {post.linkedin_post_id}: Likes={engagement_data.get('likes',0)}, Comments={engagement_data.get('comments',0)}")
            else:
                logger.warning(f"Could not fetch engagement for post {post.linkedin_post_id}. Will retry later.")
                # Optionally update 'engagement_last_checked' even on failure to avoid immediate retries on problematic posts
                await db.post_drafts.update_one(
                    {"_id": post.id},
                    {"$set": {"engagement_last_checked": datetime.datetime.now(datetime.timezone.utc)}}
                )
    if posts_checked == 0:
        logger.info("No published posts found needing an engagement check at this time.")
    logger.info("Scheduler Task: Finished track_engagement_task.")


async def generate_reports_task():
    """
    Scheduled task: Generates a simple performance report and sends it via WhatsApp.
    """
    logger.info("Scheduler Task: Starting generate_reports_task...")
    db = await get_database()
    
    # Example: Report for the last 7 days
    one_week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    
    published_count_week = await db.post_drafts.count_documents({
        "status": PostStatus.PUBLISHED,
        "updated_at": {"$gte": one_week_ago} # Assuming updated_at reflects publish time for PUBLISHED status
    })
    
    total_likes_week = 0
    total_comments_week = 0
    
    # Aggregate engagement stats from posts updated/checked in the last week
    # This requires engagement_stats to be stored in a consistent way.
    async for post_doc in db.post_drafts.find({
        "status": PostStatus.PUBLISHED, 
        "engagement_stats": {"$exists": True},
        "engagement_last_checked": {"$gte": one_week_ago} # Consider stats checked recently
    }):
        stats = post_doc.get("engagement_stats", {})
        # Assuming 'raw_data' from get_linkedin_engagement was stored, and it contains likes/comments counts
        # This parsing depends on the actual structure of 'raw_data' from get_linkedin_engagement
        total_likes_week += stats.get("likes", {}).get("count", 0) if isinstance(stats.get("likes"), dict) else stats.get("likes", 0)
        total_comments_week += stats.get("comments", {}).get("count", 0) if isinstance(stats.get("comments"), dict) else stats.get("comments", 0)

    report_message = (
        f"📊 Weekly LinkedIn Agent Performance Report:\n\n"
        f"Posts Published (Last 7 Days): {published_count_week}\n"
        f"Total Likes (on recently checked posts): {total_likes_week}\n"
        f"Total Comments (on recently checked posts): {total_comments_week}\n\n"
        f"Keep up the great work! ✨"
    )
    logger.info(f"Generated Report: {report_message}")
    
    # Send report to the user via WhatsApp
    send_whatsapp_message(settings.USER_WHATSAPP_NUMBER, report_message)
    
    logger.info("Scheduler Task: Finished generate_reports_task.")

async def refresh_linkedin_token_if_needed_task(user_id: str = DEFAULT_USER_ID):
    """
    Scheduled task: Proactively checks and refreshes the LinkedIn token if it's nearing expiry.
    The get_stored_linkedin_token function already contains refresh logic.
    """
    logger.info(f"Scheduler Task: Checking LinkedIn token status for user {user_id}...")
    token = await get_stored_linkedin_token(user_id) # This will attempt refresh if needed
    if token and token.access_token:
        # Check if it was actually refreshed by comparing expiry, or just log success
        logger.info(f"LinkedIn token for user {user_id} is currently valid. Expires at: {token.expires_at}")
    else:
        logger.warning(f"LinkedIn token for user {user_id} could not be validated or refreshed. Manual re-authentication might be required via /auth/linkedin/login.")
        # Optionally, send an alert to the admin/user if token refresh fails consistently
        # send_whatsapp_message(settings.USER_WHATSAPP_NUMBER, "⚠️ LinkedIn token needs re-authentication!")
    logger.info(f"Scheduler Task: Finished refresh_linkedin_token_if_needed_task for user {user_id}.")
