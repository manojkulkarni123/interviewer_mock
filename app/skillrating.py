from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel, Field
from typing import Dict
from app.services import shared_state

router = APIRouter(
    tags=["Skills"],
    responses={404: {"description": "Not found"}}
)

class SkillRatingRequest(BaseModel):
    interview_id: str
    skills: Dict[str, float] = Field(..., description="Dictionary of skill ratings (0-10)")

@router.post("/")
async def rate_skills(request: SkillRatingRequest):
    """Rate technical skills for an interview session."""
    try:
        # First verify the interview exists and has technical skills
        interview = await shared_state.mongodb.ai_interviews.find_one(
            {"interview_id": request.interview_id}
        )
        
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
            
        if not interview.get("technical_skills"):
            raise HTTPException(status_code=400, detail="No technical skills found for this interview")
        
        # Validate that we're only rating skills that were extracted from the resume
        invalid_skills = [skill for skill in request.skills.keys() 
                         if skill not in interview["technical_skills"]]
        if invalid_skills:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid skills provided: {', '.join(invalid_skills)}"
            )
        
        # Validate ratings (0-10)
        for skill, rating in request.skills.items():
            if not (0 <= rating <= 10):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Rating for '{skill}' must be between 0 and 10"
                )
        
        # Update skill ratings in MongoDB
        await shared_state.mongodb.update_interview_session_skills(
            interview_id=request.interview_id,
            skills=request.skills
        )
        
        # Update interview status
        await shared_state.mongodb.ai_interviews.update_one(
            {"interview_id": request.interview_id},
            {"$set": {"status": "skills_rated"}}
        )
        
        return {
            "interview_id": request.interview_id,
            "skills": request.skills,
            "status": "skills_rated"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))