"""
Base LLM Provider Interface for AI Studio
Defines the abstract interface that all LLM providers must implement
Created: 2025-05-27
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Generator, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """Capabilities that models might support"""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"


@dataclass
class ModelInfo:
    """Information about a specific model"""
    name: str
    display_name: str
    max_tokens: int
    max_output_tokens: int
    supports_streaming: bool
    supports_functions: bool
    supports_vision: bool
    supports_json_mode: bool
    cost_per_1k_input: float  # in USD
    cost_per_1k_output: float  # in USD
    
    @property
    def capabilities(self) -> List[ModelCapability]:
        """Get list of model capabilities"""
        caps = [ModelCapability.TEXT_GENERATION]
        
        if self.supports_streaming:
            caps.append(ModelCapability.STREAMING)
        if self.supports_functions:
            caps.append(ModelCapability.FUNCTION_CALLING)
        if self.supports_vision:
            caps.append(ModelCapability.VISION)
        if self.supports_json_mode:
            caps.append(ModelCapability.JSON_MODE)
            
        return caps


@dataclass
class LLMMessage:
    """Standard message format for all providers"""
    role: str  # "user", "assistant", "system"
    content: str
    name: Optional[str] = None  # For function calls
    function_call: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        data = {"role": self.role, "content": self.content}
        if self.name:
            data["name"] = self.name
        if self.function_call:
            data["function_call"] = self.function_call
        return data


@dataclass
class LLMResponse:
    """Standard response format from all providers"""
    content: str
    model: str
    finish_reason: str  # "stop", "length", "function_call"
    usage: Dict[str, int]  # {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    raw_response: Any  # Original response from provider
    function_call: Optional[Dict[str, Any]] = None
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens used"""
        return self.usage.get("total_tokens", 0)
    
    @property
    def cost(self) -> float:
        """Calculate cost based on usage (to be implemented by providers)"""
        # This would be calculated based on model pricing
        return 0.0


@dataclass
class StreamChunk:
    """A chunk of streaming response"""
    content: str
    is_final: bool = False
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    All LLM providers must implement this interface.
    """
    
    def __init__(self, api_key: str, **kwargs):
        """
        Initialize the provider
        
        Args:
            api_key: API key for the provider
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self._validate_api_key()
        
    @abstractmethod
    def _validate_api_key(self) -> None:
        """Validate the API key format"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[ModelInfo]:
        """
        Get list of available models
        
        Returns:
            List of ModelInfo objects
        """
        pass
    
    @abstractmethod
    def send_message(self,
                    messages: List[LLMMessage],
                    model: str,
                    max_tokens: Optional[int] = None,
                    temperature: float = 0.7,
                    **kwargs) -> LLMResponse:
        """
        Send messages to the LLM and get response
        
        Args:
            messages: List of messages in the conversation
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Temperature for randomness (0-1)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse object
        """
        pass
    
    @abstractmethod
    def stream_message(self,
                      messages: List[LLMMessage],
                      model: str,
                      max_tokens: Optional[int] = None,
                      temperature: float = 0.7,
                      **kwargs) -> Generator[StreamChunk, None, None]:
        """
        Stream messages from the LLM
        
        Args:
            messages: List of messages in the conversation
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Temperature for randomness (0-1)
            **kwargs: Additional provider-specific parameters
            
        Yields:
            StreamChunk objects
        """
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str, model: str) -> int:
        """
        Estimate token count for text
        
        Args:
            text: Text to count tokens for
            model: Model to use for estimation
            
        Returns:
            Estimated token count
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name"""
        pass
    
    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """
        Check if a model is valid/available
        
        Args:
            model: Model identifier
            
        Returns:
            True if model is valid
        """
        pass
    
    def format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """
        Format messages for the provider's API
        Default implementation - providers can override
        
        Args:
            messages: List of LLMMessage objects
            
        Returns:
            List of formatted message dictionaries
        """
        return [msg.to_dict() for msg in messages]
    
    def calculate_cost(self, 
                      model: str, 
                      input_tokens: int, 
                      output_tokens: int) -> float:
        """
        Calculate cost for a request
        
        Args:
            model: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        models = {m.name: m for m in self.get_available_models()}
        
        if model not in models:
            return 0.0
            
        model_info = models[model]
        
        input_cost = (input_tokens / 1000) * model_info.cost_per_1k_input
        output_cost = (output_tokens / 1000) * model_info.cost_per_1k_output
        
        return input_cost + output_cost
    
    def supports_capability(self, model: str, capability: ModelCapability) -> bool:
        """
        Check if a model supports a specific capability
        
        Args:
            model: Model identifier
            capability: Capability to check
            
        Returns:
            True if supported
        """
        models = {m.name: m for m in self.get_available_models()}
        
        if model not in models:
            return False
            
        return capability in models[model].capabilities
    
    def get_model_info(self, model: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model
        
        Args:
            model: Model identifier
            
        Returns:
            ModelInfo if found, None otherwise
        """
        models = {m.name: m for m in self.get_available_models()}
        return models.get(model)
    
    def create_message(self, 
                      role: str, 
                      content: str,
                      **kwargs) -> LLMMessage:
        """
        Helper to create a message
        
        Args:
            role: Message role
            content: Message content
            **kwargs: Additional message properties
            
        Returns:
            LLMMessage object
        """
        return LLMMessage(role=role, content=content, **kwargs)
    
    def __str__(self) -> str:
        """String representation"""
        return f"{self.get_provider_name()}Provider"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        models = self.get_available_models()
        return f"{self.get_provider_name()}Provider(models={len(models)})"