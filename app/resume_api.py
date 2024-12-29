from fastapi import File, Form, UploadFile, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login.exceptions import InvalidCredentialsException
from fastapi_login.token import generate_token
from fastapi_login.utils import verify_password
from uuid import uuid4

from app.models import User
from app.utils import process_resume, extract_technical_skills
from app.state import shared_state

from fastapi import APIRouter

router = APIRouter()

@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    candidate_name: str = Form(...)
):
    """Upload and process a resume file."""
    try:
        # Validate candidate name
        candidate_name = candidate_name.strip()
        if not candidate_name:
            raise HTTPException(
                status_code=400,
                detail="Candidate name is required"
            )

        # Read and process resume
        resume_text = await process_resume(file)
        
        # Extract technical skills
        technical_skills = extract_technical_skills(resume_text)
        
        # Generate unique interview ID
        interview_id = uuid4()
        
        # Store in MongoDB with candidate name
        await shared_state.mongodb.store_resume_data(
            interview_id=interview_id,
            data={
                "resume_text": resume_text,
                "technical_skills": technical_skills,
                "candidate_name": candidate_name
            }
        )
        
        return {
            "status": "success",
            "message": "Resume uploaded and processed successfully",
            "interview_id": str(interview_id),
            "technical_skills": technical_skills,
            "candidate_name": candidate_name
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 