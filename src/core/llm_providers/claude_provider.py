"""
Claude LLM Provider for AI Studio
Implements the Anthropic Claude API integration
Created: 2025-05-27
"""

import anthropic
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from typing import Dict, List, Any, Optional, Generator
import logging

from .base_provider import (
    BaseLLMProvider, ModelInfo, LLMMessage, LLMResponse, 
    StreamChunk, ModelCapability
)

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMProvider):
    """
    Provider for Anthropic's Claude models
    """
    
    # Model configurations
    MODELS = {
        "claude-opus-4-20250514": ModelInfo(
            name="claude-opus-4-20250514",
            display_name="Claude Opus 4",
            max_tokens=200000,  # 200k context window
            max_output_tokens=4096,
            supports_streaming=True,
            supports_functions=False,  # Claude doesn't have native function calling yet
            supports_vision=True,
            supports_json_mode=False,
            cost_per_1k_input=0.015,   # $15 per million tokens
            cost_per_1k_output=0.075   # $75 per million tokens
        ),
        "claude-3-5-sonnet-20241022": ModelInfo(
            name="claude-3-5-sonnet-20241022",
            display_name="Claude 3.5 Sonnet",
            max_tokens=200000,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_functions=False,
            supports_vision=True,
            supports_json_mode=False,
            cost_per_1k_input=0.003,   # $3 per million tokens
            cost_per_1k_output=0.015   # $15 per million tokens
        ),
        "claude-3-haiku-20240307": ModelInfo(
            name="claude-3-haiku-20240307",
            display_name="Claude 3 Haiku",
            max_tokens=200000,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_functions=False,
            supports_vision=True,
            supports_json_mode=False,
            cost_per_1k_input=0.00025,  # $0.25 per million tokens
            cost_per_1k_output=0.00125  # $1.25 per million tokens
        )
    }
    
    def __init__(self, api_key: str, **kwargs):
        """
        Initialize Claude provider
        
        Args:
            api_key: Anthropic API key
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        
        # Initialize Anthropic client
        self.client = Anthropic(api_key=api_key)
        
        # Default model
        self.default_model = kwargs.get("default_model", "claude-3-5-sonnet-20241022")
        
        logger.info(f"ClaudeProvider initialized with default model: {self.default_model}")
    
    def _validate_api_key(self) -> None:
        """Validate the API key format"""
        if not self.api_key or not self.api_key.startswith("sk-ant-"):
            raise ValueError("Invalid Anthropic API key format")
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get list of available Claude models"""
        return list(self.MODELS.values())
    
    def get_provider_name(self) -> str:
        """Get the provider name"""
        return "Claude"
    
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
        Send messages to Claude and get response
        
        Args:
            messages: List of messages in the conversation
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Temperature for randomness (0-1)
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
        
        # Format messages for Claude API
        formatted_messages = self._format_messages_for_claude(messages)
        
        # Extract system message if present
        system_message = None
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
                break
        
        try:
            # Build kwargs for API call
            api_kwargs = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            # Only add system if we have one
            if system_message:
                api_kwargs["system"] = system_message
            
            # Send to Claude API
            response = self.client.messages.create(**api_kwargs)
            
            
            
            # Extract content
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text
                    
                    
            
            # Build response
            return LLMResponse(
                content=content,
                model=model,
                finish_reason=response.stop_reason or "stop",
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            raise
    
    def stream_message(self,
                      messages: List[LLMMessage],
                      model: str,
                      max_tokens: Optional[int] = None,
                      temperature: float = 0.7,
                      **kwargs) -> Generator[StreamChunk, None, None]:
        """
        Stream messages from Claude
        
        Args:
            messages: List of messages in the conversation
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Temperature for randomness (0-1)
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
        
        # Format messages for Claude API
        formatted_messages = self._format_messages_for_claude(messages)
        
        # Extract system message if present
        system_message = None
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
                break
        
        try:
            # Build kwargs for API call
            api_kwargs = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            # Only add system if we have one
            if system_message:
                api_kwargs["system"] = system_message
            
            # Stream from Claude API
            with self.client.messages.stream(**api_kwargs) as stream:
                for event in stream:
                    if event.type == "content_block_delta":
                        yield StreamChunk(
                            content=event.delta.text,
                            is_final=False
                        )
                    elif event.type == "message_stop":
                        # Final chunk with usage info
                        message = stream.get_final_message()
                        yield StreamChunk(
                            content="",
                            is_final=True,
                            finish_reason=message.stop_reason or "stop",
                            usage={
                                "prompt_tokens": message.usage.input_tokens,
                                "completion_tokens": message.usage.output_tokens,
                                "total_tokens": message.usage.input_tokens + message.usage.output_tokens
                            }
                        )
                        
        except Exception as e:
            logger.error(f"Error streaming from Claude API: {e}")
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
        # Claude uses a similar tokenization to GPT models
        # Rough estimate: 1 token ≈ 4 characters
        # For more accuracy, we could use the anthropic tokenizer
        return len(text) // 4
    
    def _format_messages_for_claude(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """
        Format messages for Claude's expected format
        
        Args:
            messages: List of LLMMessage objects
            
        Returns:
            List of formatted message dictionaries
        """
        formatted = []
        
        for msg in messages:
            # Skip system messages as they're handled separately
            if msg.role == "system":
                continue
                
            # Claude expects "user" and "assistant" roles
            role = msg.role
            if role not in ["user", "assistant"]:
                role = "user"  # Default to user for unknown roles
            
            formatted.append({
                "role": role,
                "content": msg.content
            })
        
        # Ensure we have at least one message
        if not formatted:
            # If only system message was provided, add a default user message
            formatted.append({
                "role": "user",
                "content": "Hello"
            })
        
        return formatted
    
    def create_completion_prompt(self, messages: List[LLMMessage]) -> str:
        """
        Create a completion-style prompt (for backward compatibility)
        
        Args:
            messages: List of messages
            
        Returns:
            Formatted prompt string
        """
        prompt = ""
        
        for msg in messages:
            if msg.role == "system":
                prompt += f"{msg.content}\n\n"
            elif msg.role == "user":
                prompt += f"{HUMAN_PROMPT} {msg.content}"
            elif msg.role == "assistant":
                prompt += f"{AI_PROMPT} {msg.content}"
        
        # Ensure prompt ends with AI_PROMPT for completion
        if not prompt.endswith(AI_PROMPT):
            prompt += AI_PROMPT
        
        return prompt