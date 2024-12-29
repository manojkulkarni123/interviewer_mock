import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import json
import requests
from time import sleep
from app.schemas.models import QuestionAnswer
import re
import aiohttp
import asyncio

load_dotenv()

class GroqService:
    """
    Service class for handling interactions with the Groq LLM API.
    Manages technical interviews by generating context-aware questions and analyzing responses.
    """
    
    def __init__(self):
        """
        Initialize the GroqService with API configuration and settings.
        Sets up API key, endpoints, and retry parameters.
        Raises ValueError if GROQ_API_KEY is not set.
        """
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.model = "mixtral-8x7b-32768"
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.interview_state = None  # Add this to track interview state

    async def initialize_interview(self, role: str, experience_level: str = "mid", skills: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Initialize a new interview with required parameters.
        
        Args:
            role: The position being interviewed for (e.g., "Machine Learning Engineer")
            experience_level: The expected level ("junior", "mid", "senior")
            skills: Dictionary of skills and their importance ratings (0-10)
            
        Returns:
            Dictionary containing the initialized interview state
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not role:
            raise ValueError("Role must be specified for the interview")
            
        # Default skills if none provided
        if skills is None:
            skills = self._get_default_skills_for_role(role)
            
        # Initialize interview state
        self.interview_state = {
            "role": role,
            "experience_level": experience_level,
            "skills": skills,
            "conversation_history": [],
            "covered_skills": set(),
            "current_skill": None
        }
        
        return self.interview_state
        
    
        
     

    async def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0, max_tokens: int = 1000) -> str:
        """
        Makes async API calls to Groq with built-in retry logic.
        
        Args:
            messages: List of message dictionaries for the conversation
            temperature: Controls randomness in response (0-1)
            max_tokens: Maximum length of generated response
            
        Returns:
            Generated response text from the API
            
        Raises:
            ValueError: If API calls fail after max retries
        """
        for attempt in range(self.max_retries):
            try:
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        headers=self.headers,
                        json=data,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            response_json = await response.json()
                            return response_json["choices"][0]["message"]["content"]
                        
                        if response.status == 429 and attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                            
                        response.raise_for_status()
                        
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise ValueError(f"Failed to get response from Groq: {str(e)}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))

    def _format_history(self, history: List[QuestionAnswer]) -> str:
        """
        Formats the complete conversation history into a readable string format.
        Handles both dictionary and QuestionAnswer objects.
        """
        if not history:
            return ""
        
        formatted_history = []
        for qa in history:
            # Handle both dictionary and QuestionAnswer objects
            if isinstance(qa, dict):
                question = qa.get('question', '')
                answer = qa.get('answer', '')
            else:
                question = getattr(qa, 'question', '')
                answer = getattr(qa, 'answer', '')
            
            if question and answer:
                formatted_history.append(f"Q: {question}\nA: {answer}")
        
        return "\n\n".join(formatted_history)

    def _analyze_interview_context(self, interview_data: Dict[str, Any], conversation_history: List[QuestionAnswer]) -> Dict[str, Any]:
        """
        Analyzes interview context for intelligent question generation.
        Takes into account both skills and their ratings.
        """
        # Extract valid skills with ratings
        valid_skills = {
            skill: {
                'rating': rating,
                'depth_level': 'advanced' if rating >= 8 else 'intermediate' if rating >= 5 else 'basic'
            }
            for skill, rating in interview_data.get('skills', {}).items() if rating > 0
        }
        
        # Initialize context
        context = {
            "role": interview_data.get('role', ''),
            "experience_level": interview_data.get('experience_level', ''),
            "rated_skills": valid_skills,
            "covered_skills": set(),
            "previous_questions": set(),
            "skill_responses": {},
            "current_topics": []
        }

        if conversation_history:
            for qa in conversation_history:
                # Handle both dictionary and QuestionAnswer objects
                if isinstance(qa, dict):
                    question = qa.get('question', '')
                    answer = qa.get('answer', '')
                    current_skill = qa.get('current_skill', '')
                else:
                    question = getattr(qa, 'question', '')
                    answer = getattr(qa, 'answer', '')
                    current_skill = getattr(qa, 'current_skill', '')

                # Track questions to avoid repetition
                if question:
                    context["previous_questions"].add(question)
                
                # Track skills coverage and responses
                if current_skill:
                    context["covered_skills"].add(current_skill)
                    
                    # Track responses per skill
                    if current_skill not in context["skill_responses"]:
                        context["skill_responses"][current_skill] = []
                    if answer:
                        context["skill_responses"][current_skill].append(answer)
                    
                    # Track topic progression
                    if not context["current_topics"] or context["current_topics"][-1] != current_skill:
                        context["current_topics"].append(current_skill)

        return context

    def _create_interview_system_prompt(self, interview_state: Dict[str, Any], is_start: bool) -> str:
        """Create a natural but technically rigorous interview experience"""
        
        # Format skills with their ratings and coverage
        skills_context = []
        for skill, rating in interview_state.get('skills', {}).items():
            covered = skill in interview_state.get('covered_skills', set())
            depth = 'Advanced' if rating >= 8 else 'Intermediate' if rating >= 5 else 'Basic'
            status = 'Covered' if covered else 'Not yet covered'
            skills_context.append(f"- {skill}: Rating {rating}/10 (Focus: {depth}) - {status}")
        
        skills_summary = "\n".join(skills_context)

        # Analyze current interview progress
        conversation_history = interview_state.get('conversation_history', [])
        current_skill = interview_state.get('current_skill', 'Not specified')
        covered_skills = interview_state.get('covered_skills', set())
        experience_level = interview_state.get('experience_level', 'mid')
        
        # Create progress summary
        progress_summary = f"""
INTERVIEW FOCUS:
- Role: {interview_state['role']}
- Experience Level: {experience_level}
- Skills covered so far: {', '.join(covered_skills) if covered_skills else 'None yet'}
- Current focus area: {current_skill}
- Questions asked: {len(conversation_history)}
- Interview phase: {'Starting' if is_start else 'In progress'}"""

        # Add introduction section for the start of the interview
        introduction = """
INTRODUCTION (Only for first interaction):
- Start with a warm, professional greeting
- Briefly introduce yourself as the technical interviewer
- Explain the interview format and expectations
- Example: "Hi! I'm your technical interviewer today. We'll be discussing your experience as a [role], focusing on the skills you've listed. I'll ask technical questions and may dive deeper into specific areas. Feel free to ask clarifying questions at any point. Shall we begin?"
"""

        # Create prioritized skills list
        uncovered_skills = [
            (skill, rating) for skill, rating in interview_state.get('skills', {}).items()
            if skill not in interview_state.get('covered_skills', set())
        ]
        uncovered_skills.sort(key=lambda x: x[1], reverse=True)
        prioritized_skills = "\n".join([
            f"- {skill}: Priority {rating}/10"
            for skill, rating in uncovered_skills
        ])

        return f"""You are an experienced engineer having an in-depth technical discussion with a peer about their experience in {interview_state['role']}. 

INTERVIEW DYNAMICS:
1. Question Strategy
   - Start broad to identify areas of strength
   - Follow interesting technical threads naturally
   - Avoid repeating similar questions about the same concept
   - Let their answers guide the technical depth

2. Response Analysis
   - Listen for unique insights or approaches
   - Note when they bring up interesting trade-offs
   - Pick up on technical details they emphasize
   - Follow their technical reasoning

3. Natural Transitions
   When switching topics:
   - Reference something from their previous answers
   - Connect it to the new topic naturally
   - Acknowledge their request to switch smoothly
   Example flow: "You mentioned [previous point] earlier. That's interesting because it relates to [new topic]..."

4. Technical Deep Dives
   - When they show expertise:
     * Explore their decision-making process
     * Discuss trade-offs they considered
     * Challenge their assumptions professionally
   - When they struggle:
     * Note it and move on naturally
     * Switch to their areas of strength
     * Don't repeat similar questions

5. Conversation Balance
   - Mix technical depth with natural flow
   - Show interest in their unique approaches
   - Challenge them while keeping it collaborative
   - Let them expand on interesting points they raise

Remember:
- Each question should feel like a natural progression
- Don't get stuck in repetitive patterns or phrases 
- Follow interesting technical threads
- Keep it challenging but conversational
- Let their expertise guide the discussion
- do not repeat the same structure of responses 

SKILL CONTEXT:
{skills_summary}

{progress_summary}

Remember: 
- Be direct but professional when answers lack depth
- Don't praise superficial or vague responses
- Match follow-up difficulty to their claimed expertise level
- Show appropriate concern when core skills are weak

You must respond with a valid JSON object containing: 
{{
    "acknowledgment": "Your brief acknowledgment of their previous response",
    "question": "Your next interview question here",
    "current_skill": "One of the candidate's listed skills being assessed",
    "thought_process": {{
        "response_analysis": "Honest assessment of answer quality",
        "knowledge_assessment": "Clear evaluation of demonstrated expertise",
        "topic_decision": "Why continue or switch topics based on answer quality",
        "approach": "How to address any concerns while maintaining professionalism"
    }},
    "skill_coverage": {{
        "current_skill": "Skill being assessed",
        "covered_skills": ["List of skills covered so far"],
        "weak_areas": ["Skills where candidate showed weakness"],
        "next_priorities": ["Skills to prioritize next"]
    }},
    "difficulty": "basic|intermediate|advanced (matching their level)",
    "context": "Optional context for the question",
    "follow_ups": ["Potential follow-up points within their skills"]
}}"""

    def _validate_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Validate and structure the LLM response"""
        try:
            # Parse JSON response
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"JSON Parse Error: {str(e)}\nResponse text: {response_text}")
                return self._create_fallback_response("Failed to parse LLM response as JSON")

            # Ensure response_data is a dictionary
            if not isinstance(response_data, dict):
                print(f"Invalid response type: {type(response_data)}")
                return self._create_fallback_response("LLM response is not a dictionary")

            # Required fields with default values
            default_thought_process = {
                "response_analysis": "Analyzing response",
                "knowledge_assessment": "Evaluating knowledge",
                "topic_decision": "Maintaining current topic",
                "approach": "Using structured approach"
            }

            # Ensure thought_process exists and is a dictionary
            if "thought_process" not in response_data or not isinstance(response_data["thought_process"], dict):
                response_data["thought_process"] = default_thought_process
            else:
                # Ensure all required thought_process fields exist
                for key, value in default_thought_process.items():
                    if key not in response_data["thought_process"]:
                        response_data["thought_process"][key] = value

            # Check and set required string fields
            required_string_fields = {
                "question": "Could you elaborate on your previous answer?",
                "current_skill": "general",
                "difficulty": "intermediate",
                "context": "",
                "transition_notes": "",
                "introduction": ""
            }

            for field, default_value in required_string_fields.items():
                if field not in response_data or not isinstance(response_data.get(field), str):
                    response_data[field] = default_value

            # Ensure follow_ups exists and is a list
            if "follow_ups" not in response_data or not isinstance(response_data["follow_ups"], list):
                response_data["follow_ups"] = ["Could you provide more details?", "Can you give an example?"]

            # Add introduction field for first interaction
            if "introduction" not in response_data:
                response_data["introduction"] = "" if not is_start else "Hi! I'm your technical interviewer today..."

            # Add topic switching validation
            if "topic_decision" in response_data.get("thought_process", {}):
                topic_decision = response_data["thought_process"]["topic_decision"].lower()
                
                # Force topic switch if:
                # 1. Candidate explicitly asks to switch
                # 2. Candidate shows lack of knowledge
                # 3. Multiple vague answers about same topic
                if ("switch" in topic_decision or 
                    "move on" in topic_decision or 
                    "lack of knowledge" in topic_decision or 
                    "weak understanding" in topic_decision):
                    
                    # Ensure we're actually switching to a different skill
                    current_skill = response_data.get("current_skill")
                    if current_skill == response_data.get("previous_skill"):
                        raise ValueError("Must switch to a different skill after detecting weakness")

            return response_data

        except Exception as e:
            print(f"Validation Error: {str(e)}\nResponse text: {response_text}")
            return self._create_fallback_response(f"Error validating response: {str(e)}")

    def _create_fallback_response(self, error_msg: str) -> Dict[str, Any]:
        """Create a safe fallback response when LLM fails"""
        return {
            "interview_id": "",  # Will be filled by the API
            "question": "Could you tell me more about your experience with this technology?",
            "current_skill": "general",
            "conversation_context": "Technical Interview",
            "acknowledgment": "I understand.",
            "thought_process": {
                "response_analysis": "Fallback due to error",
                "knowledge_assessment": "Continuing general assessment",
                "topic_decision": "Maintaining current topic",
                "approach": "Using safe fallback question"
            },
            "difficulty": "intermediate",
            "introduction": ""
        }

    async def get_interview_response(self, state: dict) -> dict:
        """Generate interview responses with proper error handling"""
        try:
            if state.get("is_start"):
                # Generate personalized introduction
                system_prompt = """You are an AI technical interviewer. Keep the introduction brief and professional.
                NO pleasantries or excessive politeness. Be direct and clear.
                The introduction should ONLY:
                1. State candidate's name
                2. State the role
                3. Ask them about themselves and interest in the role
                Keep it concise and straightforward."""
                
                user_prompt = f"""Create a brief introduction for:
                Candidate Name: {state['candidate_name']}
                Role: {state['role']}
                Experience Level: {state['experience_level']}"""
                
            else:
                # Regular interview question generation
                system_prompt = """You are an AI technical interviewer. Based on the conversation history and candidate's skills,
                generate the next relevant technical question. Questions should:
                1. Be clear and specific
                2. Focus on practical applications
                3. Allow candidates to demonstrate their knowledge
                4. Follow a logical progression from previous questions
                Keep the tone professional but conversational."""
                
                user_prompt = f"""Generate the next interview question based on:
                Role: {state['role']}
                Experience Level: {state['experience_level']}
                Skills: {state.get('skills', {})}
                Conversation History: {state.get('conversation_history', [])}"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await self._call_api(messages)
            
            # Format response to match InterviewResponse model
            return {
                "status": "success",
                "data": {
                    "interview_id": state.get("interview_id"),  # Will be converted to UUID by Pydantic
                    "question": response.strip(),
                    "conversation_context": "Technical Interview",
                    "current_skill": "general",
                    "interviewer_intro": response.strip() if state.get("is_start") else None,
                    "interview_progress": "Starting interview" if state.get("is_start") else "In progress"
                }
            }
            
        except Exception as e:
            print(f"Error in get_interview_response: {str(e)}")
            # Return error response that matches InterviewResponse model
            return {
                "status": "error",
                "message": str(e),
                "data": {
                    "interview_id": state.get("interview_id"),  # Will be converted to UUID by Pydantic
                    "question": "I apologize, but I encountered an issue. Could you please try again?",
                    "conversation_context": "Technical Interview",
                    "current_skill": "general",
                    "interviewer_intro": None,
                    "interview_progress": "Error encountered"
                }
            }

    def _format_progress_message(self, thought_process: Dict[str, Any], current_skill: str, transition_notes: Optional[str] = None) -> str:
        """Create a more informative progress message"""
        if transition_notes:
            return f"Transitioning: {transition_notes}"
        
        assessment = thought_process.get("knowledge_assessment", "").lower()
        if "excellent" in assessment or "strong" in assessment:
            return f"Exploring advanced concepts in {current_skill}"
        elif "good" in assessment or "solid" in assessment:
            return f"Building on your knowledge of {current_skill}"
        else:
            return f"Understanding your experience with {current_skill}"

    def _is_similar_question(self, question1: str, question2: str) -> bool:
        """Check if two questions are similar (ignoring case and whitespace)."""
        return question1.lower().strip() == question2.lower().strip()

    def _get_fallback_response(self, interview_data: Dict[str, Any], is_start: bool) -> Dict[str, Any]:
        """Provides a fallback response in case of API errors."""
        if is_start:
            return {
                "status": "success",
                "data": {
                    "question": "Could you tell me about your background and what interests you about this role?",
                    "conversation_context": interview_data.get("conversation_state", {}).get("role", ""),
                    "interviewer_intro": "Hello! I'm your AI interviewer today. I'm looking forward to learning more about your experience and discussing some technical concepts together. Let's start with getting to know you a bit better.",
                    "interview_id": interview_data.get("interview_id", ""),
                    "current_skill": "introduction",
                    "thought_process": {
                        "personalization": "Starting with a warm welcome",
                        "initial_focus": "Understanding candidate's background",
                        "conversation_strategy": "Creating a comfortable atmosphere"
                    }
                }
            }
        
        return {
            "status": "success",
            "data": {
                "question": "Could you tell me more about a specific project where you applied these concepts?",
                "conversation_context": interview_data.get("conversation_state", {}).get("role", ""),
                "current_skill": "general",
                "technical_focus": "project_experience",
                "thought_process": {
                    "response_analysis": "Moving to practical experience",
                    "conversation_direction": "Exploring real-world applications",
                    "technical_evaluation": "Understanding hands-on experience"
                },
                "expected_aspects": ["project_details", "technical_implementation", "problem_solving"]
            }
        }

    async def _get_llm_response(self, prompt: str, temperature: float = 0) -> Dict[str, Any]:
        """
        Gets a response from the LLM and ensures it's properly formatted.
        
        Args:
            prompt: The system prompt to send to the LLM
            temperature: Controls response randomness (0-1)
            
        Returns:
            Parsed JSON response from the LLM
            
        Raises:
            ValueError: If response is not valid JSON or missing required fields
        """
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Generate the next interview response."}
        ]
        
        try:
            response_text = await self._call_api(messages, temperature=temperature)
            response_data = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["question", "current_skill"]
            missing_fields = [field for field in required_fields if field not in response_data]
            
            if missing_fields:
                raise ValueError(f"Missing required fields in LLM response: {missing_fields}")
                
            return response_data
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {str(e)}")
            print(f"Raw response: {response_text}")
            raise ValueError("Invalid JSON response from LLM")
            
        except Exception as e:
            print(f"Error in LLM response: {str(e)}")
            raise

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate LLM response.
        
        Args:
            response_text: Raw response text from LLM
            
        Returns:
            Parsed and validated response dictionary
            
        Raises:
            ValueError: If response is invalid or missing required fields
        """
        try:
            # Parse JSON response
            response_data = json.loads(response_text)
            
            # Ensure we have a valid dictionary
            if not isinstance(response_data, dict):
                raise ValueError("LLM response is not a valid dictionary")
            
            # Check for required fields
            required_fields = ["question", "current_skill", "thought_process"]
            missing_fields = [field for field in required_fields if field not in response_data]
            
            if missing_fields:
                raise ValueError(f"Missing required fields in LLM response: {missing_fields}")
            
            # Ensure thought_process is a dictionary
            if not isinstance(response_data.get("thought_process"), dict):
                response_data["thought_process"] = {
                    "analysis": "Default analysis",
                    "decision": "Moving to next question",
                    "expected_depth": "basic"
                }
            
            # Ensure expected_response_aspects is a list
            if "expected_response_aspects" not in response_data:
                response_data["expected_response_aspects"] = []
            
            return {
                "question": response_data["question"],
                "current_skill": response_data["current_skill"],
                "thought_process": response_data["thought_process"],
                "expected_response_aspects": response_data["expected_response_aspects"]
            }
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {str(e)}")
            print(f"Raw response: {response_text}")
            raise ValueError("Invalid JSON response from LLM")
            
        except Exception as e:
            print(f"Error parsing LLM response: {str(e)}")
            raise ValueError(f"Failed to parse LLM response: {str(e)}")

