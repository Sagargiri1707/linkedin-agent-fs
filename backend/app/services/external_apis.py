import httpx
from app.config import settings
import logging
from typing import Dict, Any, Optional, List
import asyncio

logger = logging.getLogger(__name__)

# --- Perplexity AI Service ---
async def get_trends_from_perplexity(query: str, industry: str) -> Optional[Dict[str, Any]]:
    """
    Placeholder: Fetches trending topics from Perplexity AI.
    """
    logger.info(f"Fetching trends from Perplexity for query: '{query}', industry: '{industry}'")
    # API_URL = "https://api.perplexity.ai/..." # Replace with actual Perplexity API endpoint
    # headers = {"Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}"}
    # params = {"query": query, "industry": industry} # Adjust params as per API docs
    # async with httpx.AsyncClient() as client:
    #     try:
    #         response = await client.get(API_URL, headers=headers, params=params)
    #         response.raise_for_status() # Raise an exception for HTTP errors
    #         return response.json()
    #     except httpx.HTTPStatusError as e:
    #         logger.error(f"Perplexity API request failed (HTTP {e.response.status_code}): {e.response.text}")
    #     except httpx.RequestError as e:
    #         logger.error(f"Perplexity API request failed (Network/Request Error): {e}")
    #     except Exception as e:
    #         logger.error(f"An unexpected error occurred with Perplexity API: {e}")
    await asyncio.sleep(1) # Simulate API call
    logger.warning("Perplexity API call is a placeholder.")
    return {"mock_trend_data": "some trend from perplexity", "query": query}

# --- DeepSeek API Service ---
async def generate_text_with_deepseek(prompt: str, voice_profile_examples: List[str]) -> Optional[str]:
    """
    Placeholder: Generates text using DeepSeek API.
    """
    logger.info(f"Generating text with DeepSeek for prompt: '{prompt[:50]}...'")
    # API_URL = "https://api.deepseek.com/..." # Replace with actual DeepSeek API endpoint
    # headers = {"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"}
    # payload = {"prompt": prompt, "examples": voice_profile_examples, "model": "deepseek-chat"} # Adjust
    # async with httpx.AsyncClient() as client:
    #     try:
    #         response = await client.post(API_URL, headers=headers, json=payload)
    #         response.raise_for_status()
    #         return response.json().get("generated_text") # Adjust based on actual response
    #     except httpx.HTTPStatusError as e:
    #         logger.error(f"DeepSeek API request failed (HTTP {e.response.status_code}): {e.response.text}")
    #     except Exception as e: # Catch other errors
    #         logger.error(f"An unexpected error occurred with DeepSeek API: {e}")
    await asyncio.sleep(1) # Simulate API call
    logger.warning("DeepSeek API call is a placeholder.")
    return f"Mock generated text for: {prompt[:30]}..."

# --- Ideogram API Service ---
async def generate_image_with_ideogram(prompt: str, aspect_ratio: str = "16:9") -> Optional[Dict[str, Any]]:
    """
    Placeholder: Generates an image using Ideogram API.
    Returns a dict with image_url and job_id (if available).
    """
    logger.info(f"Generating image with Ideogram for prompt: '{prompt[:50]}...'")
    # API_URL = "https://api.ideogram.ai/..." # Replace with actual Ideogram API endpoint
    # headers = {"Authorization": f"Bearer {settings.IDEOGRAM_API_KEY}"}
    # payload = {"prompt": prompt, "aspect_ratio": aspect_ratio} # Adjust
    # async with httpx.AsyncClient() as client:
    #     try:
    #         response = await client.post(API_URL, headers=headers, json=payload)
    #         response.raise_for_status()
    #         # Assuming response contains image_url and potentially a job_id
    #         return {"image_url": response.json().get("image_url"), "job_id": response.json().get("job_id")}
    #     except httpx.HTTPStatusError as e:
    #         logger.error(f"Ideogram API request failed (HTTP {e.response.status_code}): {e.response.text}")
    #     except Exception as e:
    #         logger.error(f"An unexpected error occurred with Ideogram API: {e}")
    await asyncio.sleep(1) # Simulate API call
    logger.warning("Ideogram API call is a placeholder.")
    return {"image_url": f"https://placehold.co/600x400/E6F7FF/003366?text=Ideogram+Mock+{prompt[:10].replace(' ','+')}", "job_id": "mock_ideogram_job_123"}

# --- Twilio WhatsApp Service ---
from twilio.rest import Client as TwilioClient

def send_whatsapp_message(to_number: str, message_body: str, media_url: Optional[str] = None) -> Optional[str]:
    """
    Sends a WhatsApp message using Twilio.
    Returns the message SID if successful, None otherwise.
    """
    logger.info(f"Sending WhatsApp message to {to_number}: '{message_body[:50]}...' Media: {media_url}")
    try:
        client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message_params = {
            "from_": settings.TWILIO_WHATSAPP_NUMBER,
            "to": to_number, # Should be in "whatsapp:+1234567890" format
            "body": message_body
        }
        if media_url:
            message_params["media_url"] = [media_url]

        # For messages with Quick Reply or Call to Action buttons, you'd use Content API or structured messages.
        # This example is for a simple text/media message.
        # For approval, you might send a message like:
        # "New post draft ready: [link_to_preview_or_text_summary]. Reply 'APPROVE [draft_id]' or 'REJECT [draft_id]'."
        # Or use Twilio's interactive message templates.

        # This is a synchronous call, consider running in a thread pool for FastAPI if it blocks too long
        # For now, keeping it simple for a personal project.
        # For truly async, you'd need an async Twilio library or wrap this in `run_in_executor`.
        message = client.messages.create(**message_params)
        logger.info(f"WhatsApp message sent successfully. SID: {message.sid}")
        return message.sid
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message via Twilio: {e}")
        return None

# --- LinkedIn API Service ---

async def exchange_linkedin_code_for_token(authorization_code: str) -> Optional[Dict[str, Any]]:
    """
    Exchanges an authorization code for a LinkedIn access token.
    This is part of the OAuth 2.0 flow.
    """
    logger.info("Exchanging authorization code for LinkedIn access token")
    
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    params = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=params)
            response.raise_for_status()
            token_data = response.json()
            logger.info("Successfully exchanged code for LinkedIn access token")
            return token_data
    except httpx.HTTPStatusError as e:
        logger.error(f"LinkedIn token exchange failed (HTTP {e.response.status_code}): {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn token exchange: {e}")
    return None

async def get_linkedin_user_profile(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the user's LinkedIn profile with the provided access token.
    At minimum, we need the user's URN (person ID) for posting.
    """
    logger.info("Fetching LinkedIn user profile")
    
    url = "https://api.linkedin.com/v2/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202405"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            profile_data = response.json()
            logger.info(f"Successfully fetched LinkedIn profile for user: {profile_data.get('id')}")
            return profile_data
    except httpx.HTTPStatusError as e:
        logger.error(f"LinkedIn profile fetch failed (HTTP {e.response.status_code}): {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error fetching LinkedIn profile: {e}")
    return None

async def store_linkedin_token(user_id: str, access_token: str, expires_in: int,
                         refresh_token: Optional[str] = None, 
                         refresh_token_expires_in: Optional[int] = None,
                         user_urn: Optional[str] = None) -> bool:
    """
    Stores or updates a LinkedIn token in the database.
    """
    from datetime import datetime, timedelta
    from app.database import get_database
    from app.models import LinkedInToken
    
    logger.info(f"Storing LinkedIn token for user: {user_id}")
    
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=expires_in)
    refresh_expires_at = None
    if refresh_token and refresh_token_expires_in:
        refresh_expires_at = now + timedelta(seconds=refresh_token_expires_in)
    
    token_data = {
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "refresh_token_expires_at": refresh_expires_at,
        "updated_at": now,
        "user_urn": user_urn
    }
    
    try:
        db = await get_database()
        # Check if a token already exists for this user
        existing_token = await db.linkedin_tokens.find_one({"user_id": user_id})
        
        if existing_token:
            # Update existing token
            result = await db.linkedin_tokens.update_one(
                {"user_id": user_id},
                {"$set": token_data}
            )
            success = result.modified_count > 0
        else:
            # Insert new token
            token_data["created_at"] = now
            token_model = LinkedInToken(**token_data)
            result = await db.linkedin_tokens.insert_one(token_model.model_dump(by_alias=True))
            success = result.inserted_id is not None
        
        logger.info(f"LinkedIn token {'updated' if existing_token else 'stored'} successfully")
        return success
    except Exception as e:
        logger.error(f"Failed to store LinkedIn token: {e}")
        return False

async def get_stored_linkedin_token(user_id: str = "default_personal_user") -> Optional[Dict[str, Any]]:
    """
    Retrieves a stored LinkedIn token from the database.
    Checks if the token is expired and needs refresh.
    """
    from datetime import datetime
    from app.database import get_database
    
    logger.info(f"Retrieving LinkedIn token for user: {user_id}")
    
    try:
        db = await get_database()
        token_doc = await db.linkedin_tokens.find_one({"user_id": user_id})
        
        if not token_doc:
            logger.warning(f"No LinkedIn token found for user: {user_id}")
            return None
        
        # Check if token is expired
        now = datetime.utcnow()
        expires_at = token_doc.get("expires_at")
        
        if expires_at and expires_at <= now:
            # Token is expired, attempt to refresh if we have a refresh token
            refresh_token = token_doc.get("refresh_token")
            refresh_expires_at = token_doc.get("refresh_token_expires_at")
            
            if refresh_token and (not refresh_expires_at or refresh_expires_at > now):
                # Attempt to refresh the token
                logger.info(f"LinkedIn token expired, attempting to refresh for user: {user_id}")
                new_token_data = await refresh_linkedin_token(refresh_token, user_id)
                if new_token_data:
                    return new_token_data
            
            logger.warning(f"LinkedIn token expired and could not be refreshed for user: {user_id}")
            return None
        
        # Token is valid
        logger.info(f"Retrieved valid LinkedIn token for user: {user_id}")
        return token_doc
    except Exception as e:
        logger.error(f"Error retrieving LinkedIn token: {e}")
        return None

async def refresh_linkedin_token(refresh_token: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Refreshes a LinkedIn access token using the refresh token.
    """
    logger.info(f"Refreshing LinkedIn token for user: {user_id}")
    
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    params = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=params)
            response.raise_for_status()
            
            new_token_data = response.json()
            # Store the new token data
            access_token = new_token_data.get("access_token")
            expires_in = new_token_data.get("expires_in", 3600)
            new_refresh_token = new_token_data.get("refresh_token", refresh_token)
            refresh_token_expires_in = new_token_data.get("refresh_token_expires_in")
            
            # Get the user URN from the existing record
            db = await get_database()
            existing_token = await db.linkedin_tokens.find_one({"user_id": user_id})
            user_urn = existing_token.get("user_urn") if existing_token else None
            
            success = await store_linkedin_token(
                user_id=user_id,
                access_token=access_token,
                expires_in=expires_in,
                refresh_token=new_refresh_token,
                refresh_token_expires_in=refresh_token_expires_in,
                user_urn=user_urn
            )
            
            if success:
                logger.info(f"Successfully refreshed LinkedIn token for user: {user_id}")
                return new_token_data
            else:
                logger.error(f"Failed to store refreshed LinkedIn token for user: {user_id}")
        
    except httpx.HTTPStatusError as e:
        logger.error(f"LinkedIn token refresh failed (HTTP {e.response.status_code}): {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error refreshing LinkedIn token: {e}")
    
    return None

# Replace the placeholder post_to_linkedin function with an improved version
async def post_to_linkedin(content_text: str, image_url: Optional[str] = None, user_id: str = "default_personal_user") -> Optional[str]:
    """
    Posts content to LinkedIn using the stored token for the user.
    Returns the LinkedIn post ID if successful.
    """
    logger.info(f"Posting to LinkedIn for user {user_id}: '{content_text[:50]}...'")
    
    # Get the token
    token_data = await get_stored_linkedin_token(user_id)
    if not token_data or "access_token" not in token_data:
        logger.error(f"LinkedIn post failed: No valid token found for user {user_id}")
        return None
    
    access_token = token_data["access_token"]
    user_urn = token_data.get("user_urn")
    
    if not user_urn:
        logger.error("LinkedIn post failed: No user URN (person ID) found")
        return None
    
    API_URL = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202405"
    }
    
    author_urn = f"urn:li:person:{user_urn}"
    
    post_payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": content_text
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    if image_url:
        # For a complete implementation, you would need to:
        # 1. Register the image upload with LinkedIn
        # 2. Upload the image to the provided upload URL
        # 3. Reference the asset in your post
        #
        # For simplicity, this example will just link to the image as an article
        post_payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "ARTICLE"
        post_payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
            "status": "READY",
            "originalUrl": image_url,
            "title": {
                "text": "Generated Content"
            }
        }]
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, headers=headers, json=post_payload)
            logger.info(f"LinkedIn API Response Status: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"LinkedIn API error: {response.text}")
                return None
                
            response.raise_for_status()
            
            # LinkedIn returns the created post ID in the response or headers
            post_id = None
            if "x-restli-id" in response.headers:
                post_id = response.headers["x-restli-id"]
            elif response.text:
                try:
                    post_id = response.json().get("id")
                except:
                    logger.warning("Could not parse LinkedIn response JSON")
            
            if post_id:
                logger.info(f"Successfully posted to LinkedIn. Post ID: {post_id}")
                return post_id
            else:
                logger.warning("LinkedIn post succeeded but no post ID was returned")
                return "unknown_post_id"
                
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn API post failed (HTTP {e.response.status_code}): {e.response.text}")
        except Exception as e:
            logger.error(f"An unexpected error occurred posting to LinkedIn: {e}")
    
    return None

# --- LinkedIn API Service (Direct HTTPX Calls) ---
# Previous placeholder functions are now replaced with full implementations above 