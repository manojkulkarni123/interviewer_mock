# AI Technical Interview System

An AI-powered technical interview system that helps conduct and analyze technical interviews.

## Features

- Resume parsing and skill extraction
- Technical interview question generation
- Real-time interview monitoring
- Performance analysis and reporting
- Skill rating and evaluation

## Components

1. Resume Parser API
   - PDF text extraction
   - Technical skill identification
   - Experience analysis

2. Interview System
   - Dynamic question generation
   - Context-aware follow-ups
   - Multi-skill assessment

3. Analysis & Reporting
   - Performance evaluation
   - Skill proficiency rating
   - Detailed interview reports

## Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Access the Swagger UI documentation at:
- http://localhost:8000/docs
- http://localhost:8000/redoc

## Environment Variables

Required environment variables:
- `GROQ_API_KEY`: Your Groq API key
- `MONGODB_URI`: MongoDB connection string

## Project Structure

```
app/
├── __init__.py
├── main.py                 # Main FastAPI application
├── parserapifinal.py       # Resume parsing functionality
├── report_api.py           # Analysis and reporting
├── skillrating.py          # Skill rating system
├── services/              
│   ├── __init__.py
│   ├── groq_service.py    # Groq API integration
│   └── mongodb_service.py  # MongoDB integration
├── schemas/               
│   ├── __init__.py
│   ├── interview.py       # Interview-related schemas
│   └── models.py          # Data models
└── docs/                  
    └── api_docs.md        # Additional API documentation
```

## Dependencies

- FastAPI
- PyPDF2
- Groq API
- MongoDB
- Python 3.8+

## License

MIT License - see LICENSE file for details
