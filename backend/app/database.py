import motor.motor_asyncio
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: motor.motor_asyncio.AsyncIOMotorClient = None
    db: motor.motor_asyncio.AsyncIOMotorDatabase = None

mongo_db = MongoDB()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    mongo_db.client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_CONNECTION_STRING)
    mongo_db.db = mongo_db.client[settings.MONGO_DATABASE_NAME]
    try:
        # Ping the server to check if the connection is successful
        await mongo_db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # Depending on your app's needs, you might want to raise an error or exit
        raise

async def close_mongo_connection():
    if mongo_db.client:
        logger.info("Closing MongoDB connection...")
        mongo_db.client.close()
        logger.info("MongoDB connection closed.")

async def get_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    if mongo_db.db is None:
        # This case should ideally not happen if connect_to_mongo is called at startup
        logger.warning("Database not initialized. Attempting to connect.")
        await connect_to_mongo()
    return mongo_db.db 