from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum
import datetime
from bson import ObjectId # For MongoDB _id field if not using Beanie

# Helper for MongoDB ObjectId compatibility with Pydantic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field): # Changed from (cls, v) to (cls, v, field) for Pydantic v2
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema): # Changed for Pydantic v2
        field_schema.update(type="string")

class PostStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ERROR = "error"

class Trend(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    topic: str
    source: str # e.g., "perplexity_api", "rss_feed_tech_crunch"
    relevance_score: Optional[float] = None
    summary: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None # Store original data from source
    identified_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    last_processed_at: Optional[datetime.datetime] = None

    class Config:
        populate_by_name = True # was allow_population_by_field_name = True
        json_encoders = {ObjectId: str} # For serialization
        arbitrary_types_allowed = True # To allow PyObjectId

class PostDraft(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    trend_id: Optional[PyObjectId] = None # Link to the Trend model
    headline_suggestion: Optional[str] = None
    generated_text: str
    image_prompt: Optional[str] = None
    generated_image_url: Optional[HttpUrl] = None
    ideogram_job_id: Optional[str] = None # If Ideogram provides one
    status: PostStatus = PostStatus.DRAFT
    voice_profile_used: Optional[str] = "default" # Or link to a voice profile ID
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    scheduled_publish_time: Optional[datetime.datetime] = None
    linkedin_post_id: Optional[str] = None # After publishing
    error_message: Optional[str] = None
    approval_message_sid: Optional[str] = None # Twilio SID for the approval request message

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, HttpUrl: lambda v: str(v) if v else None}
        arbitrary_types_allowed = True

class WhatsAppMessage(BaseModel): # For parsing incoming Twilio webhook (simplified)
    From: str # User's WhatsApp number e.g. "whatsapp:+1234567890"
    To: str   # Your Twilio WhatsApp number
    Body: str # Message content or button payload
    MessageSid: str

class LinkedInToken(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str # Your internal user identifier
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: datetime.datetime # Calculated from expires_in
    refresh_token_expires_at: Optional[datetime.datetime] = None # If applicable
    user_urn: Optional[str] = None # LinkedIn Person URN (needed for posting)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True 