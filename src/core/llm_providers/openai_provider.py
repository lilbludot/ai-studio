"""
OpenAI LLM Provider for AI Studio
Implements the OpenAI API integration
Created: 2025-05-27
"""

import openai
from openai import OpenAI
from typing import Dict, List, Any, Optional, Generator
import logging
import json

from .base_provider import (
    BaseLLMProvider, ModelInfo, LLMMessage, LLMResponse, 
    StreamChunk, ModelCapability
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    Provider for OpenAI's GPT models
    """
    
    # Model configurations
    MODELS = {
        "gpt-4-turbo-preview": ModelInfo(
            name="gpt-4-turbo-preview",
            display_name="GPT-4 Turbo",
            max_tokens=128000,  # 128k context window
            max_output_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=True,
            supports_json_mode=True,
            cost_per_1k_input=0.01,    # $10 per million tokens
            cost_per_1k_output=0.03    # $30 per million tokens
        ),
        "gpt-4": ModelInfo(
            name="gpt-4",
            display_name="GPT-4",
            max_tokens=8192,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=False,
            supports_json_mode=True,
            cost_per_1k_input=0.03,    # $30 per million tokens
            cost_per_1k_output=0.06    # $60 per million tokens
        ),
        "gpt-3.5-turbo": ModelInfo(
            name="gpt-3.5-turbo",
            display_name="GPT-3.5 Turbo",
            max_tokens=16385,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=False,
            supports_json_mode=True,
            cost_per_1k_input=0.0005,  # $0.50 per million tokens
            cost_per_1k_output=0.0015  # $1.50 per million tokens
        ),
        "gpt-4o": ModelInfo(
            name="gpt-4o",
            display_name="GPT-4o",
            max_tokens=128000,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=True,
            supports_json_mode=True,
            cost_per_1k_input=0.005,   # $5 per million tokens
            cost_per_1k_output=0.015   # $15 per million tokens
        ),
        "gpt-4o-mini": ModelInfo(
            name="gpt-4o-mini",
            display_name="GPT-4o Mini",
            max_tokens=128000,
            max_output_tokens=16384,
            supports_streaming=True,
            supports_functions=True,
            supports_vision=True,
            supports_json_mode=True,
            cost_per_1k_input=0.00015,  # $0.15 per million tokens
            cost_per_1k_output=0.0006   # $0.60 per million tokens
        )
    }
    
    def __init__(self, api_key: str, **kwargs):
        """
        Initialize OpenAI provider
        
        Args:
            api_key: OpenAI API key
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=api_key)
        
        # Default model
        self.default_model = kwargs.get("default_model", "gpt-4-turbo-preview")
        
        # Optional organization ID
        self.organization = kwargs.get("organization")
        if self.organization:
            self.client.organization = self.organization
        
        logger.info(f"OpenAIProvider initialized with default model: {self.default_model}")
    
    def _validate_api_key(self) -> None:
        """Validate the API key format"""
        if not self.api_key or not self.api_key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get list of available OpenAI models"""
        return list(self.MODELS.values())
    
    def get_provider_name(self) -> str:
        """Get the provider name"""
        return "OpenAI"
    
    def validate_model(self, model: str) -> bool:
        """Check if a model is valid/available"""
        return model in self.MODELS
    
    def send_message(self,
                    messages: List[LLMMessage],
                    model: str,
                    max_tokens: Optional[int] = None,
                    temperature: float = 0.7,
                    **kwargs) -> LLMResponse:
        """
        Send messages to OpenAI and get response
        
        Args:
            messages: List of messages in the conversation
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Temperature for randomness (0-2 for OpenAI)
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse object
        """

        if not self.validate_model(model):
            raise ValueError(f"Invalid model: {model}")
        
        # Get model info
        model_info = self.MODELS[model]
        
        # Set default max tokens if not provided
        if max_tokens is None:
            max_tokens = min(1000, model_info.max_output_tokens)
        
        # Format messages for OpenAI API
        formatted_messages = self._format_messages_for_openai(messages)
        
        
        try:
            # Build API parameters
            api_params = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            # Handle JSON mode if requested
            if kwargs.get("response_format") == "json_object" and model_info.supports_json_mode:
                api_params["response_format"] = {"type": "json_object"}
            
            # Send to OpenAI API
            response = self.client.chat.completions.create(**api_params)
    
            # Extract content
            choice = response.choices[0]
            content = choice.message.content or ""
            
            # Check for function call
            function_call = None
            if hasattr(choice.message, 'function_call') and choice.message.function_call:
                function_call = {
                    "name": choice.message.function_call.name,
                    "arguments": choice.message.function_call.arguments
                }
            
            # Build response
            return LLMResponse(
                content=content,
                model=model,
                finish_reason=choice.finish_reason or "stop",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                raw_response=response,
                function_call=function_call
            )
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise
    
    def stream_message(self,
                      messages: List[LLMMessage],
                      model: str,
                      max_tokens: Optional[int] = None,
                      temperature: float = 0.7,
                      **kwargs) -> Generator[StreamChunk, None, None]:
        """
        Stream messages from OpenAI
        
        Args:
            messages: List of messages in the conversation
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Temperature for randomness (0-2)
            **kwargs: Additional parameters
            
        Yields:
            StreamChunk objects
        """
        if not self.validate_model(model):
            raise ValueError(f"Invalid model: {model}")
        
        # Get model info
        model_info = self.MODELS[model]
        
        # Set default max tokens if not provided
        if max_tokens is None:
            max_tokens = min(1000, model_info.max_output_tokens)
        
        # Format messages for OpenAI API
        formatted_messages = self._format_messages_for_openai(messages)
        
        try:
            # Build API parameters
            api_params = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
                **kwargs
            }
            
            # Stream from OpenAI API
            stream = self.client.chat.completions.create(**api_params)
            
            accumulated_content = ""
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    
                    # Extract content
                    if delta.content:
                        accumulated_content += delta.content
                        yield StreamChunk(
                            content=delta.content,
                            is_final=False
                        )
                    
                    # Check if this is the final chunk
                    if chunk.choices[0].finish_reason:
                        yield StreamChunk(
                            content="",
                            is_final=True,
                            finish_reason=chunk.choices[0].finish_reason,
                            usage={
                                # OpenAI doesn't provide usage in streaming
                                # We'll estimate based on content
                                "prompt_tokens": self.estimate_tokens(
                                    self._messages_to_string(messages), model
                                ),
                                "completion_tokens": self.estimate_tokens(
                                    accumulated_content, model
                                ),
                                "total_tokens": 0  # Will be calculated
                            }
                        )
                        
        except Exception as e:
            logger.error(f"Error streaming from OpenAI API: {e}")
            raise
    
    def estimate_tokens(self, text: str, model: str) -> int:
        """
        Estimate token count for text
        
        Args:
            text: Text to count tokens for
            model: Model to use for estimation
            
        Returns:
            Estimated token count
        """
        # OpenAI uses tiktoken for tokenization
        # For a rough estimate: 1 token ≈ 4 characters
        # GPT-4 is slightly different but close enough
        return len(text) // 4
    
    def _format_messages_for_openai(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """
        Format messages for OpenAI's expected format
        
        Args:
            messages: List of LLMMessage objects
            
        Returns:
            List of formatted message dictionaries
        """
        formatted = []
        
        for msg in messages:
            message_dict = {
                "role": msg.role,
                "content": msg.content
            }
            
            # Add name if present (for function responses)
            if msg.name:
                message_dict["name"] = msg.name
            
            # Add function call if present
            if msg.function_call:
                message_dict["function_call"] = msg.function_call
            
            formatted.append(message_dict)
        
        return formatted
    
    def _messages_to_string(self, messages: List[LLMMessage]) -> str:
        """Convert messages to string for token estimation"""
        return " ".join([msg.content for msg in messages])
    
    def create_function_schema(self, 
                              name: str, 
                              description: str,
                              parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a function schema for function calling
        
        Args:
            name: Function name
            description: Function description
            parameters: JSON Schema for parameters
            
        Returns:
            Function schema dict
        """
        return {
            "name": name,
            "description": description,
            "parameters": parameters
        }