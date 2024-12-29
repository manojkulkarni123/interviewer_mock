"""
Shared state module for managing global services.
"""
from app.services.mongodb_service import MongoDBService
from app.services.groq_service import GroqService
import asyncio

# Global service instances
mongodb: MongoDBService = None
groq_service: GroqService = None

async def init_services(mongo_uri: str):
    """Initialize global services."""
    global mongodb, groq_service
    
    try:
        # Initialize MongoDB
        if mongodb is None:
            mongodb = MongoDBService()
        await mongodb.initialize(mongo_uri)
        
        # Initialize Groq service
        if groq_service is None:
            groq_service = GroqService()
        
        print("Services initialized successfully")
        return mongodb, groq_service
        
    except Exception as e:
        print(f"Error initializing services: {e}")
        # Clean up on error
        if mongodb and mongodb.client:
            mongodb.client.close()
        raise

def cleanup_services():
    """Cleanup service connections."""
    global mongodb, groq_service
    
    if mongodb and mongodb.client:
        mongodb.client.close()
        mongodb = None
    
    groq_service = None

# Register cleanup on module unload
import atexit
atexit.register(cleanup_services)

def get_mongodb() -> MongoDBService:
    """Get MongoDB service instance."""
    if mongodb is None:
        raise RuntimeError("MongoDB service not initialized")
    return mongodb

def get_groq_service() -> GroqService:
    """Get Groq service instance."""
    if groq_service is None:
        raise RuntimeError("Groq service not initialized")
    return groq_service