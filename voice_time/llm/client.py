"""Ollama client wrapper for LLM interactions."""
import json
import httpx
from typing import Optional, Dict, Any
from ..config import OllamaConfig


class OllamaClient:
    """
    Wrapper for Ollama API with JSON mode support.
    
    Optimized for Qwen2.5-7B-Instruct which excels at structured output.
    """
    
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.base_url = config.host
        self.model = config.model
        self.timeout = config.timeout
        
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = True,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Generate completion from Ollama.
        
        Args:
            prompt: User prompt
            system: Optional system prompt
            json_mode: If True, forces JSON output
            temperature: Sampling temperature (0.2 for structured output)
            
        Returns:
            Parsed JSON response (if json_mode=True) or text string
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        
        if system:
            payload["system"] = system
            
        if json_mode:
            payload["format"] = "json"
        
        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get("response", "")
            
            if json_mode:
                # Parse JSON response
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse JSON response: {response_text}") from e
            else:
                return {"text": response_text}
                
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to connect to Ollama: {e}")
    
    def health_check(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            url = f"{self.base_url}/api/tags"
            response = httpx.get(url, timeout=5)
            response.raise_for_status()
            
            # Check if our model is available
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            return any(self.model in name for name in model_names)
        except:
            return False
