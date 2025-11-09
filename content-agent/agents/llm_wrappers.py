from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.llms.base import LLM
from typing import Optional, List, Dict, Any
import requests
import json
from pydantic import Field

class GeminiLLM(LLM):
    """Custom LangChain wrapper for Gemini models using ChatGoogleGenerativeAI"""
    api_key: str
    model_name: str = "gemini-1.5-flash"
    _model: ChatGoogleGenerativeAI = Field(exclude=True)

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash", **kwargs):
        llm_kwargs = {
            'api_key': api_key,
            'model_name': model_name,
            **kwargs
        }
        super().__init__(**llm_kwargs)
        object.__setattr__(self, '_model', ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key
        ))

    @property
    def model(self):
        return self._model

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
        try:
            response = self.model.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error generating response: {str(e)}"

class ZAILLM(LLM):
    """Custom LangChain wrapper for ZAI models"""
    api_key: str
    model_name: str = "glm-4.5-air"  # Updated to use available model
    base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self, api_key: str, model_name: str = "glm-4.5-air", **kwargs):
        super().__init__(api_key=api_key, model_name=model_name, **kwargs)
        self.api_key = api_key
        self.model_name = model_name

    @property
    def _llm_type(self) -> str:
        return "zai"

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