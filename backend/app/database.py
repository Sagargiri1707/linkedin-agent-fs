# app/database.py
# Handles MongoDB connection and provides a way to access the database instance.

import motor.motor_asyncio # Asynchronous MongoDB driver
from app.config import settings # Import the application settings
import logging

# Get a logger instance for this module
logger = logging.getLogger(__name__)

class MongoDB:
    """
    A class to manage the MongoDB client and database instances.
    This helps in organizing the connection state.
    """
    client: motor.motor_asyncio.AsyncIOMotorClient = None
    db: motor.motor_asyncio.AsyncIOMotorDatabase = None

# Global instance of the MongoDB manager
mongo_db_manager = MongoDB()

async def connect_to_mongo():
    """
    Establishes a connection to the MongoDB server and initializes the database instance.
    This function should be called during application startup.
    """
    logger.info("Attempting to connect to MongoDB...")
    try:
        # Create a new Motor client instance
        mongo_db_manager.client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGO_CONNECTION_STRING,
            # You can add serverSelectionTimeoutMS if needed, e.g., serverSelectionTimeoutMS=5000
        )
        # Get the database instance from the client
        mongo_db_manager.db = mongo_db_manager.client[settings.MONGO_DATABASE_NAME]

        # Ping the server to verify the connection.
        # The ping command is cheap and does not require auth.
        await mongo_db_manager.client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB. Database: '{settings.MONGO_DATABASE_NAME}'")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
        # Depending on your application's needs, you might want to raise an error
        # or handle this more gracefully (e.g., allow the app to start but log the error).
        # For now, we'll re-raise to make it explicit during startup if connection fails.
        raise ConnectionError(f"Could not connect to MongoDB: {e}")


async def close_mongo_connection():
    """
    Closes the MongoDB connection.
    This function should be called during application shutdown.
    """
    if mongo_db_manager.client:
        logger.info("Closing MongoDB connection...")
        mongo_db_manager.client.close()
        logger.info("MongoDB connection closed.")
    else:
        logger.info("MongoDB client not initialized, no connection to close.")

async def get_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """
    Returns the initialized MongoDB database instance.
    If the database is not initialized, it attempts to connect.
    (Ideally, connect_to_mongo should be called at app startup).
    """
    if mongo_db_manager.db is None:
        logger.warning("MongoDB database instance is None. Attempting to connect now...")
        # This is a fallback, connection should ideally be established at startup.
        await connect_to_mongo()
    return mongo_db_manager.db

# Example usage (optional, for direct testing of this module)
# if __name__ == "__main__":
#     import asyncio
#     async def test_db_connection():
#         try:
#             await connect_to_mongo()
#             db = await get_database()
#             print(f"Database object: {db}")
#             # Example: List collections (requires auth if not on localhost without auth)
#             # collections = await db.list_collection_names()
#             # print(f"Collections: {collections}")
#         except Exception as e:
#             print(f"Test connection failed: {e}")
#         finally:
#             await close_mongo_connection()
#
#     asyncio.run(test_db_connection())
