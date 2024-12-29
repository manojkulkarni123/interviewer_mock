from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from .models import QuestionAnswer
from uuid import UUID

class InterviewResponse(BaseModel):
    interview_id: UUID
    question: str
    conversation_context: str
    current_skill: str
    interviewer_intro: Optional[str] = None
    interview_progress: Optional[str] = None

class StartInterviewRequest(BaseModel):
    interview_id: UUID
    role: str
    experience_level: str
    candidate_name: Optional[str] = None
    resume_text: Optional[str] = None

class InterviewRequest(BaseModel):
    interview_id: UUID
    conversation_history: List[QuestionAnswer]
    role: str
    experience_level: str
    skills: Dict[str, int]
    candidate_name: Optional[str] = None

class InterviewPlan(BaseModel):
    skill_plan: List[Dict[str, Any]]
    cross_skill_opportunities: List[str]
    estimated_total_questions: int
    strategy_notes: str