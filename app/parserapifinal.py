from fastapi import FastAPI, HTTPException, UploadFile, File, APIRouter
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime
import os
from PyPDF2 import PdfReader
from app.services import shared_state
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

router = APIRouter(
    tags=["Resume"],
    responses={404: {"description": "Not found"}}
)

class PDFTextExtractor:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text()
            return text.strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")

class ResumeExtractor:
    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=groq_api_key,
            model="llama-3.3-70b-versatile"
        )

    def extract_skills(self, resume_text: str) -> Dict[str, Any]:
        """Extract technical skills from resume text."""
        skills_prompt = """
        Extract ALL technical skills from the following resume text. Include:
        1. Programming Languages
        2. Frameworks & Libraries
        3. Databases
        4. Cloud Services
        5. Tools & Software
        6. Other Technical Skills

        Resume Text:
        {text}

        Return ONLY a JSON object with this structure:
        {{"technical_skills": ["skill1", "skill2", "skill3", ...]}}
        """
        
        try:
            messages = [
                SystemMessage(content="Extract technical skills from resumes."),
                HumanMessage(content=skills_prompt.format(text=resume_text))
            ]
            
            response = self.llm.invoke(messages)
            
            # Clean and parse response
            response_text = response.content.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            import json
            skills = json.loads(response_text.strip())
            skills["technical_skills"] = sorted(list(set(str(skill).strip() 
                                                      for skill in skills["technical_skills"])))
            return skills
            
        except Exception as e:
            return {"technical_skills": []}

@router.post("/")
async def parse_resume(file: UploadFile = File(...), candidate_name: str = None):
    """Upload and parse a resume PDF."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_path = f"temp_{file.filename}"
    try:
        # Save uploaded file
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Extract text
        resume_text = PDFTextExtractor.extract_text(temp_path)
        if not resume_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from the resume")
        
        # Extract skills
        extractor = ResumeExtractor(os.getenv("GROQ_API_KEY"))
        skills = extractor.extract_skills(resume_text)
        
        # Generate interview ID and store data
        interview_id = str(uuid4())
        await shared_state.mongodb.store_resume_data(
            interview_id=interview_id,
            data={
                "resume_text": resume_text,
                "technical_skills": skills.get("technical_skills", []),
                "candidate_name": candidate_name or "Anonymous",
                "status": "initialized"
            }
        )
        
        return {
            "interview_id": interview_id,
            "technical_skills": skills.get("technical_skills", []),
            "status": "initialized",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
