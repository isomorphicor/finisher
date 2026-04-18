from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class BaseSkill(ABC):
    """
    Abstract Base Class for all Investment Skills.
    A 'Skill' is a deterministic Python function wrapped for LLM usage.
    """
    name: str = "base_skill"
    description: str = "Base description"
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """
        Converts the skill into an OpenAI/LiteLLM compatible tool definition.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema()
            }
        }

    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """
        Returns the JSON Schema for the tool's parameters.
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        The actual implementation of the skill.
        """
        pass

    def format_output(self, result: Dict[str, Any]) -> str:
        """
        Formats the raw result into a human/LLM-readable string.
        """
        return str(result)
