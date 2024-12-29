from fastapi import APIRouter, HTTPException, status
from typing import Dict
from uuid import UUID
from datetime import datetime

from app.schemas.analysis import AnalysisRequest
from app.services import shared_state

router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
    responses={404: {"description": "Not found"}}
)

@router.post("/generate")
async def generate_analysis(request: AnalysisRequest):
    """Generate analysis for a completed interview."""
    try:
        interview_id = str(request.interview_id)
        print(f"\n=== Generating Analysis for Interview {interview_id} ===")
        
        # Get interview data from ai_interviews collection
        interview_data = await shared_state.mongodb.ai_interviews.find_one(
            {"interview_id": interview_id}
        )
        
        if not interview_data:
            raise HTTPException(
                status_code=404,
                detail="Interview data not found"
            )
            
        # Check if interview has conversation history
        conversation_history = interview_data.get("conversation_history", [])
        if not conversation_history:
            raise HTTPException(
                status_code=400,
                detail="No conversation history found for analysis"
            )
            
        # Generate analysis using Groq
        analysis_data = await shared_state.groq_service.generate_analysis(
            role=interview_data.get("role", "software engineer"),
            conversation_history=conversation_history,
            skills=interview_data.get("skills", {})
        )
        
        if not analysis_data or analysis_data.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail="Failed to generate analysis"
            )
            
        # Store analysis in the same document
        await shared_state.mongodb.store_analysis(
            interview_id=interview_id,
            analysis_data=analysis_data["data"]
        )
        
        return {
            "status": "success",
            "data": analysis_data["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\nError in generate_analysis: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{interview_id}")
async def get_analysis(interview_id: UUID):
    """Get the analysis for a completed interview."""
    try:
        # Get interview data from ai_interviews collection
        interview_data = await shared_state.mongodb.ai_interviews.find_one(
            {"interview_id": str(interview_id)}
        )
        
        if not interview_data:
            raise HTTPException(
                status_code=404,
                detail="Interview data not found"
            )
            
        analysis = interview_data.get("technical_assessment")
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found for this interview"
            )
            
        return {
            "status": "success",
            "data": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
 