# app/services/external_apis.py
# Functions for interacting with all external APIs (Perplexity, DeepSeek, Ideogram, Twilio, LinkedIn).

import httpx # Modern asynchronous HTTP client
from app.config import settings # Application settings (API keys, URLs)
import logging # For logging API requests and responses
from typing import Dict, Any, Optional, List
import datetime # For token expiry calculations
import urllib.parse # For URL encoding parameters, e.g., for LinkedIn URNs
import asyncio # For simulating async operations in placeholders

# Import Pydantic models if needed for request/response typing or data manipulation
from app.models import LinkedInToken
from app.database import get_database # For storing/retrieving tokens

logger = logging.getLogger(__name__)

# --- LinkedIn API Constants ---
LINKEDIN_OAUTH_BASE_URL = "https://www.linkedin.com/oauth/v2"
LINKEDIN_API_BASE_URL = "https://api.linkedin.com/v2"
LINKEDIN_ACCESS_TOKEN_URL = f"{LINKEDIN_OAUTH_BASE_URL}/accessToken"
LINKEDIN_ME_API_URL = f"{LINKEDIN_API_BASE_URL}/me" # Gets basic profile including URN ('id')
LINKEDIN_USERINFO_API_URL = f"{LINKEDIN_API_BASE_URL}/userinfo" # For OpenID Connect scopes (name, email, pic)
LINKEDIN_UGC_POSTS_URL = f"{LINKEDIN_API_BASE_URL}/ugcPosts"
LINKEDIN_ASSETS_URL = f"{LINKEDIN_API_BASE_URL}/assets" # For image/video uploads

# --- Perplexity AI Service ---
async def get_trends_from_perplexity(query: str, industry: str) -> Optional[Dict[str, Any]]:
    """
    Fetches trending topics or insights from Perplexity AI.
    This is a placeholder and needs to be implemented based on Perplexity's actual API.
    """
    logger.info(f"Attempting to fetch trends from Perplexity for query: '{query}', industry: '{industry}'")
    # Example: Perplexity's pplx-online models are good for web-connected search
    # API_URL = "https://api.perplexity.ai/chat/completions" # Check Perplexity's documentation
    headers = {
        "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": "pplx-7b-online", # Or other suitable model like pplx-70b-online
        "messages": [
            {"role": "system", "content": f"You are an AI assistant specializing in identifying and summarizing key trending topics within the {industry} sector."},
            {"role": "user", "content": f"Based on current web data, what are the top 3-5 emerging trends related to '{query}' in {industry}? For each trend, provide a concise summary (1-2 sentences) and list 2-3 relevant keywords or hashtags."}
        ],
        "max_tokens": 500, # Adjust as needed
        "temperature": 0.7, # Adjust for creativity vs. factuality
    }
    # async with httpx.AsyncClient(timeout=30.0) as client:
    #     try:
    #         # response = await client.post(API_URL, headers=headers, json=payload)
    #         # response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
    #         # parsed_response = response.json()
    #         # logger.info("Successfully fetched data from Perplexity.")
    #         # return parsed_response # Process this to fit your Trend model
    #     except httpx.HTTPStatusError as e:
    #         logger.error(f"Perplexity API request failed (HTTP {e.response.status_code}): {e.response.text}")
    #     except httpx.RequestError as e: # Covers network errors, timeouts, etc.
    #         logger.error(f"Perplexity API request failed (Network/Request Error): {e}")
    #     except Exception as e: # Catch any other unexpected errors
    #         logger.error(f"An unexpected error occurred with Perplexity API: {e}", exc_info=True)
    await asyncio.sleep(1) # Simulate API call duration
    logger.warning("Perplexity API call (get_trends_from_perplexity) is a placeholder.")
    return {"mock_trend_data": f"Emerging trend about '{query}' in {industry}", "summary": "Detailed summary here.", "keywords": ["keyword1", "hashtag2"]}

# --- DeepSeek API Service ---
async def generate_text_with_deepseek(prompt: str, voice_profile_examples: Optional[List[str]] = None) -> Optional[str]:
    """
    Generates text content using the DeepSeek API.
    """
    logger.info(f"Attempting to generate text with DeepSeek for prompt: '{prompt[:70]}...'")
    # API_URL = "https://api.deepseek.com/chat/completions" # Standard OpenAI-compatible endpoint
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [{"role": "system", "content": "You are an expert LinkedIn content creator. Your tone should be professional, insightful, and engaging. Aim for clarity and conciseness suitable for LinkedIn."}]
    if voice_profile_examples:
        style_guide = "\n".join([f"- Example: \"{ex}\"" for ex in voice_profile_examples])
        messages.append({"role": "system", "content": f"Please adapt your writing style to match the following examples:\n{style_guide}"})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "deepseek-chat", # Or "deepseek-coder" if more appropriate for specific tasks
        "messages": messages,
        "max_tokens": 400, # LinkedIn posts are generally not extremely long
        "temperature": 0.75,
    }
    # async with httpx.AsyncClient(timeout=60.0) as client: # Longer timeout for generation
    #     try:
    #         # response = await client.post(API_URL, headers=headers, json=payload)
    #         # response.raise_for_status()
    #         # generated_content = response.json().get("choices", [{}])[0].get("message", {}).get("content")
    #         # logger.info("Successfully generated text with DeepSeek.")
    #         # return generated_content.strip() if generated_content else None
    #     except httpx.HTTPStatusError as e:
    #         logger.error(f"DeepSeek API request failed (HTTP {e.response.status_code}): {e.response.text}")
    #     except Exception as e:
    #         logger.error(f"An unexpected error occurred with DeepSeek API: {e}", exc_info=True)
    await asyncio.sleep(1)
    logger.warning("DeepSeek API call (generate_text_with_deepseek) is a placeholder.")
    return f"Mock AI-generated LinkedIn post about: {prompt[:50]}... #Mock #AI #LinkedIn"

# --- Ideogram API Service ---
async def generate_image_with_ideogram(prompt: str, aspect_ratio: str = "16:9") -> Optional[Dict[str, Any]]:
    """
    Generates an image using the Ideogram API.
    Ideogram's API might be asynchronous (submit job, poll for result). This is a simplified placeholder.
    Returns a dictionary with 'image_url' and 'job_id' (if applicable).
    """
    logger.info(f"Attempting to generate image with Ideogram for prompt: '{prompt[:70]}...'")
    # API_URL = "https_api_ideogram_ai_v1_images_generations" # Fictional, check Ideogram's actual API
    headers = {
        "Authorization": f"Bearer {settings.IDEOGRAM_API_KEY}", # Or other auth method
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "style": "photorealistic", # Or "cinematic", "illustration", "3d_render" etc.
        # Other Ideogram specific parameters
    }
    # async with httpx.AsyncClient(timeout=180.0) as client: # Image generation can take time
    #     try:
    #         # response = await client.post(API_URL, headers=headers, json=payload)
    #         # response.raise_for_status()
    #         # data = response.json()
    #         # logger.info("Successfully submitted image generation job to Ideogram or got direct image.")
    #         # return {"image_url": data.get("image_url"), "job_id": data.get("job_id")} # Adjust based on actual response
    #     except httpx.HTTPStatusError as e:
    #         logger.error(f"Ideogram API request failed (HTTP {e.response.status_code}): {e.response.text}")
    #     except Exception as e:
    #         logger.error(f"An unexpected error occurred with Ideogram API: {e}", exc_info=True)
    await asyncio.sleep(2)
    logger.warning("Ideogram API call (generate_image_with_ideogram) is a placeholder.")
    # Use a placeholder image service for mock data
    encoded_prompt = urllib.parse.quote_plus(prompt[:20])
    return {"image_url": f"https://placehold.co/1200x628/E6F7FF/003366?text=IdeogramMock:{encoded_prompt}", "job_id": f"mock_ideogram_{ObjectId()}"}


# --- Twilio WhatsApp Service ---
from twilio.rest import Client as TwilioSyncClient # Twilio's library is synchronous

# For running synchronous Twilio calls in an async app, you might wrap them
# or use a thread pool. For simplicity in a personal project, direct calls might be acceptable
# if they are infrequent and don't block critical paths for too long.
# Consider `asyncio.to_thread` for FastAPI if needed:
# `message = await asyncio.to_thread(twilio_sync_client.messages.create, **message_params)`

def send_whatsapp_message(to_number: str, message_body: str, media_url: Optional[str] = None) -> Optional[str]:
    """
    Sends a WhatsApp message using Twilio's synchronous library.
    Returns the message SID if successful, None otherwise.
    """
    logger.info(f"Attempting to send WhatsApp message via Twilio to {to_number}: '{message_body[:70]}...' Media: {media_url}")
    if not settings.TWILIO_ACCOUNT_SID or settings.TWILIO_ACCOUNT_SID == "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx":
        logger.warning("Twilio credentials not configured or are placeholders. Skipping actual send.")
        return f"mock_twilio_sid_{ObjectId()}" # Return a mock SID for testing flow

    try:
        client = TwilioSyncClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message_params = {
            "from_": settings.TWILIO_WHATSAPP_NUMBER,
            "to": to_number, # Should be in "whatsapp:+1234567890" format
            "body": message_body
        }
        if media_url: # Ensure media_url is publicly accessible by Twilio
            message_params["media_url"] = [media_url]

        # For interactive messages (buttons for approval):
        # You would use Twilio's Content API or specific template features.
        # Example: "Reply 'APPROVE DRAFT_ID' or 'REJECT DRAFT_ID'."
        # Or send a message template with quick reply buttons.

        message = client.messages.create(**message_params)
        logger.info(f"WhatsApp message sent successfully. SID: {message.sid}")
        return message.sid
    except Exception as e: # Catch Twilio specific errors if possible, e.g., TwilioRestException
        logger.error(f"Failed to send WhatsApp message via Twilio: {e}", exc_info=True)
    return None

# --- LinkedIn OAuth & API Services (Direct HTTPX Calls) ---

async def exchange_linkedin_code_for_token(code: str) -> Optional[Dict[str, Any]]:
    """Exchanges an OAuth 2.0 authorization code for an access token with LinkedIn."""
    logger.info(f"Exchanging LinkedIn authorization code for access token...")
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(LINKEDIN_ACCESS_TOKEN_URL, data=payload, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            logger.info("Successfully exchanged code for LinkedIn access token.")
            return token_data
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn token exchange failed (HTTP {e.response.status_code}): {e.response.text}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during LinkedIn token exchange: {e}", exc_info=True)
    return None

async def refresh_linkedin_token(refresh_token_value: str) -> Optional[Dict[str, Any]]:
    """Refreshes an expired LinkedIn access token using a refresh token."""
    logger.info("Attempting to refresh LinkedIn access token...")
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(LINKEDIN_ACCESS_TOKEN_URL, data=payload, headers=headers)
            response.raise_for_status()
            refreshed_data = response.json()
            logger.info("Successfully refreshed LinkedIn access token.")
            return refreshed_data # Should contain new access_token, expires_in, etc.
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn token refresh failed (HTTP {e.response.status_code}): {e.response.text}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during LinkedIn token refresh: {e}", exc_info=True)
    return None

async def get_linkedin_user_profile(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Fetches basic user profile information from LinkedIn, primarily the URN (user ID).
    The URN is typically in the 'id' field from the /v2/me endpoint.
    """
    logger.info("Fetching LinkedIn user profile (URN)...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": settings.LINKEDIN_API_VERSION
    }
    async with httpx.AsyncClient() as client:
        try:
            # /v2/me is standard for getting the authenticated user's profile, including their URN ('id')
            response_me = await client.get(LINKEDIN_ME_API_URL, headers=headers)
            response_me.raise_for_status()
            profile_data = response_me.json() # This should contain the 'id' which is the URN
            
            # If you also requested OpenID Connect scopes (openid, profile, email),
            # you can get more PII from /v2/userinfo.
            # response_userinfo = await client.get(LINKEDIN_USERINFO_API_URL, headers=headers)
            # response_userinfo.raise_for_status()
            # userinfo_data = response_userinfo.json()
            # profile_data.update(userinfo_data) # Merge if needed (e.g., for email, name, picture)
            
            logger.info(f"Successfully fetched LinkedIn profile. User URN: {profile_data.get('id')}")
            return profile_data
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn profile fetch failed (HTTP {e.response.status_code}): {e.response.text}")
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching LinkedIn profile: {e}", exc_info=True)
    return None

async def store_linkedin_token(
    user_id: str,
    access_token_value: str,
    expires_in: int,
    user_urn: str,
    refresh_token_value: Optional[str] = None,
    refresh_token_expires_in: Optional[int] = None
):
    """Stores or updates the LinkedIn token in the database."""
    db = await get_database()
    now = datetime.datetime.now(datetime.timezone.utc) # Use timezone-aware datetime
    expires_at = now + datetime.timedelta(seconds=expires_in)
    
    refresh_expires_at = None
    if refresh_token_value and refresh_token_expires_in:
        # LinkedIn refresh tokens usually have a longer validity (e.g., 1 year)
        refresh_expires_at = now + datetime.timedelta(seconds=refresh_token_expires_in)

    token_data_to_store = LinkedInToken(
        user_id=user_id,
        user_urn=user_urn,
        access_token=access_token_value,
        refresh_token=refresh_token_value,
        expires_at=expires_at,
        refresh_token_expires_at=refresh_expires_at,
        updated_at=now # Record when this token info was last updated
        # created_at will be set by default if it's a new document
    )
    
    # Using model_dump(by_alias=True) to ensure _id is handled correctly if present,
    # and exclude_none=True to avoid inserting nulls for optional fields not provided.
    update_doc = token_data_to_store.model_dump(by_alias=True, exclude_none=True)
    # Ensure 'created_at' is set on insert but not overwritten on update unless explicitly included
    if "created_at" in update_doc: del update_doc["created_at"]


    await db.linkedin_tokens.update_one(
        {"user_id": user_id}, # Filter to find the document for this user
        {
            "$set": update_doc,
            "$setOnInsert": {"created_at": now} # Set 'created_at' only when inserting a new document
        },
        upsert=True # Creates the document if it doesn't exist, updates it if it does
    )
    logger.info(f"LinkedIn token stored/updated for user_id: {user_id}, URN: {user_urn}")

async def get_stored_linkedin_token(user_id: str) -> Optional[LinkedInToken]:
    """
    Retrieves a stored LinkedIn token for a user.
    If the access token is expired and a refresh token is available, it attempts to refresh it.
    """
    db = await get_database()
    token_doc = await db.linkedin_tokens.find_one({"user_id": user_id})
    if not token_doc:
        logger.info(f"No LinkedIn token found in DB for user_id: {user_id}")
        return None

    token = LinkedInToken(**token_doc)
    
    # Check if the access token is expired or nearing expiry (e.g., within next 5 minutes)
    # Add timezone.utc to now() for correct comparison with stored timezone-aware expires_at
    if token.expires_at < (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)):
        logger.info(f"LinkedIn access token for {user_id} (URN: {token.user_urn}) is expired or nearing expiry.")
        if token.refresh_token:
            # Check if refresh token itself is expired (if expiry info is available)
            if token.refresh_token_expires_at and token.refresh_token_expires_at < datetime.datetime.now(datetime.timezone.utc):
                logger.error(f"LinkedIn refresh token for {user_id} has also expired. Manual re-authentication required.")
                return None # Both tokens are effectively useless

            logger.info(f"Attempting to refresh LinkedIn token for {user_id} using refresh token...")
            refreshed_data = await refresh_linkedin_token(token.refresh_token)
            
            if refreshed_data and "access_token" in refreshed_data:
                new_access_token = refreshed_data["access_token"]
                new_expires_in = refreshed_data.get("expires_in", 3600) # Default 1 hour
                # LinkedIn might also return a new refresh_token and its expiry
                new_refresh_token = refreshed_data.get("refresh_token", token.refresh_token) # Keep old if not provided
                new_refresh_token_expires_in = refreshed_data.get("refresh_token_expires_in")

                await store_linkedin_token( # This will update the token in DB
                    user_id=user_id,
                    access_token_value=new_access_token,
                    expires_in=new_expires_in,
                    user_urn=token.user_urn, # User URN does not change
                    refresh_token_value=new_refresh_token,
                    refresh_token_expires_in=new_refresh_token_expires_in
                )
                logger.info(f"Successfully refreshed and stored new LinkedIn token for {user_id}.")
                # Fetch the newly stored token to return it with updated timestamps
                updated_token_doc = await db.linkedin_tokens.find_one({"user_id": user_id})
                return LinkedInToken(**updated_token_doc) if updated_token_doc else None
            else:
                logger.error(f"Failed to refresh LinkedIn token for {user_id}. Manual re-authentication likely required.")
                # Optionally, delete or mark the invalid token in DB
                return None # Indicate token is invalid/could not be refreshed
        else:
            logger.warning(f"LinkedIn access token for {user_id} expired, and no refresh token is available. Manual re-authentication required.")
            return None # Token is expired, no refresh token
            
    logger.info(f"Valid LinkedIn token retrieved from DB for user_id: {user_id}")
    return token # Token is valid

async def post_content_to_linkedin(access_token: str, author_urn: str, content_text: str, image_asset_urn: Optional[str] = None, article_link: Optional[str] = None) -> Optional[str]:
    """
    Posts content to LinkedIn. Supports text, text + registered image asset, or text + article link.
    Returns the LinkedIn post URN if successful.
    """
    logger.info(f"Attempting to post to LinkedIn by author {author_urn}: '{content_text[:70]}...'")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0", # Often required by LinkedIn
        "LinkedIn-Version": settings.LINKEDIN_API_VERSION
    }
    
    share_content: Dict[str, Any] = {"shareCommentary": {"text": content_text}}
    
    if image_asset_urn:
        share_content["shareMediaCategory"] = "IMAGE"
        share_content["media"] = [{"status": "READY", "media": image_asset_urn}]
    elif article_link:
        share_content["shareMediaCategory"] = "ARTICLE"
        share_content["media"] = [{"status": "READY", "originalUrl": article_link}]
    else:
        share_content["shareMediaCategory"] = "NONE"

    post_payload: Dict[str, Any] = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"} # Or "CONNECTIONS"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(LINKEDIN_UGC_POSTS_URL, headers=headers, json=post_payload)
            logger.debug(f"LinkedIn Post API Request Payload: {post_payload}")
            logger.debug(f"LinkedIn Post API Response Status: {response.status_code}")
            logger.debug(f"LinkedIn Post API Response Headers: {response.headers}")
            logger.debug(f"LinkedIn Post API Response Content: {response.text}")
            response.raise_for_status()
            # LinkedIn returns the created post URN in the 'x-restli-id' header or in the body as 'id'
            post_urn = response.headers.get("x-restli-id") or response.json().get("id")
            logger.info(f"Successfully posted to LinkedIn. Post URN: {post_urn}")
            return post_urn
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn API post failed (HTTP {e.response.status_code}): {e.response.text}")
            logger.error(f"Request payload that failed: {post_payload}")
        except Exception as e:
            logger.error(f"An unexpected error occurred posting to LinkedIn: {e}", exc_info=True)
    return None

async def register_linkedin_image_asset(access_token: str, author_urn: str) -> Optional[Dict[str, Any]]:
    """
    Step 1 for image uploads: Registers an image upload with LinkedIn.
    Returns a dictionary with 'asset' (URN) and 'uploadUrl'.
    """
    logger.info(f"Registering LinkedIn image asset for author: {author_urn}")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": settings.LINKEDIN_API_VERSION
    }
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author_urn,
            "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
        }
    }
    # The endpoint is /v2/assets?action=registerUpload
    url = f"{LINKEDIN_ASSETS_URL}?action=registerUpload"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json().get("value", {})
            asset_urn = data.get("asset")
            upload_url = data.get("uploadMechanism", {}).get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {}).get("uploadUrl")
            if asset_urn and upload_url:
                logger.info(f"Successfully registered image asset. URN: {asset_urn}")
                return {"asset_urn": asset_urn, "upload_url": upload_url}
            else:
                logger.error(f"Failed to get asset URN or upload URL from LinkedIn registration response: {data}")
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn image asset registration failed (HTTP {e.response.status_code}): {e.response.text}")
        except Exception as e:
            logger.error(f"Error registering LinkedIn image asset: {e}", exc_info=True)
    return None

async def upload_linkedin_image(upload_url: str, image_path_or_bytes: Any, access_token: str) -> bool:
    """
    Step 2 for image uploads: Uploads the image binary to the URL provided by LinkedIn.
    image_path_or_bytes can be a file path (str) or bytes.
    """
    logger.info(f"Uploading image to LinkedIn: {upload_url[:50]}...")
    headers = {
        "Authorization": f"Bearer {access_token}", # LinkedIn docs say this might be needed
        # "Content-Type" will be set by httpx based on files or content
    }
    async with httpx.AsyncClient() as client:
        try:
            if isinstance(image_path_or_bytes, str): # it's a file path
                with open(image_path_or_bytes, "rb") as f:
                    content = f.read()
            elif isinstance(image_path_or_bytes, bytes):
                content = image_path_or_bytes
            else:
                logger.error("Invalid image_path_or_bytes type for upload.")
                return False
            
            # LinkedIn expects a PUT request with the binary data in the body
            response = await client.put(upload_url, content=content, headers=headers) # No specific Content-Type needed here for raw bytes usually
            response.raise_for_status() # Check for 200 or 201 typically
            logger.info(f"Successfully uploaded image to LinkedIn. Status: {response.status_code}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn image upload failed (HTTP {e.response.status_code}): {e.response.text}")
        except FileNotFoundError:
             logger.error(f"Image file not found for upload: {image_path_or_bytes}")
        except Exception as e:
            logger.error(f"Error uploading LinkedIn image: {e}", exc_info=True)
    return False


async def get_linkedin_engagement(access_token: str, post_urn: str) -> Optional[Dict[str, Any]]:
    """
    Fetches engagement statistics for a given LinkedIn post URN.
    """
    logger.info(f"Fetching engagement for LinkedIn post URN: {post_urn}")
    
    # Ensure the post_urn is properly URL-encoded for use in a URL path or query param
    encoded_post_urn = urllib.parse.quote(post_urn)
    
    # LinkedIn has multiple ways to get engagement.
    # /v2/socialActions/{activityURN}/summary or /v2/socialActions/{ugcPostURN}/summary
    # /v2/reactions/(entity:{encoded_post_urn})?q=entity  (for reactions)
    # /v2/comments/(entity:{encoded_post_urn})?q=entity (for comments)
    # Let's try the summary endpoint first, it's simpler.
    # The URN for socialActions is often the same as the post URN itself for UGC posts.
    api_url = f"{LINKEDIN_API_BASE_URL}/socialActions/{encoded_post_urn}/summary"
    # Alternative for just likes: f"{LINKEDIN_API_BASE_URL}/reactions/(entity:{encoded_post_urn})?q=entity&projection=(paging)"
    # Then check paging.total for count.

    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": settings.LINKEDIN_API_VERSION
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, headers=headers)
            logger.debug(f"LinkedIn Engagement API Response Status for {post_urn}: {response.status_code}")
            logger.debug(f"LinkedIn Engagement API Response Content: {response.text}")
            response.raise_for_status()
            data = response.json()
            
            # Parse data according to LinkedIn's response structure for the summary endpoint
            # This structure can vary, so consult LinkedIn docs for the specific endpoint used.
            # Example structure based on common patterns:
            return {
                "likes": data.get("likes", {}).get("count", 0), # Example path
                "comments": data.get("comments", {}).get("count", 0), # Example path
                "shares": data.get("shares", {}).get("count", 0), # Example path, may not always be in summary
                "post_urn": post_urn,
                "raw_data": data # Store the full response for later analysis if needed
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn engagement fetch for {post_urn} failed (HTTP {e.response.status_code}): {e.response.text}")
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching LinkedIn engagement for {post_urn}: {e}", exc_info=True)
    return None

# Helper to get ObjectId if needed for mock data
from bson import ObjectId
