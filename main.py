from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv
from datetime import datetime
import os
import asyncio
from uuid import UUID

# Import routers
from app.parserapifinal import router as resume_router
from app.skillrating import router as skills_router
from app.interview_api import router as interview_router
from app.pdf_report_generator import generate_pdf_report, get_pdf_report

from app.services import shared_state

# Initialize FastAPI app
app = FastAPI(
    title="AI Technical Interviewer API",
    description="An AI-powered technical interview system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(resume_router, prefix="/resume")
app.include_router(skills_router, prefix="/skills")
app.include_router(interview_router, prefix="/interview")

# Add PDF report routes
@app.post("/report/generate/{interview_id}")
async def generate_report(interview_id: str):
    """Generate PDF report for an interview."""
    return await generate_pdf_report(interview_id)

@app.get("/report/{interview_id}")
async def get_report(interview_id: str):
    """Get the generated PDF report."""
    return await get_pdf_report(interview_id)

# Load environment variables at startup
load_dotenv()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Verify environment variables
        required_vars = ["MONGO_URI", "GROQ_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        await shared_state.init_services(os.getenv("MONGO_URI"))
        print("Services initialized successfully")
    except Exception as e:
        print(f"Failed to initialize services: {e}")
        raise

@app.get("/health")
async def health_check():
    """API health check endpoint."""
    try:
        # Check MongoDB connection
        db_status = "active" if await shared_state.mongodb.check_connection() else "error"
        
        return {
            "status": "healthy" if db_status == "active" else "unhealthy",
            "services": {
                "database": {
                    "status": db_status,
                    "error": None if db_status == "active" else "MongoDB connection failed"
                },
                "parser": {"status": "active", "mounted": True},
                "skill_rating": {"status": "active", "mounted": True},
                "interview": {"status": "active", "mounted": True},
                "report": {"status": "active", "mounted": True}
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "services": {
                "database": {"status": "error", "error": str(e)},
                "parser": {"status": "active", "mounted": True},
                "skill_rating": {"status": "active", "mounted": True},
                "interview": {"status": "active", "mounted": True},
                "report": {"status": "active", "mounted": True}
            },
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 