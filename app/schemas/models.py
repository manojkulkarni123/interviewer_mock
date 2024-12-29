from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class QuestionAnswer(BaseModel):
    question: str
    answer: str
    skill: Optional[str] = None

class InterviewTranscript(BaseModel):
    candidate_name: str
    position_applied: str
    interview_date: str
    interviewer_name: str
    question_answer: List[QuestionAnswer]

class PerformanceReport(BaseModel):
    personal_details: Dict
    skill_categories: Dict
    overall_performance: str
    overall_rating: float
    result: str
    evidence: List[str]

class ReportRequest(BaseModel):
    analysis_file: str
    radar_chart: str
    bar_chart: str 