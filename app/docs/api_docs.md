# AI Technical Interviewer API Documentation

## Overview
This API provides endpoints for conducting automated technical interviews using AI. The system uses the Groq LLM to generate context-aware interview questions and maintain conversation flow. Each interview session is assigned a unique UUID based on the candidate's resume content, ensuring consistent identification throughout the interview process.

## Endpoints

### 1. Start Interview
**POST** `/interview/start`

Starts a new interview session with an initial question. A unique interview ID is generated based on the resume content and candidate information.

Request Body:
```json
{
    "role": "string",
    "experience_level": "string",
    "skills": {
        "skill_name": integer
    },
    "candidate_name": "string (optional)",
    "resume_text": "string"
}
```

Response:
```json
{
    "interview_id": "uuid",
    "question": "string",
    "conversation_context": "string",
    "current_skill": "string",
    "interviewer_intro": "string",
    "interview_progress": "string"
}
```

Notes:
- The `interview_id` is deterministically generated from the resume content and candidate information
- If an interview session already exists for the same resume, a 400 error will be returned

### 2. Continue Interview
**POST** `/interview/continue`

Continues an ongoing interview by processing the candidate's answer and generating the next question.

Request Body:
```json
{
    "interview_id": "uuid",
    "role": "string",
    "experience_level": "string",
    "skills": {
        "skill_name": integer
    },
    "conversation_history": [
        {
            "question": "string",
            "answer": "string",
            "skill": "string"
        }
    ],
    "candidate_name": "string (optional)"
}
```

Response:
```json
{
    "interview_id": "uuid",
    "question": "string",
    "conversation_context": "string",
    "current_skill": "string",
    "interview_progress": "string"
}
```

### 3. Get Interview Status
**GET** `/interview/{interview_id}/status`

Retrieves the current status of an interview session.

Response:
```json
{
    "interview_id": "uuid",
    "role": "string",
    "candidate_name": "string",
    "start_time": "string (ISO format)",
    "last_activity": "string (ISO format)",
    "question_count": integer
}
```

### 4. Get Interview Plan
**GET** `/interview/plan`

Retrieves a structured interview plan based on the role and required skills.

Query Parameters:
- role: string
- skills: Dictionary[string, integer]

### 5. Health Check
**GET** `/health`

Simple health check endpoint to verify API status.

Response:
```json
{
    "status": "string",
    "active_interviews": integer
}
```

## Error Responses

The API may return the following error status codes:

- 400: Bad Request - Invalid input data or duplicate interview session
- 404: Not Found - Interview ID not found
- 500: Internal Server Error - Server-side error

Each error response includes a detail message explaining the error.

## Interview ID Generation

The interview ID is generated deterministically based on:
- Resume content
- Candidate name (if provided)
- Timestamp

This ensures:
- Consistent identification throughout the interview process
- Prevention of duplicate sessions for the same resume
- Unique identification even for candidates with similar resumes