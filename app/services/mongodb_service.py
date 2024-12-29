from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId, json_util
from datetime import datetime
from typing import Dict, Optional, List, Any
from uuid import UUID, uuid4
import asyncio
import json

class MongoDBService:
    _instance = None
    _initialized = False
    client = None
    db = None
    ai_interviews = None  # We'll use only this collection

    def __new__(cls, mongo_uri: str = None):
        if cls._instance is None:
            cls._instance = super(MongoDBService, cls).__new__(cls)
        return cls._instance

    async def check_connection(self) -> bool:
        """Check if MongoDB connection is alive"""
        try:
            if not self.client:
                return False
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            print(f"MongoDB connection check failed: {e}")
            return False

    async def initialize(self, mongo_uri: str):
        """Initialize MongoDB connection"""
        if not self._initialized:
            try:
                if self.client:
                    self.client.close()
                
                self.client = AsyncIOMotorClient(mongo_uri)
                self.db = self.client.test  # Using the 'test' database
                
                # Use only ai_interviews collection for all data
                self.ai_interviews = self.db.ai_interviews
                
                # Create index for better query performance
                await self.ai_interviews.create_index([
                    ("interview_id", 1),
                    ("timestamp", -1)
                ])
                
                await self.client.admin.command('ping')
                print("Successfully connected to MongoDB Test Database")
                self._initialized = True
            except Exception as e:
                print(f"Failed to connect to MongoDB: {e}")
                self._initialized = False
                raise

    async def create_interview(self, interview_data: Dict[str, Any]) -> str:
        """Create a new AI interview session"""
        interview_id = str(uuid4())
        
        print(f"[DEBUG] Creating new interview with data: {json.dumps(interview_data, default=str)}")
        
        # Initialize the interview document
        interview = {
            "interview_id": interview_id,
            "timestamp": datetime.utcnow(),
            "role": interview_data["role"],
            "experience_level": interview_data["experience_level"],
            "candidate_name": interview_data.get("candidate_name", "Anonymous"),
            "skills": interview_data.get("skills", {}),
            "status": "in_progress",
            "conversation_history": [],  # Will be populated with first question later
            "technical_assessment": {},
            "interview_type": "ai_technical",
            "metadata": {
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow()
            }
        }
        
        try:
            print(f"[DEBUG] Inserting new interview document")
            await self.ai_interviews.insert_one(interview)
            print(f"[DEBUG] Successfully created interview with ID: {interview_id}")
            return interview_id
        except Exception as e:
            print(f"[ERROR] Failed to create interview: {str(e)}")
            raise ValueError(f"Failed to create interview: {str(e)}")

    async def initialize_conversation(self, interview_id: str, first_question: Dict[str, Any]):
        """Initialize conversation history with first question"""
        print(f"[DEBUG] Initializing conversation history - id: {interview_id}")
        print(f"[DEBUG] First question data: {json.dumps(first_question, default=str)}")
        
        try:
            # Add first question to conversation history
            update_data = {
                "$set": {
                    "conversation_history": [{
                        "question": first_question["question"],
                        "answer": "",
                        "skill_assessed": first_question.get("skill_assessed", "general"),
                        "technical_depth": first_question.get("technical_depth", "basic"),
                        "timestamp": datetime.utcnow()
                    }],
                    "metadata.last_updated": datetime.utcnow()
                }
            }
            
            await self.ai_interviews.update_one(
                {"interview_id": interview_id},
                update_data
            )
            print(f"[DEBUG] Successfully initialized conversation history")
        except Exception as e:
            print(f"[ERROR] Failed to initialize conversation: {str(e)}")
            raise

    async def update_interview(self, interview_id: str, interaction: Dict[str, Any]):
        """Update interview with new interaction"""
        print(f"[DEBUG] Updating interview - id: {interview_id}")
        print(f"[DEBUG] Update data: {json.dumps(interaction, default=str)}")
        
        update_data = {
            "$push": {
                "conversation_history": {
                    "question": interaction["question"],
                    "answer": interaction.get("answer", ""),
                    "skill_assessed": interaction.get("skill_assessed", "general"),
                    "technical_depth": interaction.get("technical_depth", "basic"),
                    "timestamp": datetime.utcnow()
                }
            },
            "$set": {
                "metadata.last_updated": datetime.utcnow()
            }
        }
        
        try:
            await self.ai_interviews.update_one(
                {"interview_id": interview_id},
                update_data
            )
            print(f"[DEBUG] Interview updated successfully")
        except Exception as e:
            print(f"[ERROR] Failed to update interview in MongoDB: {str(e)}")
            raise

    async def get_interview_history(self, interview_id: str | UUID) -> Dict[str, Any]:
        """Get complete interview data"""
        # Convert UUID to string if needed
        interview_id_str = str(interview_id)
        print(f"[DEBUG] Fetching interview history - id: {interview_id_str}")
        
        try:
            interview = await self.ai_interviews.find_one({"interview_id": interview_id_str})
            if not interview:
                print(f"[ERROR] Interview not found in MongoDB: {interview_id_str}")
                return None
                
            print(f"[DEBUG] Raw interview data: {json.dumps(interview, default=str)}")
            
            # Convert MongoDB ObjectId to string for JSON serialization
            if "_id" in interview:
                interview["_id"] = str(interview["_id"])
                
            # Convert datetime objects to ISO format strings
            if "metadata" in interview:
                if "created_at" in interview["metadata"]:
                    interview["metadata"]["created_at"] = interview["metadata"]["created_at"].isoformat()
                if "last_updated" in interview["metadata"]:
                    interview["metadata"]["last_updated"] = interview["metadata"]["last_updated"].isoformat()
                    
            # Convert timestamps in conversation history
            if "conversation_history" in interview:
                print(f"[DEBUG] Conversation history entries: {len(interview['conversation_history'])}")
                for qa in interview["conversation_history"]:
                    if "timestamp" in qa:
                        qa["timestamp"] = qa["timestamp"].isoformat()
                        
            # Extract resume data if available
            resume_text = interview.get("resume_text", "")
            technical_skills = interview.get("technical_skills", [])
            
            # Determine role from either direct field or technical skills
            role = interview.get("role")
            if not role and technical_skills:
                # Default to most relevant technical role if not specified
                if "Machine Learning" in technical_skills:
                    role = "machine learning engineer"
                elif "Python" in technical_skills:
                    role = "python developer"
                else:
                    role = "software engineer"
                print(f"[DEBUG] Inferred role from skills: {role}")
            
            formatted_data = {
                "interview_id": interview["interview_id"],
                "role": role or "software engineer",  # Fallback role
                "experience_level": interview.get("experience_level", "junior"),  # Fallback level
                "candidate_name": interview.get("candidate_name", "Anonymous Candidate"),
                "status": interview.get("status", "in_progress"),
                "conversation_history": interview.get("conversation_history", []),
                "technical_assessment": interview.get("technical_assessment", {}),
                "metadata": interview.get("metadata", {
                    "created_at": datetime.utcnow().isoformat(),
                    "last_updated": datetime.utcnow().isoformat()
                }),
                "skills": interview.get("skills", {})
            }
            print(f"[DEBUG] Returning formatted interview data: {json.dumps(formatted_data, default=str)}")
            return formatted_data
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch interview history: {str(e)}")
            raise

    async def list_interviews(self, limit: int = 10) -> List[Dict]:
        """List recent AI interviews"""
        cursor = self.ai_interviews.find({}).sort("metadata.created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def update_technical_assessment(self, interview_id: str, assessment: Dict[str, Any]):
        """Update technical assessment for an interview"""
        await self.ai_interviews.update_one(
            {"interview_id": interview_id},
            {
                "$set": {
                    "technical_assessment": assessment,
                    "metadata.last_updated": datetime.utcnow()
                }
            }
        )

    async def store_resume_data(self, interview_id: UUID, data: Dict[str, Any]):
        """Store all interview-related data in ai_interviews collection"""
        try:
            # Validate and get candidate name
            candidate_name = data.get("candidate_name", "").strip()
            if not candidate_name:
                raise ValueError("Candidate name is required")

            # Create interview document
            interview_data = {
                "interview_id": str(interview_id),
                "resume_text": data.get("resume_text", ""),
                "technical_skills": data.get("technical_skills", []),
                "candidate_name": candidate_name,  # Store the validated name
                "timestamp": datetime.utcnow(),
                "status": "initialized",
                "skills": {},
                "conversation_history": [],
                "technical_assessment": {},
                "metadata": {
                    "created_at": datetime.utcnow(),
                    "last_updated": datetime.utcnow()
                }
            }
            
            print(f"[DEBUG] Storing resume data for candidate: {candidate_name}")
            
            # Check if interview already exists and update it
            existing = await self.ai_interviews.find_one({"interview_id": str(interview_id)})
            if existing:
                await self.ai_interviews.update_one(
                    {"interview_id": str(interview_id)},
                    {"$set": {
                        **interview_data,
                        "metadata.last_updated": datetime.utcnow()
                    }}
                )
            else:
                await self.ai_interviews.insert_one(interview_data)
            
            return str(interview_id)
            
        except Exception as e:
            print(f"[ERROR] Failed to store resume data: {str(e)}")
            raise

    async def update_interview_session_skills(self, interview_id: str, skills: Dict[str, float]):
        """Update skills ratings in the interview document"""
        try:
            print(f"[DEBUG] Updating skills for interview {interview_id}: {skills}")
            await self.ai_interviews.update_one(
                {"interview_id": interview_id},
                {
                    "$set": {
                        "skills": skills,
                        "metadata.last_updated": datetime.utcnow()
                    }
                }
            )
            print(f"[DEBUG] Skills updated successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to update skills: {str(e)}")
            raise

    async def update_interview_details(self, interview_id: str, data: Dict[str, Any]):
        """Update interview details in the same document"""
        try:
            # Keep the status from the data if provided, otherwise use 'active'
            status = data.pop("status", "active") if isinstance(data, dict) else "active"
            
            # Ensure candidate name is preserved if it exists
            existing_doc = await self.ai_interviews.find_one({"interview_id": str(interview_id)})
            if existing_doc and existing_doc.get("candidate_name"):
                data["candidate_name"] = existing_doc["candidate_name"]
            
            await self.ai_interviews.update_one(
                {"interview_id": str(interview_id)},
                {
                    "$set": {
                        **data,
                        "status": status,  # Use the status from data or default to 'active'
                        "metadata.last_updated": datetime.utcnow()
                    }
                }
            )
            print(f"Updated interview {interview_id} status to: {status}")  # Debug log
        except Exception as e:
            print(f"[ERROR] Failed to update interview details: {str(e)}")
            raise

    async def store_analysis(self, interview_id: str, analysis_data: Dict[str, Any]):
        """Store analysis in the interview document"""
        try:
            print(f"[DEBUG] Storing analysis for interview {interview_id}")
            await self.ai_interviews.update_one(
                {"interview_id": str(interview_id)},
                {
                    "$set": {
                        "technical_assessment": analysis_data,
                        "status": "analyzed",
                        "metadata.last_updated": datetime.utcnow()
                    }
                }
            )
            print(f"[DEBUG] Successfully stored analysis")
        except Exception as e:
            print(f"[ERROR] Failed to store analysis: {str(e)}")
            raise

    async def store_pdf_report(self, interview_id: str, pdf_data: bytes):
        """Store PDF report in the same interview document"""
        try:
            await self.ai_interviews.update_one(
                {"interview_id": str(interview_id)},
                {
                    "$set": {
                        "pdf_report": pdf_data,
                        "metadata.last_updated": datetime.utcnow(),
                        "status": "report_generated"
                    }
                }
            )
        except Exception as e:
            print(f"[ERROR] Failed to store PDF report: {str(e)}")
            raise

    async def get_interview_session(self, interview_id: str) -> Dict[str, Any]:
        """Get interview session data"""
        try:
            session = await self.ai_interviews.find_one({"interview_id": str(interview_id)})
            if not session:
                print(f"[DEBUG] Interview session not found: {interview_id}")
                return None
                
            print(f"[DEBUG] Found session with candidate: {session.get('candidate_name')}")
            return session
        except Exception as e:
            print(f"[ERROR] Failed to get interview session: {str(e)}")
            raise

    async def update_last_answer(self, interview_id: str, answer: str):
        """Update the last answer in the conversation history"""
        try:
            # First get the current conversation history
            interview = await self.ai_interviews.find_one(
                {"interview_id": interview_id}
            )
            if not interview or "conversation_history" not in interview:
                raise ValueError("No conversation history found")

            # Update the last answer
            conversation_history = interview["conversation_history"]
            if not conversation_history:
                raise ValueError("Empty conversation history")

            # Update the last entry with the answer
            await self.ai_interviews.update_one(
                {"interview_id": interview_id},
                {
                    "$set": {
                        "conversation_history.$[last].answer": answer,
                        "metadata.last_updated": datetime.utcnow()
                    }
                },
                array_filters=[{"last.answer": ""}]
            )
        except Exception as e:
            print(f"[ERROR] Failed to update last answer: {str(e)}")
            raise

    async def add_to_history(self, interview_id: str, interaction: Dict[str, Any]):
        """Add a new interaction to the conversation history"""
        try:
            # Validate the interaction has required fields
            if "question" not in interaction:
                raise ValueError("Interaction must include a question")

            # Add timestamp if not present
            if "timestamp" not in interaction:
                interaction["timestamp"] = datetime.utcnow()

            # Add the new interaction to history
            await self.ai_interviews.update_one(
                {"interview_id": interview_id},
                {
                    "$push": {
                        "conversation_history": interaction
                    },
                    "$set": {
                        "metadata.last_updated": datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            print(f"[ERROR] Failed to add to history: {str(e)}")
            raise

    async def update_interview_session(self, interview_id: str, conversation_history: List[Dict[str, Any]] = None) -> bool:
        """Update interview session with new conversation history"""
        try:
            print(f"Updating interview session {interview_id}")
            
            # First verify the document exists
            session = await self.ai_interviews.find_one({"interview_id": str(interview_id)})
            if not session:
                print(f"[ERROR] Session not found for ID: {interview_id}")
                return False
            
            update_data = {
                "metadata.last_updated": datetime.utcnow()
            }
            
            if conversation_history is not None:
                update_data["conversation_history"] = conversation_history
                print(f"Updating conversation history with {len(conversation_history)} entries")
            
            result = await self.ai_interviews.update_one(
                {"interview_id": str(interview_id)},
                {
                    "$set": update_data,
                    "$setOnInsert": {  # In case document doesn't exist
                        "status": "active",
                        "metadata.created_at": datetime.utcnow()
                    }
                },
                upsert=True  # Create if doesn't exist
            )
            
            # Consider both matched and upserted as success
            success = result.matched_count > 0 or result.upserted_id is not None
            print(f"Update {'successful' if success else 'failed'}")
            print(f"Matched count: {result.matched_count}, Modified count: {result.modified_count}, Upserted ID: {result.upserted_id}")
            return success
            
        except Exception as e:
            print(f"[ERROR] Failed to update interview session: {str(e)}")
            return False

    async def validate_candidate_name(self, interview_id: str) -> str:
        """Always return a default name for report generation"""
        return "Candidate"  # Simple default name
  