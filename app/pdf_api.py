from fastapi import APIRouter, HTTPException, status
from typing import Dict
from uuid import UUID
from datetime import datetime

from app.schemas.pdf import PDFRequest
from app.services import shared_state

router = APIRouter(
    prefix="/pdf",
    tags=["PDF"],
    responses={404: {"description": "Not found"}}
)

@router.post("/generate")
async def generate_pdf_report(request: PDFRequest):
    """Generate PDF report for a completed interview."""
    try:
        interview_id = str(request.interview_id)
        print(f"\n=== Generating PDF Report for Interview {interview_id} ===")
        
        # Get interview data from ai_interviews collection
        interview_data = await shared_state.mongodb.ai_interviews.find_one(
            {"interview_id": interview_id}
        )
        
        if not interview_data:
            raise HTTPException(
                status_code=404,
                detail="Interview data not found"
            )
            
        # Check if analysis exists
        analysis = interview_data.get("technical_assessment")
        if not analysis:
            raise HTTPException(
                status_code=400,
                detail="Analysis must be generated before creating PDF report"
            )
            
        # Generate PDF using the PDF service
        pdf_data = await shared_state.pdf_service.generate_report(
            interview_data=interview_data,
            analysis_data=analysis
        )
        
        if not pdf_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate PDF report"
            )
            
        # Store PDF in the same document
        await shared_state.mongodb.store_pdf_report(
            interview_id=interview_id,
            pdf_data=pdf_data
        )
        
        return {
            "status": "success",
            "message": "PDF report generated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\nError in generate_pdf_report: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{interview_id}")
async def get_pdf_report(interview_id: UUID):
    """Get the PDF report for a completed interview."""
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
            
        pdf_data = interview_data.get("pdf_report")
        if not pdf_data:
            raise HTTPException(
                status_code=404,
                detail="PDF report not found for this interview"
            )
            
        return {
            "status": "success",
            "data": pdf_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 