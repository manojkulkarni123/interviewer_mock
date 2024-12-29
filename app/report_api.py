from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from uuid import UUID
import json
import os
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from app.schemas.models import InterviewTranscript, PerformanceReport, QuestionAnswer
from app.services import shared_state
import requests
import base64
from fastapi import APIRouter, Request
from app.pdf_report_generator import generate_pdf_report
from app.analysis_utils import analyze_performance_from_json

app = FastAPI(
    title="Interview Analysis API",
    description="API for analyzing interview transcripts and generating performance reports",
    version="1.0.0"
)

ANALYSIS_PROMPT = """Analyze the following interview transcript and provide a performance evaluation. 
Your response must be a valid JSON object with no trailing commas and properly quoted strings.

Interview Details:
Candidate Name: {candidate_name}
Position Applied: {position_applied}
Interview Date: {interview_date}
Interviewer: {interviewer_name}

Transcript:
{transcript}

Additional Notes:
{extra_prompt}

Provide your analysis in the following JSON format:
{{
    "personal_details": {{
        "candidate_name": "{candidate_name}",
        "position_applied": "{position_applied}",
        "interview_date": "{interview_date}",
        "interviewer_name": "{interviewer_name}"
    }},
    "skill_categories": {{
        "Technical Proficiency": {{
            "rating": 8.0,
            "evidence": "Demonstrated strong technical knowledge",
            "subcategories": {{
                "Core Knowledge": {{
                    "rating": 8.0,
                    "evidence": "Specific example from interview"
                }},
                "Tools and Software": {{
                    "rating": 8.0,
                    "evidence": "Specific example from interview"
                }},
                "Domain-Specific Knowledge": {{
                    "rating": 8.0,
                    "evidence": "Specific example from interview"
                }}
            }}
        }},
        "Problem Solving": {{
            "rating": 8.0,
            "evidence": "Strong analytical abilities",
            "subcategories": {{
                "Algorithmic Thinking": {{
                    "rating": 8.0,
                    "evidence": "Specific example from interview"
                }},
                "Analytical Skills": {{
                    "rating": 8.0,
                    "evidence": "Specific example from interview"
                }},
                "Innovation": {{
                    "rating": 8.0,
                    "evidence": "Specific example from interview"
                }}
            }}
        }},
        "Behavioral Skills": {{
            "rating": 8.0,
            "evidence": "Excellent communication",
            "subcategories": {{
                "Team Collaboration": {{
                    "rating": 8.0,
                    "evidence": "Specific example from interview"
                }},
                "Communication": {{
                    "rating": 8.0,
                    "evidence": "Specific example from interview"
                }},
                "Leadership": {{
                    "rating": 8.0,
                    "evidence": "Specific example from interview"
                }}
            }}
        }}
    }},
    "overall_performance": "Strong technical background with good communication skills",
    "overall_rating": 8.0,
    "result": "Pass",
    "evidence": [
        "Key strength point 1",
        "Key strength point 2",
        "Area for improvement 1",
        "Area for improvement 2"
    ]
}}

Remember:
1. All ratings must be between 0.0 and 10.0
2. Result must be "Pass" if overall_rating >= 7.0, "Fail" if < 7.0
3. Provide specific evidence from the transcript for each rating
4. Maintain the exact JSON structure shown above
"""

async def analyze_performance_from_json(json_data: dict, extra_prompt: str = "") -> dict:
    try:
        # Validate and extract data
        if "question_answer" not in json_data:
            raise HTTPException(status_code=400, detail="Missing required field: question_answer")

        # Format the transcript
        combined_transcript = ""
        for qa in json_data["question_answer"]:
            question = qa.get("question", "").strip()
            answer = qa.get("answer", "").strip()
            if question and answer:
                combined_transcript += f"Question: {question}\nAnswer: {answer}\n\n"

        # Prepare messages for Groq API
        messages = [
            {
                "role": "system",
                "content": "You are an expert interviewer evaluating candidates. You must provide your response in valid JSON format exactly matching the template provided."
            },
            {
                "role": "user",
                "content": ANALYSIS_PROMPT.format(
                    transcript=combined_transcript,
                    candidate_name=json_data.get("candidate_name", "Unknown"),
                    position_applied=json_data.get("position_applied", "Unknown"),
                    interview_date=json_data.get("interview_date", "Unknown"),
                    interviewer_name=json_data.get("interviewer_name", "Unknown"),
                    extra_prompt=extra_prompt
                )
            }
        ]

        # Call Groq API directly
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0,
                "max_tokens": 2000
            }
        )
        response.raise_for_status()
        
        # Get response content
        response_text = response.json()["choices"][0]["message"]["content"].strip()
        
        # Debug print
        print("\nRaw response:", response_text)
        
        # Remove any markdown formatting
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
        if response_text.startswith('json'):
            response_text = response_text[4:]
        response_text = response_text.strip()
        
        try:
            analysis = json.loads(response_text)
            
            # Simple validation based on overall rating
            if analysis["overall_rating"] < 7.0:
                analysis["result"] = "Fail"
            else:
                analysis["result"] = "Pass"
            
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"\nJSON Decode Error: {str(e)}")
            print(f"Problematic content: {response_text}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse model response: {str(e)}"
            )

    except Exception as e:
        print(f"\nError in analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in analysis: {str(e)}"
        )

async def generate_performance_charts(analysis_data, candidate_info):
    """Generate both radar and bar charts for the interview analysis."""
    try:
        # Create directories with absolute paths
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, 'analysis_charts')
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate Radar Chart for main categories
        categories = []
        ratings = []
        
        for category, details in analysis_data['skill_categories'].items():
            rating = details.get('rating')
            if rating is not None:  # Only add categories with ratings
                categories.append(category)
                ratings.append(float(rating))
        
        # Add overall rating to radar chart
        overall_rating = analysis_data.get('overall_rating')
        if overall_rating is not None:
            categories.append("Overall")
            ratings.append(float(overall_rating))
        
        if not categories or not ratings:  # If no valid ratings found
            print("No valid ratings found for radar chart")
            return None, None
        
        # Create radar chart
        num_vars = len(categories)
        theta = np.linspace(0, 2*np.pi, num_vars, endpoint=False)
        
        fig1 = plt.figure(figsize=(8, 8))
        ax = fig1.add_subplot(111, projection='polar')
        
        # Plot the data on radar chart
        ax.plot(theta, ratings, 'o-', linewidth=2, label='Ratings')
        ax.fill(theta, ratings, alpha=0.25)
        ax.set_xticks(theta)
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 10)
        
        # Add title to radar chart
        plt.title(f"Category Performance - {candidate_info['candidate_name']}\n{candidate_info['position_applied']}", 
                 pad=20)
        
        # Add result annotation to radar chart
        result_text = f"Overall: {analysis_data['overall_rating']:.1f}\nResult: {analysis_data['result']}"
        plt.annotate(result_text, 
                    xy=(0, 0), 
                    xytext=(0.95, 0.95),
                    textcoords='figure fraction',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                    horizontalalignment='right',
                    verticalalignment='top')
        
        # Save radar chart with absolute path
        radar_filename = os.path.join(output_dir, 
                                    f"radar_chart_{candidate_info['candidate_name'].replace(' ', '_')}.png")
        plt.savefig(radar_filename, bbox_inches='tight', dpi=300)
        plt.close()
        
        # Generate Bar Chart for subcategories
        sub_categories = []
        sub_ratings = []
        
        for category, details in analysis_data['skill_categories'].items():
            for sub_name, sub_details in details['subcategories'].items():
                rating = sub_details.get('rating')
                if rating is not None:  # Only add subcategories with ratings
                    sub_categories.append(f"{category}\n{sub_name}")
                    sub_ratings.append(float(rating))
        
        if not sub_categories or not sub_ratings:  # If no valid ratings found
            print("No valid ratings found for bar chart")
            return radar_filename, None
        
        # Create bar chart
        fig2 = plt.figure(figsize=(12, 8))
        ax = fig2.add_subplot(111)
        
        # Plot bars
        x = np.arange(len(sub_categories))
        bars = ax.bar(x, sub_ratings, width=0.8)
        
        # Customize bar chart
        ax.set_ylabel('Rating')
        ax.set_title(f'Subcategory Performance - {candidate_info["candidate_name"]}')
        ax.set_xticks(x)
        ax.set_xticklabels(sub_categories, rotation=45, ha='right')
        ax.set_ylim(0, 10)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}',
                   ha='center', va='bottom')
        
        # Adjust layout
        plt.subplots_adjust(bottom=0.2)
        
        # Save bar chart with absolute path
        bar_filename = os.path.join(output_dir, 
                                  f"bar_chart_{candidate_info['candidate_name'].replace(' ', '_')}.png")
        plt.savefig(bar_filename, bbox_inches='tight', dpi=300)
        plt.close()
        
        return radar_filename, bar_filename
        
    except Exception as e:
        print(f"Error generating charts: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None, None

class QuestionAnswer(BaseModel):
    question: str
    answer: str

class AnalysisRequest(BaseModel):
    candidate_name: str
    position_applied: str
    question_answer: List[QuestionAnswer]
    interview_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    interviewer_name: str = "AI Interviewer"

@app.post("/{interview_id}")
async def analyze_interview(interview_id: UUID, extra_prompt: Optional[str] = ""):
    """Generate analysis and charts for an interview using its ID."""
    try:
        # Get interview data from MongoDB
        interview_session = await shared_state.mongodb.get_interview_session(interview_id)
        if not interview_session:
            raise HTTPException(status_code=404, detail="Interview not found")

        # Format data for analysis
        analysis_request = {
            "candidate_name": interview_session.get("candidate_name", "Unknown"),
            "position_applied": interview_session.get("role", "Unknown"),
            "interview_date": interview_session.get("start_time", datetime.utcnow()).strftime("%Y-%m-%d"),
            "interviewer_name": "AI Interviewer",
            "question_answer": interview_session.get("conversation_history", [])
        }

        # Get analysis
        analysis = await analyze_performance_from_json(analysis_request, extra_prompt)
        
        # Generate charts
        radar_chart_path, bar_chart_path = await generate_performance_charts(
            analysis, 
            {"candidate_name": analysis_request["candidate_name"], 
             "position_applied": analysis_request["position_applied"]}
        )

        # Read charts as base64
        def read_file_as_base64(file_path: str) -> Optional[str]:
            if not file_path:
                return None
            try:
                with open(file_path, "rb") as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"Error reading file {file_path}: {str(e)}")
                return None

        # Save analysis JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        analysis_dir = os.path.join(base_dir, 'analysis_results')
        os.makedirs(analysis_dir, exist_ok=True)
        
        analysis_filename = os.path.join(
            analysis_dir, 
            f"analysis_{interview_id}_{timestamp}.json"
        )
        
        analysis_data = {
            "interview_id": str(interview_id),
            "candidate_info": analysis_request,
            "analysis": analysis,
            "file_paths": {
                "analysis_json": analysis_filename,
                "radar_chart": radar_chart_path,
                "bar_chart": bar_chart_path
            },
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save to file and MongoDB
        with open(analysis_filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=4, default=str)

        # Update interview document with analysis data
        await shared_state.mongodb.ai_interviews.update_one(
            {"interview_id": str(interview_id)},
            {"$set": analysis_data},
            upsert=True
        )

        # Prepare response
        response = {
            "status": "success",
            "data": {
                "interview_id": str(interview_id),
                "analysis": analysis,
                "charts": {
                    "radar_chart": read_file_as_base64(radar_chart_path),
                    "bar_chart": read_file_as_base64(bar_chart_path)
                },
                "file_paths": analysis_data["file_paths"]
            }
        }

        return JSONResponse(content=response)

    except Exception as e:
        print(f"\nError in analyze_interview: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/report/{interview_id}")
async def get_interview_report(interview_id: UUID):
    """Get the analysis report for an interview."""
    try:
        # Get analysis from MongoDB
        analysis = await shared_state.mongodb.ai_interviews.find_one(
            {"interview_id": str(interview_id)}
        )
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Verify files exist
        for path_type, file_path in analysis["file_paths"].items():
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found: {path_type}"
                )

        # Read files as base64
        def read_file_as_base64(file_path: str) -> str:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')

        return {
            "interview_id": str(interview_id),
            "analysis": analysis["analysis"],
            "charts": {
                "radar_chart": read_file_as_base64(analysis["file_paths"]["radar_chart"]),
                "bar_chart": read_file_as_base64(analysis["file_paths"]["bar_chart"])
            },
            "file_paths": analysis["file_paths"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/")
async def root():
    return {"message": "Interview Analysis API is running"}

router = APIRouter(
    prefix="/report",
    tags=["Report Generation"]
)

@router.post("/generate/{interview_id}")
async def generate_report(interview_id: str):
    """Generate a PDF report for the interview."""
    try:
        # Get interview data first to check if it exists
        interview_data = await shared_state.mongodb.ai_interviews.find_one(
            {"interview_id": interview_id}
        )
        
        if not interview_data:
            raise HTTPException(status_code=404, detail="Interview not found")
            
        # Check if candidate name is stored in MongoDB
        candidate_name = interview_data.get("candidate_name", "").strip()
        if not candidate_name or candidate_name == "Anonymous":
            raise HTTPException(
                status_code=400, 
                detail="Candidate name is required. Please update the candidate information before generating the report."
            )
        
        # Generate the PDF report
        report_result = await generate_pdf_report(interview_id)
        return report_result
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)