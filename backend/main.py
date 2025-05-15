# main.py
# Main FastAPI application file for the LinkedIn Automation AI Agent.

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import RedirectResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware # Import CORS middleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import httpx # For OAuth token exchange, though it's mostly in external_apis.py
import urllib.parse # Import urllib for urlencode

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.scheduler import scheduler, start_scheduler, shutdown_scheduler
from app.services.linkedin_agent_service import (
    handle_whatsapp_approval,
    _process_single_trend_for_content # Import the helper for direct trigger
)
from app.services.external_apis import (
    exchange_linkedin_code_for_token,
    get_linkedin_user_profile,
    store_linkedin_token,
    get_stored_linkedin_token # For the /auth/linkedin/status endpoint
)
from app.models import Trend, LinkedInToken # Import necessary Pydantic models
from typing import Optional # Ensure Optional is imported

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Application Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting up {settings.PROJECT_NAME}...")
    await connect_to_mongo()
    logger.info("MongoDB connection established.")
    start_scheduler()
    logger.info("APScheduler started.")
    
    yield
    
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    await close_mongo_connection()
    logger.info("MongoDB connection closed.")
    shutdown_scheduler()
    logger.info("APScheduler shut down.")

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="An AI agent to automate LinkedIn content creation, approval, and posting.",
    version="0.1.0",
    lifespan=lifespan
)

# --- CORS Middleware Configuration ---
# Define the origins that are allowed to make requests to this backend.
# For development, this will typically be your React app's local server.
origins = [
    "http://localhost:3000",  # React default development server
    # Add any other origins if needed (e.g., your deployed frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True, # Allows cookies to be included in requests
    allow_methods=["*"],    # Allows all standard HTTP methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)

# --- API Endpoints ---

@app.get("/", tags=["General"])
async def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME}! Agent is operational."}

# --- LinkedIn OAuth 2.0 Endpoints ---
LINKEDIN_AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"

@app.get("/auth/linkedin/login", tags=["LinkedIn Authentication"])
async def linkedin_login_redirect():
    csrf_state = "SOME_RANDOM_CSRF_PREVENTION_STRING_12345" # Replace with dynamic state generation & validation
    scopes = [
        "openid", "profile", "email", "r_liteprofile", "w_member_social"
    ]
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "state": csrf_state,
        "scope": " ".join(scopes)
    }
    auth_url = f"{LINKEDIN_AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"
    logger.info(f"Redirecting user to LinkedIn for authorization: {auth_url}")
    return RedirectResponse(url=auth_url, status_code=307) # Use 307 for explicit GET redirect

@app.get("/auth/linkedin/callback", tags=["LinkedIn Authentication"])
async def linkedin_oauth_callback(code: str, state: str, background_tasks: BackgroundTasks):
    logger.info(f"Received LinkedIn OAuth callback. Code: '{code[:15]}...', State: '{state}'")
    expected_state = "SOME_RANDOM_CSRF_PREVENTION_STRING_12345" # Validate this properly
    
    # Define frontend URL (React app's typical dev server)
    frontend_url = "http://localhost:3000" 

    if state != expected_state:
        logger.error("Invalid OAuth state received from LinkedIn. Potential CSRF attack.")
        return RedirectResponse(url=f"{frontend_url}/?auth_error=InvalidState", status_code=307)

    token_data = await exchange_linkedin_code_for_token(code)
    if not token_data or "access_token" not in token_data:
        logger.error("Failed to exchange authorization code for access token with LinkedIn.")
        return RedirectResponse(url=f"{frontend_url}/?auth_error=TokenExchangeFailed", status_code=307)

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)
    refresh_token = token_data.get("refresh_token")
    refresh_token_expires_in = token_data.get("refresh_token_expires_in")

    user_profile = await get_linkedin_user_profile(access_token)
    if not user_profile or "id" not in user_profile:
        logger.error("Failed to fetch user profile (URN) from LinkedIn after obtaining token.")
        return RedirectResponse(url=f"{frontend_url}/?auth_error=ProfileFetchFailed", status_code=307)
    
    linkedin_user_urn = user_profile["id"]
    logger.info(f"Successfully obtained LinkedIn access token. User URN: {linkedin_user_urn}")

    from app.services.linkedin_agent_service import DEFAULT_USER_ID # Import here to avoid circular dependency issues at module level
    internal_user_id = DEFAULT_USER_ID
    
    background_tasks.add_task(
        store_linkedin_token,
        user_id=internal_user_id,
        access_token_value=access_token,
        expires_in=expires_in,
        user_urn=linkedin_user_urn,
        refresh_token_value=refresh_token,
        refresh_token_expires_in=refresh_token_expires_in
    )
    
    logger.info("Redirecting to frontend after successful LinkedIn authentication.")
    return RedirectResponse(url=f"{frontend_url}/?auth_success=true", status_code=307)


@app.get("/auth/linkedin/status", tags=["LinkedIn Authentication"])
async def get_linkedin_authentication_status():
    from app.services.linkedin_agent_service import DEFAULT_USER_ID # Import here
    token: Optional[LinkedInToken] = await get_stored_linkedin_token(DEFAULT_USER_ID)
    if token and token.access_token:
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
    try:
        form_data = await request.form()
        message_sid = form_data.get("MessageSid")
        from_number = form_data.get("From")
        body = form_data.get("Body")

        logger.info(f"Received WhatsApp message from {from_number} (SID: {message_sid}): '{body}'")
        if not all([message_sid, from_number, body]):
            logger.error("Missing required fields (MessageSid, From, Body) in Twilio webhook data.")
            raise HTTPException(status_code=400, detail="Missing required fields in Twilio webhook data")

        background_tasks.add_task(handle_whatsapp_approval, from_number, body, message_sid)
        
        # Twilio expects TwiML. Responding with an empty MessagingResponse is standard.
        from twilio.twiml.messaging_response import MessagingResponse
        twiml_response = MessagingResponse()
        return PlainTextResponse(str(twiml_response), media_type="application/xml")

    except Exception as e:
        logger.error(f"Error processing Twilio WhatsApp webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error processing webhook")


@app.post("/trigger/generate-content", tags=["Testing & Triggers"])
async def trigger_content_generation_for_trend(trend_topic: str, background_tasks: BackgroundTasks):
    try:
        db = await get_database()
        trend = Trend(
            topic=trend_topic,
            source="manual_trigger_endpoint",
            summary=f"Manually triggered content generation for the topic: {trend_topic}",
            relevance_score=0.95
        )
        logger.info(f"Manually triggering content generation for trend topic: '{trend.topic}'")
        background_tasks.add_task(_process_single_trend_for_content, trend)
        return {"message": f"Content generation process for '{trend.topic}' triggered in the background."}
    except Exception as e:
        logger.error(f"Error triggering manual content generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error triggering content generation: {str(e)}")

if __name__ == "__main__":
    logger.info(f"Starting Uvicorn development server for {settings.PROJECT_NAME} on http://0.0.0.0:8000")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
