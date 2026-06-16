import httpx
from typing import Optional, List, Dict, Any
from config import settings

class AIService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.io/api/v1"
        self.model = "anthropic/claude-3.5-sonnet"
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        mode: str = "chat",
        explain_mode: Optional[str] = None,
        humanizer_mode: Optional[str] = None,
        code_language: Optional[str] = None
    ) -> str:
        """Send chat request to Claude via OpenRouter"""
        
        system_prompt = self._build_system_prompt(mode, explain_mode, humanizer_mode, code_language)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "system": system_prompt,
            "temperature": 0.7,
            "max_tokens": 4000,
            "top_p": 1
        }
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    def _build_system_prompt(
        self,
        mode: str,
        explain_mode: Optional[str],
        humanizer_mode: Optional[str],
        code_language: Optional[str]
    ) -> str:
        base = "You are DevBuddy AI, an expert coding assistant. Help users write, debug, and understand code."
        
        if mode == "explain":
            explain_prompts = {
                "beginner": "Explain code in very simple terms, like you're teaching a 10-year-old. Use analogies.",
                "student": "Explain code for a computer science student. Include concepts and theory.",
                "developer": "Explain code for a working developer. Focus on logic and patterns.",
                "senior_dev": "Explain for a senior engineer. Discuss architecture, performance, and edge cases.",
                "interview": "Explain as if in a technical interview. Be comprehensive and articulate.",
                "eli5": "Explain Like I'm 5. Use the simplest possible language."
            }
            base += f"\n\n{explain_prompts.get(explain_mode, explain_prompts['developer'])}"
        
        if mode == "humanizer":
            humanizer_prompts = {
                "professional": "Rewrite text in formal, professional business language.",
                "casual": "Rewrite text in friendly, conversational language.",
                "simple": "Rewrite text in simple, clear language anyone can understand.",
                "academic": "Rewrite text in academic, scholarly language with proper citations.",
                "github_readme": "Rewrite text as GitHub README markdown. Use clear sections and formatting.",
                "custom_voice": "Rewrite text in a unique, memorable voice."
            }
            base += f"\n\n{humanizer_prompts.get(humanizer_mode, humanizer_prompts['professional'])}"
        
        if mode == "code" and code_language:
            base += f"\n\nWrite code in {code_language}. Format with proper syntax highlighting markers."
        
        return base
    
    async def execute_code(self, code: str, language: str) -> str:
        """Execute code using Piston API"""
        
        language_map = {
            "python": "python",
            "javascript": "javascript",
            "typescript": "typescript",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
            "html": "html",
            "css": "css",
            "sql": "sql",
            "bash": "bash"
        }
        
        piston_lang = language_map.get(language.lower(), language.lower())
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "language": piston_lang,
            "source": code,
            "stdin": ""
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    f"{settings.PISTON_API_URL}/execute",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                output = result.get("run", {}).get("stdout", "")
                error = result.get("run", {}).get("stderr", "")
                
                if error:
                    return f"Error:\n{error}"
                return output if output else "(No output)"
            except Exception as e:
                return f"Execution Error: {str(e)}"
    
    def validate_code_format(self, code: str, language: str) -> bool:
        """Basic code validation"""
        if not code or len(code) > 100000:
            return False
        return True

ai_service = AIService()