from abc import ABC, abstractmethod
from typing import List, Any, Optional, Dict
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

class AbstractBrain(ABC):
    @abstractmethod
    def bind_optimized_tools(self, tools: List[Any], context: Optional[Dict] = None):
        """middleware binding option"""
        pass

    @abstractmethod
    def get_model(self) -> BaseChatModel:
        pass

class OpenAIBrain(AbstractBrain):
    def __init__(self, model_name: str = "gpt-4o", api_key: Optional[str] = None):
        kwargs = {
            "model": model_name,
            "temperature": 0
        }
        if api_key is not None:
            kwargs["openai_api_key"] = api_key
            
        self.model = ChatOpenAI(**kwargs)
        self._bound_model = None

    def bind_optimized_tools(self, tools: List[Any], context: Optional[Dict] = None):
        """
        Bind optimized tools to the model for enhanced capabilities
        """
        # Placeholder cho CASS:
        # optimized_tools = CASS.filter(tools, context)
        optimized_tools = tools 
        
        formatted_tools = []
        for t in optimized_tools:
            if hasattr(t, "name") and hasattr(t, "description") and hasattr(t, "args_schema"):
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.args_schema.model_json_schema()
                    }
                })
            else:
                formatted_tools.append(t)
        
        self._bound_model = self.model.bind_tools(formatted_tools)
        return self._bound_model

    def get_model(self) -> BaseChatModel:
        if self._bound_model is None:
            return self.model
        return self._bound_model