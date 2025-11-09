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

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        try:
            response = self.model.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error generating response: {str(e)}"

class ZAILLM(LLM):
    """Custom LangChain wrapper for ZAI models"""
    api_key: str
    model_name: str = "glm-4"
    base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key

    @property
    def _llm_type(self) -> str:
        return "zai"

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

        except Exception as e:
            return f"Error generating response: {str(e)}"