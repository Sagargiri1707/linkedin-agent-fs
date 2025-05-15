from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
import httpx # For OAuth token exchange

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.scheduler import scheduler, start_scheduler, shutdown_scheduler
from app.services.linkedin_agent_service import (
    handle_whatsapp_approval,
    process_new_trend_for_content_generation
)
from app.services.external_apis import (
    exchange_linkedin_code_for_token,
    get_linkedin_user_profile,
    store_linkedin_token,
    get_stored_linkedin_token
)
from app.models import WhatsAppMessage, Trend, LinkedInToken

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan manager for application startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    await connect_to_mongo()
    logger.info("MongoDB connected.")
    start_scheduler()
    logger.info("Scheduler started.")
    yield
    # Shutdown
    logger.info("Application shutting down...")
    await close_mongo_connection()
    logger.info("MongoDB connection closed.")
    shutdown_scheduler()
    logger.info("Scheduler shut down.")

# Initialize FastAPI app with lifespan manager
app = FastAPI(
    title="LinkedIn Automation AI Agent",
    description="An AI agent to automate LinkedIn content creation and posting.",
    version="0.1.0",
    lifespan=lifespan
)

# --- API Endpoints ---

@app.get("/", tags=["General"])
async def read_root():
    """
    Root endpoint for health check.
    """
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}

# --- LinkedIn OAuth 2.0 Endpoints ---
LINKEDIN_AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_ACCESS_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

@app.get("/auth/linkedin/login", tags=["Authentication"])
async def linkedin_login():
    """
    Redirects the user to LinkedIn for authorization.
    """
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "state": "DCEeFWf45A53sdfKef424",  # CSRF token, generate and validate this properly
        "scope": "openid profile email w_member_social r_liteprofile rw_organization_admin w_organization_social r_organization_social" # Adjust scopes as needed
        # Common scopes:
        # r_liteprofile: Name, photo, headline
        # r_emailaddress: Email address (requires partner program for some apps)
        # w_member_social: Post, comment, react on behalf of the member
        # openid, profile, email: For Sign In with LinkedIn v2
        # For organization posting: rw_organization_admin, w_organization_social, r_organization_social
    }
    auth_url = f"{LINKEDIN_AUTHORIZATION_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    logger.info(f"Redirecting to LinkedIn for authorization: {auth_url}")
    return RedirectResponse(url=auth_url)

@app.get("/auth/linkedin/callback", tags=["Authentication"])
async def linkedin_callback(code: str, state: str, background_tasks: BackgroundTasks):
    """
    Handles the callback from LinkedIn after user authorization.
    Exchanges the authorization code for an access token.
    """
    logger.info(f"Received LinkedIn callback with code: {code}, state: {state}")
    # IMPORTANT: Validate the 'state' parameter here to prevent CSRF attacks.
    # For this example, we're skipping proper state validation.
    if state != "DCEeFWf45A53sdfKef424": # Replace with your actual state validation
        logger.error("Invalid OAuth state received from LinkedIn.")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    token_data = await exchange_linkedin_code_for_token(code)

    if not token_data or "access_token" not in token_data:
        logger.error("Failed to exchange code for access token with LinkedIn.")
        raise HTTPException(status_code=400, detail="Could not obtain access token from LinkedIn")

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600) # Default to 1 hour
    refresh_token = token_data.get("refresh_token")
    refresh_token_expires_in = token_data.get("refresh_token_expires_in")

    # Fetch user profile to get their URN (needed for posting)
    # This also verifies the access token is working.
    user_profile = await get_linkedin_user_profile(access_token)
    if not user_profile or "id" not in user_profile: # 'id' is the person URN
        logger.error("Failed to fetch user profile from LinkedIn after obtaining token.")
        raise HTTPException(status_code=500, detail="Could not fetch user profile from LinkedIn.")
    
    linkedin_user_urn = user_profile["id"]
    logger.info(f"Successfully obtained LinkedIn access token and user URN: {linkedin_user_urn}")

    # Store the token securely (e.g., in MongoDB)
    # Associate it with your internal user ID if you have a multi-user system.
    # For this personal project, we might use a default user_id.
    internal_user_id = "default_personal_user"
    
    background_tasks.add_task(
        store_linkedin_token,
        user_id=internal_user_id,
        access_token=access_token,
        expires_in=expires_in,
        refresh_token=refresh_token,
        refresh_token_expires_in=refresh_token_expires_in,
        user_urn=linkedin_user_urn # Store the URN as well
    )

    return {
        "message": "LinkedIn authentication successful! Token stored.",
        "linkedin_user_urn": linkedin_user_urn,
        # "access_token": access_token # Avoid sending token to client in production
    }

@app.post("/webhook/twilio/whatsapp", tags=["Webhooks"])
async def webhook_twilio_whatsapp(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint to receive messages/events from Twilio for WhatsApp.
    """
    try:
        form_data = await request.form()
        message_sid = form_data.get("MessageSid")
        from_number = form_data.get("From")
        body = form_data.get("Body")

        logger.info(f"Received WhatsApp message from {from_number}: '{body}' (SID: {message_sid})")

        if not message_sid or not from_number or not body:
            logger.error("Missing required fields in Twilio webhook data")
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        background_tasks.add_task(handle_whatsapp_approval, from_number, body, message_sid)
        
        return {"status": "success", "message": "Webhook received"}

    except Exception as e:
        logger.error(f"Error processing Twilio webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.post("/trigger/generate-content-from-trend", tags=["Testing"])
async def trigger_content_generation(trend_topic: str, background_tasks: BackgroundTasks):
    """
    An example endpoint to manually trigger content generation for a trend.
    """
    try:
        db = await get_database()
        trend = Trend(topic=trend_topic, source="manual_trigger", relevance_score=0.9)
        
        logger.info(f"Manually triggering content generation for trend: {trend.topic}")
        background_tasks.add_task(process_new_trend_for_content_generation, trend)
        return {"message": "Content generation process triggered in background."}
    except Exception as e:
        logger.error(f"Error triggering content generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info") 