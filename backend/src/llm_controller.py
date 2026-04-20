"""
LLM Controller - GPT with Vector Memory
"""

import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from typing import List, Dict
from src.vector_memory import VectorMemory

load_dotenv()

class LLMController:
    def __init__(self, session_id: str = "default_user", max_memory_messages: int = 20):
        """Initialize OpenAI client with vector memory"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ OPENAI_API_KEY not found in .env file")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"
        
        # Vector memory
        self.vector_memory = VectorMemory(session_id=session_id)
        self.session_id = session_id
        self.max_memory_messages = max_memory_messages
        
        # Local cache for recent messages
        self.recent_messages: List[Dict] = []
        
        print("✅ LLM Controller initialized with Vector Memory")
        print(f"   Session: {session_id}")
    
    def process_user_message(self, user_message: str) -> dict:
        """Process user message with vector memory context"""
        
        now = datetime.now()
        current_date = now.strftime("%A, %B %d, %Y")
        
        relevant_memories = self.vector_memory.get_relevant_memories(user_message, top_k=10)
        user_info = self._extract_user_info_from_memories()
        
        system_prompt = f"""You are a helpful AI assistant.

CURRENT DATE: {current_date}

KNOWN USER INFORMATION:
{self._format_user_info(user_info)}

IMPORTANT: When asked for a list, provide the COMPLETE list in your response. Be thorough and complete."""

        print("\n" + "="*50)
        print(f"📝 USER MESSAGE: {user_message}")
        print("="*50)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            output = response.choices[0].message.content
            
            # DETAILED DEBUG PRINTS
            print(f"📏 RAW RESPONSE LENGTH: {len(output)} characters")
            print(f"📊 TOKENS USED: {response.usage.total_tokens} (prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens})")
            print("-"*50)
            print("🤖 RAW GPT OUTPUT:")
            print(output)
            print("-"*50)
            print("="*50 + "\n")
            
            # Parse the response
            result = self._parse_gpt_output(output)
            
            print(f"📦 FINAL RESPONSE (first 200 chars): {result['response'][:200]}..." if len(result['response']) > 200 else f"📦 FINAL RESPONSE: {result['response']}")
            print(f"😊 EMOTION: {result['emotion']}, INTENSITY: {result['intensity']}")
            
            # Store in vector memory
            self.vector_memory.add_memory(
                user_message=user_message,
                assistant_response=result["response"],
                emotion=result["emotion"]
            )
            
            # Keep local cache
            self._add_to_recent(user_message, result)
            
            result["user_message"] = user_message
            return result
            
        except Exception as e:
            print(f"❌ OpenAI Error: {e}")
            return {
                "emotion": "neutral",
                "intensity": 5,
                "response": "I'm here to help. Could you please repeat that?",
                "user_message": user_message
            }
    
    def _extract_user_info_from_memories(self) -> Dict:
        """Extract user info by searching through all memories"""
        info_queries = {
            "name": ["my name is", "call me", "i am", "i'm"],
            "favorite": ["favorite", "love", "like"],
            "location": ["i live in", "i'm from", "my city", "place in"]
        }
        
        user_info = {}
        
        for info_type, queries in info_queries.items():
            for query in queries:
                memories = self.vector_memory.search_all_memories(query)
                for mem in memories:
                    user_text = mem["user"].lower()
                    
                    if info_type == "name":
                        patterns = [
                            r'(?:my name is|call me|i am|i\'m)\s+(\w+)',
                            r'name is (\w+)'
                        ]
                        for pattern in patterns:
                            match = re.search(pattern, user_text, re.IGNORECASE)
                            if match:
                                name = match.group(1).capitalize()
                                if name not in ["hi", "hello", "hey", "ok", "yes", "no"]:
                                    user_info["name"] = name
                                    break
                    
                    elif info_type == "location":
                        match = re.search(r'(?:i live in|i\'m from|my city is)\s+(\w+(?:\s+\w+)?)', user_text, re.IGNORECASE)
                        if match:
                            user_info["location"] = match.group(1).capitalize()
                            break
                    
                    elif info_type == "favorite":
                        if "favorite" in user_text or "love" in user_text:
                            user_info["has_favorites"] = True
        
        return user_info
    
    def _format_memories(self, memories: List[Dict]) -> str:
        """Format memories for system prompt"""
        if not memories:
            return "No relevant past conversations."
        
        lines = ["Here are relevant things the user has told you before:"]
        for i, mem in enumerate(memories[:5], 1):
            lines.append(f"{i}. User said: \"{mem['user']}\"")
            lines.append(f"   You replied: \"{mem['assistant']}\"")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_user_info(self, user_info: Dict) -> str:
        """Format user info for prompt"""
        if not user_info:
            return "No personal information known yet."
        
        lines = []
        for key, value in user_info.items():
            if key == "has_favorites":
                lines.append(f"- User has mentioned favorite things")
            else:
                lines.append(f"- User's {key}: {value}")
        
        return "\n".join(lines) if lines else "No personal information known yet."
    
    def _add_to_recent(self, user_message: str, result: dict):
        """Add to recent messages cache"""
        self.recent_messages.append({
            "user": user_message,
            "assistant": result["response"],
            "emotion": result["emotion"]
        })
        
        if len(self.recent_messages) > self.max_memory_messages:
            self.recent_messages = self.recent_messages[-self.max_memory_messages:]
    
    def _parse_gpt_output(self, output: str) -> dict:
        """Parse GPT's structured output"""
        result = {
            "emotion": "neutral",
            "intensity": 5,
            "response": ""
        }
        
        print(f"🔍 PARSING OUTPUT (first 300 chars): {output[:300]}...")
        
        # Extract EMOTION
        emotion_match = re.search(r'EMOTION:\s*(\w+)', output, re.IGNORECASE)
        if emotion_match:
            result["emotion"] = emotion_match.group(1).lower()
            print(f"   Found emotion: {result['emotion']}")
        
        # Extract INTENSITY
        intensity_match = re.search(r'INTENSITY:\s*(\d+)', output)
        if intensity_match:
            result["intensity"] = int(intensity_match.group(1))
            print(f"   Found intensity: {result['intensity']}")
        
        # Extract RESPONSE
        response_match = re.search(r'RESPONSE:\s*(.+?)(?=\n\w+:|$)', output, re.DOTALL)
        if response_match:
            result["response"] = response_match.group(1).strip()
            print(f"   Extracted response length: {len(result['response'])} chars")
        else:
            # If no RESPONSE tag, use the whole output
            result["response"] = output.strip()
            print(f"   No RESPONSE tag found, using full output ({len(result['response'])} chars)")
        
        # Clean up
        result["response"] = re.sub(r'\[.*?\]', '', result["response"]).strip()
        
        return result
    
    def clear_memory(self):
        """Clear all memories"""
        self.vector_memory.clear_memory()
        self.recent_messages = []
        print("🧹 All memories cleared")
    
    def get_memory_summary(self) -> dict:
        """Get memory summary"""
        stats = self.vector_memory.get_memory_stats()
        return {
            "total_memories": stats["total_vectors"],
            "session_id": stats["session_id"],
            "user_info": self._extract_user_info_from_memories()
        }