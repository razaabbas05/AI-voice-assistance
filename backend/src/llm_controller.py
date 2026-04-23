"""
LLM Controller - GPT with Vector Memory and Proactive Personality
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
        
        # Track the last question asked (for follow-ups)
        self.last_question_asked = None
        
        # Engagement tracking
        self.conversation_stage = "new"
        self.user_engagement_level = 0
        self.message_count = 0
        
        print("✅ LLM Controller initialized with Vector Memory and Proactive Personality")
        print(f"   Session: {session_id}")
    
    def _analyze_query_type(self, message: str) -> str:
        """Analyze user message to determine response style"""
        message_lower = message.lower()
        
        # Short follow-up responses
        if message_lower.strip() in ['yes', 'no', 'yeah', 'nope', 'sure', 'okay', 'ok', 'yep', 'nah']:
            return "FOLLOWUP"
        
        # List requests - be concise
        if any(word in message_lower for word in ['list', 'top', 'name of', 'names of', 'all the']):
            return "CONCISE_LIST"
        
        # Comparison requests
        if any(word in message_lower for word in ['compare', 'better', 'vs', 'versus', 'who is better']):
            return "COMPARISON"
        
        # Explanation requests
        if any(word in message_lower for word in ['explain', 'how', 'why', 'what is', 'tell me about']):
            return "EXPLANATION"
        
        # Greetings
        if message_lower.strip() in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']:
            return "GREETING"
        
        return "GENERAL"
    
    def _build_recent_context(self) -> str:
        """Build recent conversation context from last 3 exchanges"""
        if len(self.recent_messages) < 2:
            return ""
        
        # Get last 3 exchanges (up to 6 messages)
        recent = self.recent_messages[-6:]
        
        context = "RECENT CONVERSATION (CRITICAL FOR UNDERSTANDING FOLLOW-UPS):\n"
        for msg in recent:
            if "user" in msg:
                context += f"User: {msg['user']}\n"
            else:
                context += f"You: {msg['assistant']}\n"
        context += "\n"
        
        return context
    
    def process_user_message(self, user_message: str) -> dict:
        """Process user message with vector memory context and proactive personality"""
        
        now = datetime.now()
        current_date = now.strftime("%A, %B %d, %Y")
        
        # Track engagement
        self.message_count += 1
        if len(user_message.split()) > 5:
            self.user_engagement_level += 1
        if "?" in user_message:
            self.user_engagement_level += 1
        
        # Analyze query type
        query_type = self._analyze_query_type(user_message)
        
        # Get relevant memories from vector DB
        relevant_memories = self.vector_memory.get_relevant_memories(user_message, top_k=5)
        user_info = self._extract_user_info_from_memories()
        
        # Build recent conversation context (last 3 exchanges)
        recent_context = self._build_recent_context()
        
        # Special handling for follow-up responses
        followup_hint = ""
        if query_type == "FOLLOWUP" and self.last_question_asked:
            followup_hint = f"IMPORTANT: The user is responding to your previous question: '{self.last_question_asked}'. Their '{user_message}' is an answer to THAT question. Respond accordingly."
        
        # Response style based on query type
        if query_type == "CONCISE_LIST":
            style_guide = """
            - Provide ONLY the requested list items (names only, no descriptions)
            - Put each item on a NEW LINE with numbers (1. 2. 3.)
            - After the list, ask ONE brief follow-up: "Want details on any of these?"
            - Keep it SHORT - no extra facts or commentary
            """
        elif query_type == "FOLLOWUP":
            style_guide = """
            - The user is answering your previous question
            - Acknowledge their answer and continue the conversation naturally
            - If they said 'yes', provide what you offered
            - If they said 'no', offer an alternative or move on
            """
        elif query_type == "COMPARISON":
            style_guide = """
            - Give specific stats and a clear verdict
            - Use [excited] or [passionate] tags for enthusiasm
            - Be opinionated but fair
            """
        elif query_type == "GREETING":
            style_guide = """
            - Keep it to 1 short, warm sentence
            - Use [warmly] tag
            - Ask a simple follow-up
            """
        elif query_type == "EXPLANATION":
            style_guide = """
            - Provide 2-4 sentences of clear explanation
            - Use [calmly] or [curious] tags
            - End with an engaging follow-up
            """
        else:
            style_guide = "Be natural and match the user's tone."
        
        system_prompt = f"""You are Maya, a warm, smart AI assistant with excellent judgment and strong conversation memory.

CURRENT DATE: {current_date}

{recent_context}
{followup_hint}

YOUR PERSONALITY:
- You remember what you just talked about and understand follow-ups like 'yes' or 'no'
- You know when to be brief (lists = just names) and when to elaborate (explanations = details)
- You have opinions and share them when asked to compare things
- You use the FULL range of ElevenLabs V3 tags naturally

ELEVENLABS V3 TAGS YOU CAN USE:
- [excited] - for enthusiasm, good news, sports
- [whispers] - for secrets, intimate moments
- [warmly] - for greetings, comfort, caring
- [calmly] - for neutral information
- [curious] - when asking follow-up questions
- [sighs] - for disappointment, tiredness
- [laughs] - for humor
- [pause] - for dramatic timing or natural breaks

RESPONSE STYLE FOR THIS QUERY:
{style_guide}

CRITICAL FORMATTING RULES:
- For ANY list: Put EACH item on its OWN LINE with a number (1. 2. 3.)
- NEVER use bullet points (•) - use numbers (1. 2. 3.)
- NO markdown (** or *) anywhere
- Plain text only

KNOWN USER INFORMATION (from long-term memory):
{self._format_user_info(user_info)}

LONG-TERM MEMORIES (semantically relevant):
{self._format_memories(relevant_memories)}

EXAMPLES:

User: "List top 5 footballers"
You: 
EMOTION: neutral
INTENSITY: 3
RESPONSE: Here are 5 of the greatest footballers:
1. Lionel Messi
2. Cristiano Ronaldo
3. Neymar Jr
4. Kylian Mbappe
5. Kevin De Bruyne
Want details on any of these players?
TAGGED: [calmly] Here are 5 of the greatest footballers:
1. Lionel Messi
2. Cristiano Ronaldo
3. Neymar Jr
4. Kylian Mbappe
5. Kevin De Bruyne
[curious] Want details on any of these players?

User: "yes" (after you asked about details)
You:
EMOTION: excited
INTENSITY: 6
RESPONSE: Great! Which player would you like to know more about? Messi, Ronaldo, Neymar, Mbappe, or De Bruyne?
TAGGED: [excited] Great! [curious] Which player would you like to know more about? Messi, Ronaldo, Neymar, Mbappe, or De Bruyne?

User: "I have a secret"
You:
EMOTION: curious
INTENSITY: 6
RESPONSE: Ooh, I love secrets! What is it? I promise I'm a great listener.
TAGGED: [whispers] Ooh, I love secrets! [curious] What is it? I promise I'm a great listener.

User: "Who's better, Messi or Ronaldo?"
You:
EMOTION: excited
INTENSITY: 8
RESPONSE: The eternal debate! Messi has more Ballon d'Ors (8 vs 5) and a World Cup, while Ronaldo has more Champions League goals and is the all-time top scorer. I'd give Messi the edge for his pure magic on the ball, but both are legends. Who's your pick?
TAGGED: [excited] The eternal debate! Messi has more Ballon d'Ors - 8 versus 5 - and a World Cup, while Ronaldo has more Champions League goals and is the all-time top scorer. [pause] I'd give Messi the edge for his pure magic on the ball, but both are legends. [curious] Who's your pick?

Now process the user's message. Format EXACTLY as:
EMOTION: [emotion]
INTENSITY: [1-10]
RESPONSE: [plain text]
TAGGED: [text with ElevenLabs emotion tags]"""

        print("\n" + "="*50)
        print(f"📝 USER MESSAGE: {user_message}")
        print(f"📊 Query Type: {query_type}")
        print("="*50)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500 if query_type == "CONCISE_LIST" else 800,
                temperature=0.85
            )
            
            output = response.choices[0].message.content
            
            print(f"📏 RAW RESPONSE LENGTH: {len(output)} characters")
            print("-"*50)
            print("🤖 RAW GPT OUTPUT:")
            print(output)
            print("-"*50)
            print("="*50 + "\n")
            
            result = self._parse_gpt_output(output)
            
            print(f"📦 FINAL RESPONSE:\n{result['response']}")
            print(f"😊 EMOTION: {result['emotion']}, INTENSITY: {result['intensity']}")
            
            # Extract and store the question asked (for follow-up context)
            if "?" in result["response"]:
                # Extract the last question
                questions = re.findall(r'[^.!?]*\?', result["response"])
                if questions:
                    self.last_question_asked = questions[-1].strip()
            
            self.vector_memory.add_memory(
                user_message=user_message,
                assistant_response=result["response"],
                emotion=result["emotion"]
            )
            
            self._add_to_recent(user_message, result)
            
            result["user_message"] = user_message
            return result
            
        except Exception as e:
            print(f"❌ OpenAI Error: {e}")
            return {
                "emotion": "neutral",
                "intensity": 5,
                "response": "I'm here to help. Could you please repeat that?",
                "tagged_script": "[calmly] I'm here to help. Could you please repeat that?",
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
    
    def _format_response(self, text: str) -> str:
        """Clean markdown and ensure proper list formatting"""
        # Remove markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # Force line breaks before numbered items
        text = re.sub(r'(\d+\.\s)', r'\n\1', text)
        
        # Process lines
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            # Convert bullets to numbers if needed
            if stripped.startswith(('• ', '* ', '- ')):
                item_num = len(formatted_lines) + 1
                formatted_lines.append(f"{item_num}. {stripped[2:]}")
            elif re.match(r'^\d+\.\s+', stripped):
                formatted_lines.append(stripped)
            else:
                formatted_lines.append(stripped)
        
        text = '\n'.join(formatted_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _parse_gpt_output(self, output: str) -> dict:
        """Parse GPT's structured output"""
        result = {
            "emotion": "neutral",
            "intensity": 5,
            "response": "",
            "tagged_script": ""
        }
        
        # Extract EMOTION
        emotion_match = re.search(r'EMOTION:\s*(\w+)', output, re.IGNORECASE)
        if emotion_match:
            result["emotion"] = emotion_match.group(1).lower()
        
        # Extract INTENSITY
        intensity_match = re.search(r'INTENSITY:\s*(\d+)', output)
        if intensity_match:
            result["intensity"] = int(intensity_match.group(1))
        
        # Extract RESPONSE
        response_match = re.search(r'RESPONSE:\s*(.+?)(?=\n\w+:|$)', output, re.DOTALL)
        if response_match:
            result["response"] = response_match.group(1).strip()
        else:
            result["response"] = output.strip()
        
        # Extract TAGGED script
        tagged_match = re.search(r'TAGGED:\s*(.+)', output, re.DOTALL | re.IGNORECASE)
        if tagged_match:
            result["tagged_script"] = tagged_match.group(1).strip()
        else:
            clean_response = re.sub(r'\[.*?\]', '', result["response"]).strip()
            result["tagged_script"] = f"[calmly] {clean_response}"
        
        # Clean response
        result["response"] = re.sub(r'\[.*?\]', '', result["response"])
        result["response"] = self._format_response(result["response"])
        
        # Clean tagged script for audio
        result["tagged_script"] = re.sub(r'\*\*(.*?)\*\*', r'\1', result["tagged_script"])
        result["tagged_script"] = re.sub(r'\*(.*?)\*', r'\1', result["tagged_script"])
        result["tagged_script"] = result["tagged_script"].strip()
        
        return result
    
    def clear_memory(self):
        """Clear all memories"""
        self.vector_memory.clear_memory()
        self.recent_messages = []
        self.last_question_asked = None
        self.conversation_stage = "new"
        self.user_engagement_level = 0
        self.message_count = 0
        print("🧹 All memories cleared")
    
    def get_memory_summary(self) -> dict:
        """Get memory summary"""
        stats = self.vector_memory.get_memory_stats()
        return {
            "total_memories": stats["total_vectors"],
            "session_id": stats["session_id"],
            "user_info": self._extract_user_info_from_memories()
        }