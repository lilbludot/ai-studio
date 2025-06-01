"""
LLM Provider Manager for AI Studio
Manages multiple LLM providers and handles provider switching
Created: 2025-05-27
"""

import logging
from typing import Dict, List, Optional, Any, Generator, Type
from dataclasses import dataclass

from .base_provider import BaseLLMProvider, ModelInfo, LLMMessage, LLMResponse, StreamChunk
from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider
from ...utils.config import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a provider"""
    name: str
    provider_class: Type[BaseLLMProvider]
    api_key: str
    enabled: bool
    default_model: Optional[str] = None
    additional_config: Dict[str, Any] = None


class ProviderManager:
    """
    Manages multiple LLM providers and handles switching between them.
    Provides a unified interface for all LLM operations.
    """
    
    # Available provider classes
    PROVIDER_CLASSES = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        # "gemini": GeminiProvider,  # Future
    }
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize ProviderManager
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.current_provider_name: Optional[str] = None
        
        # Initialize providers from config
        self._initialize_providers()
        
        # Set default provider
        self._set_default_provider()
        
        logger.info(f"ProviderManager initialized with {len(self.providers)} providers")
    
    def _initialize_providers(self) -> None:
        """Initialize all enabled providers from configuration"""
        for provider_name, provider_class in self.PROVIDER_CLASSES.items():
            provider_config = self.config.get_provider_config(provider_name)
            
            if not provider_config or not provider_config.enabled:
                logger.info(f"Provider {provider_name} is disabled or not configured")
                continue
            
            if not provider_config.api_key:
                logger.warning(f"Provider {provider_name} enabled but no API key found")
                continue
            
            try:
                # Create provider instance
                kwargs = {
                    "default_model": provider_config.model
                }
                
                provider = provider_class(
                    api_key=provider_config.api_key,
                    **kwargs
                )
                
                self.providers[provider_name] = provider
                logger.info(f"Initialized {provider_name} provider")
                
            except Exception as e:
                logger.error(f"Failed to initialize {provider_name} provider: {e}")
    
    def _set_default_provider(self) -> None:
        """Set the default provider based on availability and configuration"""
        # First, try to use the configured default
        default_provider = self.config.get("llm.default_provider")
        if default_provider and default_provider in self.providers:
            self.current_provider_name = default_provider
            return
        
        # Otherwise, use the first available provider
        if self.providers:
            self.current_provider_name = list(self.providers.keys())[0]
            logger.info(f"Set default provider to: {self.current_provider_name}")
        else:
            logger.warning("No LLM providers available")
    
    def register_provider(self, name: str, provider: BaseLLMProvider) -> None:
        """
        Register a provider instance
        
        Args:
            name: Provider name
            provider: Provider instance
        """
        self.providers[name] = provider
        logger.info(f"Registered provider: {name}")
    
    def get_provider(self, name: Optional[str] = None) -> Optional[BaseLLMProvider]:
        """
        Get a provider by name
        
        Args:
            name: Provider name (uses current if not specified)
            
        Returns:
            Provider instance or None
        """
        if name is None:
            name = self.current_provider_name
            
        if name is None:
            return None
            
        return self.providers.get(name)
    
    def get_current_provider(self) -> Optional[BaseLLMProvider]:
        """Get the currently active provider"""
        return self.get_provider(self.current_provider_name)
    
    def list_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())
    
    def switch_provider(self, name: str) -> bool:
        """
        Switch to a different provider
        
        Args:
            name: Provider name to switch to
            
        Returns:
            True if successful
        """
        if name not in self.providers:
            logger.error(f"Provider {name} not available")
            return False
        
        self.current_provider_name = name
        logger.info(f"Switched to provider: {name}")
        return True
    
    def get_all_models(self) -> Dict[str, List[ModelInfo]]:
        """
        Get all available models from all providers
        
        Returns:
            Dictionary mapping provider names to their models
        """
        all_models = {}
        
        for name, provider in self.providers.items():
            try:
                models = provider.get_available_models()
                all_models[name] = models
            except Exception as e:
                logger.error(f"Failed to get models from {name}: {e}")
                all_models[name] = []
        
        return all_models
    
    def get_model_info(self, model: str, provider: Optional[str] = None) -> Optional[ModelInfo]:
        """
        Get information about a specific model
        
        Args:
            model: Model identifier
            provider: Provider name (searches all if not specified)
            
        Returns:
            ModelInfo if found
        """
        if provider:
            # Check specific provider
            prov = self.get_provider(provider)
            if prov:
                return prov.get_model_info(model)
        else:
            # Search all providers
            for prov in self.providers.values():
                info = prov.get_model_info(model)
                if info:
                    return info
        
        return None
    
    def send_message(self,
                    messages: List[LLMMessage],
                    model: Optional[str] = None,
                    provider: Optional[str] = None,
                    **kwargs) -> LLMResponse:
        """
        Send messages to LLM
        
        Args:
            messages: List of messages
            model: Model to use (uses provider default if not specified)
            provider: Provider to use (uses current if not specified)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse
        """

        # Get provider
        prov = self.get_provider(provider)
        if not prov:
            raise ValueError(f"No provider available: {provider or 'current'}")
        
        # Use default model if not specified
        if model is None:
            # Try to get from provider's default
            if hasattr(prov, 'default_model'):
                model = prov.default_model
            else:
                # Get first available model
                models = prov.get_available_models()
                if models:
                    model = models[0].name
                else:
                    raise ValueError("No models available")
        
        
        # Send message
        response = prov.send_message(messages, model, **kwargs)
        
        # Add provider info to response
        response.provider = provider or self.current_provider_name
        
        return response
    
    def stream_message(self,
                      messages: List[LLMMessage],
                      model: Optional[str] = None,
                      provider: Optional[str] = None,
                      **kwargs) -> Generator[StreamChunk, None, None]:
        """
        Stream messages from LLM
        
        Args:
            messages: List of messages
            model: Model to use
            provider: Provider to use
            **kwargs: Additional parameters
            
        Yields:
            StreamChunk objects
        """
        # Get provider
        prov = self.get_provider(provider)
        if not prov:
            raise ValueError(f"No provider available: {provider or 'current'}")
        
        # Use default model if not specified
        if model is None:
            if hasattr(prov, 'default_model'):
                model = prov.default_model
            else:
                models = prov.get_available_models()
                if models:
                    model = models[0].name
                else:
                    raise ValueError("No models available")
        
        # Stream from provider
        yield from prov.stream_message(messages, model, **kwargs)
    
    def estimate_tokens(self, text: str, model: str, provider: Optional[str] = None) -> int:
        """
        Estimate token count
        
        Args:
            text: Text to estimate
            model: Model to use for estimation
            provider: Provider (will search if not specified)
            
        Returns:
            Estimated token count
        """
        if provider:
            prov = self.get_provider(provider)
            if prov:
                return prov.estimate_tokens(text, model)
        else:
            # Find which provider has this model
            for prov in self.providers.values():
                if prov.validate_model(model):
                    return prov.estimate_tokens(text, model)
        
        # Fallback to simple estimation
        return len(text) // 4
    
    def calculate_cost(self,
                      model: str,
                      input_tokens: int,
                      output_tokens: int,
                      provider: Optional[str] = None) -> float:
        """
        Calculate cost for tokens
        
        Args:
            model: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: Provider (will search if not specified)
            
        Returns:
            Cost in USD
        """
        if provider:
            prov = self.get_provider(provider)
            if prov:
                return prov.calculate_cost(model, input_tokens, output_tokens)
        else:
            # Find which provider has this model
            for prov in self.providers.values():
                if prov.validate_model(model):
                    return prov.calculate_cost(model, input_tokens, output_tokens)
        
        return 0.0
    
    def test_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Test all available providers
        
        Returns:
            Test results for each provider
        """
        results = {}
        
        test_message = LLMMessage(
            role="user",
            content="Say 'Hello from AI Studio' and nothing else."
        )
        
        for name, provider in self.providers.items():
            try:
                # Get cheapest model for testing
                models = provider.get_available_models()
                cheapest_model = min(models, key=lambda m: m.cost_per_1k_output)
                
                # Send test message
                response = provider.send_message(
                    messages=[test_message],
                    model=cheapest_model.name,
                    max_tokens=20,
                    temperature=0
                )
                
                results[name] = {
                    "status": "success",
                    "model": cheapest_model.name,
                    "response": response.content,
                    "tokens": response.total_tokens,
                    "cost": provider.calculate_cost(
                        cheapest_model.name,
                        response.usage['prompt_tokens'],
                        response.usage['completion_tokens']
                    )
                }
                
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics about available providers
        
        Returns:
            Provider statistics
        """
        stats = {}
        
        for name, provider in self.providers.items():
            models = provider.get_available_models()
            
            stats[name] = {
                "name": provider.get_provider_name(),
                "model_count": len(models),
                "models": [m.display_name for m in models],
                "cheapest_model": min(models, key=lambda m: m.cost_per_1k_output).name if models else None,
                "supports_streaming": any(m.supports_streaming for m in models),
                "supports_functions": any(m.supports_functions for m in models),
                "supports_vision": any(m.supports_vision for m in models),
                "is_current": name == self.current_provider_name
            }
        
        return stats