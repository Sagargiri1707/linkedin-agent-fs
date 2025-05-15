# main.py
# Main FastAPI application file for the LinkedIn Automation AI Agent.

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import RedirectResponse, PlainTextResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
import httpx # For OAuth token exchange, though it's mostly in external_apis.py

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.scheduler import scheduler, start_scheduler, shutdown_scheduler
from app.services.linkedin_agent_service import (
    handle_whatsapp_approval,
    # process_new_trend_for_content_generation # This was a helper, direct call in endpoint if needed
    _process_single_trend_for_content # Import the helper for direct trigger
)
from app.services.external_apis import (
    exchange_linkedin_code_for_token,
    get_linkedin_user_profile,
    store_linkedin_token,
    get_stored_linkedin_token # For the /auth/linkedin/status endpoint
)
from app.models import Trend, LinkedInToken # Import necessary Pydantic models

# Configure logging
# You can customize this further, e.g., by adding formatters, file handlers, etc.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Application Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    - Connects to MongoDB on startup.
    - Starts the APScheduler on startup.
    - Closes MongoDB connection on shutdown.
    - Shuts down the APScheduler on shutdown.
    """
    # Startup sequence
    logger.info(f"Starting up {settings.PROJECT_NAME}...")
    await connect_to_mongo() # Establish MongoDB connection
    logger.info("MongoDB connection established.")
    start_scheduler() # Initialize and start scheduled jobs
    logger.info("APScheduler started.")
    
    yield # Application runs after this point
    
    # Shutdown sequence
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    await close_mongo_connection() # Close MongoDB connection
    logger.info("MongoDB connection closed.")
    shutdown_scheduler() # Gracefully shut down the scheduler
    logger.info("APScheduler shut down.")

# Initialize FastAPI application with the lifespan manager
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="An AI agent to automate LinkedIn content creation, approval, and posting.",
    version="0.1.0",
    lifespan=lifespan # Register the lifespan context manager
)

# --- API Endpoints ---

@app.get("/", tags=["General"])
async def read_root():
    """
    Root endpoint for a basic health check or welcome message.
    """
    return {"message": f"Welcome to the {settings.PROJECT_NAME}! Agent is operational."}

# --- LinkedIn OAuth 2.0 Endpoints ---
LINKEDIN_AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
# LINKEDIN_ACCESS_TOKEN_URL is defined in external_apis.py

@app.get("/auth/linkedin/login", tags=["LinkedIn Authentication"])
async def linkedin_login_redirect():
    """
    Redirects the user to LinkedIn's authorization page to initiate OAuth 2.0 flow.
    The user will be asked to grant permissions (scopes) to your application.
    """
    # CSRF protection: Generate a unique, unpredictable 'state' parameter.
    # Store it temporarily (e.g., in user's session or a short-lived DB entry)
    # and verify it in the callback. For simplicity, using a hardcoded one for now.
    # In a real app, DO NOT use a hardcoded state.
    csrf_state = "SOME_RANDOM_CSRF_PREVENTION_STRING_12345" # Replace with dynamic state generation & validation

    scopes = [
        "openid",       # Standard OpenID scope
        "profile",      # Access to basic profile fields available through OpenID
        "email",        # Access to primary email address (if available and permission granted)
        "r_liteprofile",# Access to name, photo, headline (alternative to OpenID 'profile')
        "w_member_social" # Permission to post, comment, react on behalf of the member
        # For organization/company page posting, you'd need scopes like:
        # "r_organization_social", "w_organization_social", "rw_organization_admin" (if managing company pages)
    ]
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "state": csrf_state,
        "scope": " ".join(scopes) # Scopes are space-separated
    }
    auth_url = f"{LINKEDIN_AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"
    logger.info(f"Redirecting user to LinkedIn for authorization: {auth_url}")
    return RedirectResponse(url=auth_url, status_code=307)

@app.get("/auth/linkedin/callback", tags=["LinkedIn Authentication"])
async def linkedin_oauth_callback(code: str, state: str, background_tasks: BackgroundTasks):
    """
    Handles the callback from LinkedIn after user authorization.
    Exchanges the authorization code for an access token and stores it.
    """
    logger.info(f"Received LinkedIn OAuth callback. Code: '{code[:15]}...', State: '{state}'")

    # IMPORTANT: Validate the 'state' parameter here against the one you generated
    # and stored before redirecting the user. This prevents CSRF attacks.
    # For this example, we're using the hardcoded state.
    expected_state = "SOME_RANDOM_CSRF_PREVENTION_STRING_12345"
    if state != expected_state:
        logger.error("Invalid OAuth state received from LinkedIn. Potential CSRF attack.")
        # Redirect to frontend with error
        return RedirectResponse(url=f"http://localhost:3000/?auth_error=InvalidState", status_code=307)


    token_data = await exchange_linkedin_code_for_token(code)

    if not token_data or "access_token" not in token_data:
        logger.error("Failed to exchange authorization code for access token with LinkedIn.")
        # Redirect to frontend with error
        return RedirectResponse(url=f"http://localhost:3000/?auth_error=TokenExchangeFailed", status_code=307)

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600) # Default to 1 hour (3600 seconds)
    refresh_token = token_data.get("refresh_token")
    # LinkedIn's refresh token TTL is typically 1 year, but they don't always return refresh_token_expires_in
    refresh_token_expires_in = token_data.get("refresh_token_expires_in") # In seconds

    # Fetch user profile to get their URN (needed for posting and associating the token)
    user_profile = await get_linkedin_user_profile(access_token)
    if not user_profile or "id" not in user_profile: # 'id' is the person URN
        logger.error("Failed to fetch user profile (URN) from LinkedIn after obtaining token.")
        return RedirectResponse(url=f"http://localhost:3000/?auth_error=ProfileFetchFailed", status_code=307)
    
    linkedin_user_urn = user_profile["id"]
    logger.info(f"Successfully obtained LinkedIn access token. User URN: {linkedin_user_urn}")

    # Store the token securely (e.g., in MongoDB)
    # For this personal project, we use a default internal user ID.
    internal_user_id = "default_personal_user" # Defined in linkedin_agent_service.py
    
    # Run token storage in the background to respond quickly to the callback
    background_tasks.add_task(
        store_linkedin_token,
        user_id=internal_user_id,
        access_token_value=access_token,
        expires_in=expires_in,
        user_urn=linkedin_user_urn,
        refresh_token_value=refresh_token,
        refresh_token_expires_in=refresh_token_expires_in
    )
    
    # Redirect back to the frontend, indicating success
    # The React frontend is set up to look for 'auth_success=true'
    logger.info("Redirecting to frontend after successful LinkedIn authentication.")
    return RedirectResponse(url=f"http://localhost:3000/?auth_success=true", status_code=307)


@app.get("/auth/linkedin/status", tags=["LinkedIn Authentication"])
async def get_linkedin_authentication_status():
    """
    Checks and returns the current LinkedIn authentication status for the default user.
    Used by the frontend to display connection status.
    """
    # DEFAULT_USER_ID should be consistent, e.g., from config or a constant
    from app.services.linkedin_agent_service import DEFAULT_USER_ID

    token: Optional[LinkedInToken] = await get_stored_linkedin_token(DEFAULT_USER_ID)
    if token and token.access_token:
        # get_stored_linkedin_token handles refresh if token is near expiry
        logger.info(f"LinkedIn token found for user {DEFAULT_USER_ID}, URN: {token.user_urn}")
        return {
            "is_connected": True,
            "user_urn": token.user_urn,
            "token_expires_at": token.expires_at.isoformat() if token.expires_at else None
        }
    logger.info(f"No valid LinkedIn token found for user {DEFAULT_USER_ID}.")
    return {"is_connected": False, "user_urn": None, "token_expires_at": None}


@app.post("/webhook/twilio/whatsapp", tags=["Twilio Webhook"])
async def webhook_twilio_whatsapp_receiver(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint to receive incoming messages/events from Twilio for WhatsApp.
    Twilio typically sends data as 'application/x-www-form-urlencoded'.
    """
    try:
        # Parse form data from Twilio's request
        form_data = await request.form()
        message_sid = form_data.get("MessageSid")
        from_number = form_data.get("From") # User's WhatsApp number, e.g., "whatsapp:+1234567890"
        body = form_data.get("Body")         # User's message or button payload

        logger.info(f"Received WhatsApp message from {from_number} (SID: {message_sid}): '{body}'")

        if not all([message_sid, from_number, body]):
            logger.error("Missing required fields (MessageSid, From, Body) in Twilio webhook data.")
            raise HTTPException(status_code=400, detail="Missing required fields in Twilio webhook data")

        # Add the approval handling task to the background to respond to Twilio quickly
        background_tasks.add_task(handle_whatsapp_approval, from_number, body, message_sid)
        
        # Respond to Twilio to acknowledge receipt.
        # An empty TwiML response is standard if you don't want to send an immediate reply message.
        # from twilio.twiml.messaging_response import MessagingResponse
        # twiml_response = MessagingResponse()
        # return PlainTextResponse(str(twiml_response), media_type="application/xml")
        # For now, a simple JSON response might work for testing, but Twilio expects TwiML.
        return {"status": "success", "message": "Webhook received and processing initiated."}

    except Exception as e:
        logger.error(f"Error processing Twilio WhatsApp webhook: {e}", exc_info=True)
        # Avoid sending detailed error back to Twilio unless necessary for their debugging.
        raise HTTPException(status_code=500, detail="Internal Server Error processing webhook")


# --- Example endpoint for Manual Triggering (for testing purposes) ---
@app.post("/trigger/generate-content", tags=["Testing & Triggers"])
async def trigger_content_generation_for_trend(trend_topic: str, background_tasks: BackgroundTasks):
    """
    An example endpoint to manually trigger the content generation process for a given trend topic.
    This bypasses the automated trend fetching for direct testing of content creation.
    """
    try:
        db = await get_database()
        # Create a dummy Trend object for now. In a real scenario, you might select an existing trend.
        # Or, this endpoint could accept more details to create a full Trend object.
        trend = Trend(
            topic=trend_topic,
            source="manual_trigger_endpoint",
            summary=f"Manually triggered content generation for the topic: {trend_topic}",
            relevance_score=0.95 # High relevance as it's manually triggered
        )
        # Optionally save this manually triggered trend to the DB
        # await db.trends.insert_one(trend.model_dump(by_alias=True, exclude_none=True))
        
        logger.info(f"Manually triggering content generation for trend topic: '{trend.topic}'")
        # Use the internal helper function that processes a single trend
        background_tasks.add_task(_process_single_trend_for_content, trend)
        
        return {"message": f"Content generation process for '{trend.topic}' triggered in the background."}
    except Exception as e:
        logger.error(f"Error triggering manual content generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error triggering content generation: {str(e)}")


if __name__ == "__main__":
    # This block is for local development.
    # For production, use a process manager like Gunicorn or Hypercorn with Uvicorn workers.
    # Example: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    logger.info(f"Starting Uvicorn development server for {settings.PROJECT_NAME} on http://0.0.0.0:8000")
    uvicorn.run(
        "main:app", # Points to the 'app' instance in this 'main.py' file
        host="0.0.0.0",
        port=8000,
        reload=True, # Enable auto-reload for development convenience
        log_level="info" # Uvicorn's own log level
    )
