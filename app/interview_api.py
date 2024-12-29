from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from app.schemas.interview import StartInterviewRequest, InterviewResponse
from app.schemas.models import QuestionAnswer
from app.services import shared_state

router = APIRouter(
    tags=["Interview"],
    responses={404: {"description": "Not found"}}
)

class InterviewRequest(BaseModel):
    interview_id: str
    role: str
    experience_level: str
    conversation_history: List[QuestionAnswer]

@router.post("/start", response_model=InterviewResponse)
async def start_interview(request: StartInterviewRequest):
    """Start a new interview session."""
    try:
        # Get resume data from ai_interviews collection
        resume_data = await shared_state.mongodb.ai_interviews.find_one(
            {"interview_id": str(request.interview_id)}
        )
        
        if not resume_data:
            raise HTTPException(status_code=404, detail="Resume data not found")
        
        # Get skill ratings from the same session
        if not resume_data.get("skills"):
            raise HTTPException(
                status_code=400, 
                detail="Skills must be rated before starting interview"
            )
        
        # Ensure we have a valid candidate name
        candidate_name = resume_data.get("candidate_name", "").strip()
        if not candidate_name or candidate_name == "Anonymous":
            # Try to get candidate name from request
            if request.candidate_name:
                candidate_name = request.candidate_name.strip()
            
            if not candidate_name or candidate_name == "Anonymous":
                raise HTTPException(
                    status_code=400,
                    detail="Candidate name is required. Please provide a name during resume upload."
                )
        
        # Update interview details and set status to 'active'
        await shared_state.mongodb.update_interview_details(
            interview_id=str(request.interview_id),
            data={
                "role": request.role,
                "experience_level": request.experience_level,
                "status": "active",
                "candidate_name": candidate_name  # Use the validated name
            }
        )
        
        # Prepare context for LLM
        context = {
            "interview_id": str(request.interview_id),
            "role": request.role,
            "experience_level": request.experience_level,
            "candidate_name": candidate_name,
            "technical_skills": resume_data.get("technical_skills", []),
            "resume_text": resume_data.get("resume_text", ""),
            "is_start": True  # Flag to indicate this is the interview start
        }
        
        # Get personalized introduction from LLM
        response = await shared_state.groq_service.get_interview_response(context)
        
        if response["status"] != "success":
            raise HTTPException(
                status_code=500,
                detail="Failed to generate interview introduction"
            )
            
        # Format response to match InterviewResponse model
        formatted_response = {
            "interview_id": request.interview_id,  # Using UUID from request
            "question": response["data"]["question"],
            "conversation_context": response["data"]["conversation_context"],
            "current_skill": response["data"]["current_skill"],
            "interviewer_intro": response["data"]["interviewer_intro"],
            "interview_progress": response["data"]["interview_progress"]
        }
            
        return InterviewResponse(**formatted_response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/continue", response_model=InterviewResponse)
async def continue_interview(request: InterviewRequest):
    """Continue an ongoing interview session."""
    try:
        interview_id = request.interview_id
        
        # Get interview session
        session = await shared_state.mongodb.get_interview_session(interview_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found")
            
        # Check if interview is active
        if session["status"] not in ["active", "in_progress"]:
            raise HTTPException(
                status_code=400,
                detail=f"Interview is not active (current status: {session['status']})"
            )
        
        # Add the latest Q&A to history
        if request.conversation_history:
            latest_qa = request.conversation_history[-1]
            new_interaction = {
                "question": latest_qa.question,
                "answer": latest_qa.answer,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await shared_state.mongodb.add_to_history(str(interview_id), new_interaction)
        
        # Get updated session with skills
        updated_session = await shared_state.mongodb.get_interview_session(interview_id)
        
        # Generate next question
        state = {
            "interview_id": str(interview_id),
            "role": request.role,
            "experience_level": request.experience_level,
            "skills": updated_session.get("skills", {}),
            "conversation_history": updated_session.get("conversation_history", [])
        }
        
        response = await shared_state.groq_service.get_interview_response(state)
        
        if response["status"] != "success":
            raise HTTPException(
                status_code=500,
                detail="Failed to generate interview question"
            )
            
        return InterviewResponse(**response["data"])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{interview_id}/status")
async def get_interview_status(interview_id: UUID):
    """Get the current status of an interview session."""
    try:
        session = await shared_state.mongodb.ai_interviews.find_one({"interview_id": str(interview_id)})
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found")
            
        return {
            "interview_id": str(interview_id),
            "role": session.get("role"),
            "candidate_name": session.get("candidate_name"),
            "technical_skills": session.get("technical_skills", []),
            "start_time": session.get("metadata", {}).get("created_at"),
            "last_activity": session.get("metadata", {}).get("last_updated"),
            "question_count": len(session.get("conversation_history", [])),
            "status": session.get("status", "unknown")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 