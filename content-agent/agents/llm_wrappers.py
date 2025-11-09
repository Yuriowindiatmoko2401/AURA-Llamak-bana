from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.llms.base import LLM
from typing import Optional, List, Dict, Any
import requests
import json
import time
import threading
from pydantic import Field

# Rate limiting for Gemini API
class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 15):  # Conservative limit
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.lock = threading.Lock()

    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]

            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest_request = min(self.requests)
                wait_time = 60 - (now - oldest_request)
                if wait_time > 0:
                    print(f"Rate limit reached, waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)

            self.requests.append(now)

# Global rate limiter for Gemini
gemini_rate_limiter = RateLimiter(max_requests_per_minute=15)

class FallbackLLM:
    """Fallback LLM manager that automatically switches providers on failure"""

    def __init__(self):
        self.providers = []
        self.current_index = 0
        self._init_providers()

    def _init_providers(self):
        """Initialize available LLM providers based on environment variables"""
        import os

        # Check for available API keys and create providers
        if os.getenv("GEMINI_API_KEY"):
            try:
                self.providers.append({
                    'name': 'gemini',
                    'instance': GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"))
                })
                print("✅ Gemini provider initialized")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini: {e}")

        if os.getenv("ZAI_API_KEY"):
            try:
                self.providers.append({
                    'name': 'zai',
                    'instance': ZAILLM(api_key=os.getenv("ZAI_API_KEY"))
                })
                print("✅ ZAI provider initialized")
            except Exception as e:
                print(f"❌ Failed to initialize ZAI: {e}")

        if os.getenv("DEEPSEEK_API_KEY"):
            try:
                self.providers.append({
                    'name': 'deepseek',
                    'instance': DeepseekLLM(api_key=os.getenv("DEEPSEEK_API_KEY"))
                })
                print("✅ Deepseek provider initialized")
            except Exception as e:
                print(f"❌ Failed to initialize Deepseek: {e}")

        if not self.providers:
            raise ValueError("No LLM providers available. Please configure API keys.")

        print(f"🚀 Initialized {len(self.providers)} LLM providers: {[p['name'] for p in self.providers]}")

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Try each provider in sequence until one succeeds"""

        for _ in range(len(self.providers)):
            provider = self.providers[self.current_index]

            try:
                print(f"🤖 Trying {provider['name']} provider...")
                result = provider['instance']._call(prompt, stop)

                # Check if the result indicates a quota/rate limit error
                if "quota exceeded" in result.lower() or "rate limit" in result.lower() or "429" in result:
                    print(f"⚠️  {provider['name']} provider quota exceeded. Trying next provider...")
                    self.current_index = (self.current_index + 1) % len(self.providers)
                    continue

                print(f"✅ {provider['name']} provider succeeded")
                return result

            except Exception as e:
                print(f"❌ {provider['name']} provider failed: {e}")
                self.current_index = (self.current_index + 1) % len(self.providers)
                continue

        return "Error: All LLM providers failed. Please check API keys and quotas."

    @property
    def model(self):
        return "fallback_llm"

    @property
    def model_identifier(self):
        return "fallback_llm"

# Global fallback LLM instance
fallback_llm = None

def get_fallback_llm():
    """Get or create the fallback LLM instance"""
    global fallback_llm
    if fallback_llm is None:
        fallback_llm = FallbackLLM()
    return fallback_llm

class GeminiLLM(LLM):
    """Custom LangChain wrapper for Gemini models using ChatGoogleGenerativeAI"""
    api_key: str
    model_name: str = "gemini-2.5-pro"
    _model: ChatGoogleGenerativeAI = Field(exclude=True)

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro", **kwargs):
        # Initialize Pydantic model first
        super().__init__(api_key=api_key, model_name=model_name, **kwargs)
        # Set internal attributes
        object.__setattr__(self, '_model', ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key
        ))

    @property
    def model(self):
        """Return the model name for CrewAI compatibility"""
        return self.model_name

    @property
    def _llm_type(self) -> str:
        return "gemini"

    @property
    def model_identifier(self) -> str:
        """Return the model identifier for CrewAI compatibility"""
        return self.model_name

    def to_dict(self):
        """Return a dictionary representation for CrewAI compatibility"""
        return {
            'model': self.model_name,
            'api_key': self.api_key
        }

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        max_retries = 3
        base_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                gemini_rate_limiter.wait_if_needed()

                response = self._model.invoke(prompt)
                return response.content

            except Exception as e:
                error_str = str(e)

                # Check if it's a quota/rate limit error
                if "429" in error_str or "quota" in error_str.lower() or "ResourceExhausted" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        delay = base_delay * (2 ** attempt)
                        print(f"Gemini API quota exceeded. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        return "Error: Gemini API quota exceeded. Please try again later or switch to a different model."

                # For other errors, don't retry
                if attempt == max_retries - 1:
                    return f"Error generating response: {str(e)}"

                # For non-quota errors, shorter retry
                time.sleep(1)

        return f"Error generating response after {max_retries} attempts"

class ZAILLM(LLM):
    """Custom LangChain wrapper for ZAI models"""
    api_key: str
    model_name: str = "glm-4.6"  # Updated to use GLM-4.6 model
    base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self, api_key: str, model_name: str = "glm-4.6", **kwargs):
        super().__init__(api_key=api_key, model_name=model_name, **kwargs)
        self.api_key = api_key
        self.model_name = model_name

    @property
    def _llm_type(self) -> str:
        return "zai"

    @property
    def model(self):
        """Return the model name for CrewAI compatibility"""
        return self.model_name

    @property
    def model_identifier(self) -> str:
        """Return the model identifier for CrewAI compatibility"""
        return self.model_name

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }

            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                return "Error: ZAI API balance insufficient. Please top up your account at https://open.bigmodel.cn/"
            elif response.status_code == 401:
                return "Error: ZAI API key is invalid or expired. Please check your ZAI_API_KEY."
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                return f"Error: ZAI API request failed - {error_msg}"
            else:
                return f"Error: ZAI API HTTP {response.status_code} - {str(e)}"
        except Exception as e:
            return f"Error generating response: {str(e)}"

class DeepseekLLM(LLM):
    """Custom LangChain wrapper for Deepseek models using Replicate API"""
    api_key: str = Field(default="")

    def __init__(self, api_key: str, model_name: str = "deepseek-ai/deepseek-r1", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        # Set Replicate API key
        import replicate
        import os
        # Use REPLICATE_API_KEY from environment if available, fallback to provided api_key
        replicate_api_key = os.getenv("REPLICATE_API_KEY", api_key)
        # Set both the environment variable and the client token
        os.environ["REPLICATE_API_TOKEN"] = replicate_api_key
        replicate.api_token = replicate_api_key
        # Store model name as instance variable (not Pydantic field)
        object.__setattr__(self, '_model_name', model_name)

    @property
    def _llm_type(self) -> str:
        return "custom_deepseek_replicate"  # Changed to avoid litellm detection

    @property
    def model(self):
        """Return the model name for CrewAI compatibility"""
        return getattr(self, '_model_name', 'deepseek-ai/deepseek-r1')

    @property
    def model_name(self):
        """Return the model name for backward compatibility"""
        return getattr(self, '_model_name', 'deepseek-ai/deepseek-r1')

    @property
    def model_identifier(self) -> str:
        """Return the model identifier for CrewAI compatibility"""
        return getattr(self, '_model_name', 'deepseek-ai/deepseek-r1')

    def to_dict(self):
        """Return a dictionary representation for CrewAI compatibility"""
        return {
            'model': self._model_name,
            'api_key': self.api_key,
            'model_name': self._model_name,
            'model_identifier': self._model_name
        }

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        try:
            import replicate

            # Run DeepSeek R1 model using official Replicate client
            output = replicate.run(
                "deepseek-ai/deepseek-r1",
                input={
                    "prompt": prompt,
                    "max_tokens": 2048,
                    "temperature": 0.1,
                    "top_p": 1
                }
            )

            # DeepSeek-R1 outputs an iterator of strings, join them
            return "".join(output)

        except Exception as e:
            # Handle specific Replicate errors
            error_str = str(e)
            if "401" in error_str or "Unauthorized" in error_str:
                return "Error: Deepseek API key is invalid or expired. Please check your DEEPSEEK_API_KEY."
            elif "402" in error_str or "payment" in error_str.lower():
                return "Error: Deepseek API payment required. Please check your Replicate account balance."
            elif "429" in error_str or "rate limit" in error_str.lower():
                return "Error: Deepseek API rate limit exceeded. Please try again later."
            elif "timeout" in error_str.lower():
                return "Error: Deepseek prediction timed out. Please try again."
            else:
                return f"Error generating response: {str(e)}"