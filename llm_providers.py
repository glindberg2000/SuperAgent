#!/usr/bin/env python3
"""
LLM Provider implementations for different AI models
"""

import json
import httpx
import logging
import asyncio
from typing import List, Dict, Optional
from openai import OpenAI
from xai_sdk import Client as XaiClient

logger = logging.getLogger(__name__)

class LLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, api_key: str, name: str):
        self.api_key = api_key
        self.name = name
    
    async def generate_response(self, messages: List[Dict], system_prompt: str = "") -> str:
        """Generate response from LLM - to be implemented by subclasses"""
        raise NotImplementedError

class Grok4Provider(LLMProvider):
    """Grok4 LLM provider using OpenAI SDK with xAI endpoint"""
    
    def __init__(self, api_key: str, enable_search: bool = True):
        super().__init__(api_key, "grok4")
        # Use OpenAI client with xAI endpoint (more reliable)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )
        self.enable_search = enable_search
    
    async def generate_response(self, messages: List[Dict], system_prompt: str = "") -> str:
        """Generate response using Grok via xAI SDK"""
        
        try:
            # Convert our message format to xAI format
            api_messages = []
            
            if system_prompt:
                api_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Convert conversation history to chat format
            for msg in messages:
                if msg.get('is_bot') and msg.get('agent_name'):
                    role = "assistant"
                else:
                    role = "user"
                
                api_messages.append({
                    "role": role,
                    "content": f"{msg['author']}: {msg['content']}"
                })
            
            # Try different model names that should work with xAI
            models_to_try = ["grok-2-1212", "grok-beta", "grok-2-latest"]
            
            for model_name in models_to_try:
                try:
                    logger.info(f"Trying model: {model_name}")
                    
                    # Use OpenAI client with xAI endpoint with Live Search
                    def sync_call():
                        request_params = {
                            "model": model_name,
                            "messages": api_messages,
                            "temperature": 0.7,
                            "max_tokens": 1000
                        }
                        
                        # Add Live Search if enabled
                        if self.enable_search:
                            request_params["extra_body"] = {
                                "search_parameters": {
                                    "mode": "auto"  # "auto", "on", or "off"
                                }
                            }
                        
                        return self.client.chat.completions.create(**request_params)
                    
                    # Run sync function in thread
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(None, sync_call)
                    
                    content = response.choices[0].message.content
                    
                    # Log search usage if available
                    if hasattr(response, 'usage') and hasattr(response.usage, 'num_sources_used'):
                        logger.info(f"Live Search used {response.usage.num_sources_used} sources")
                    
                    return content
                    
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
                    continue
            
            return "Sorry, I'm having trouble with all Grok models right now. Please try again later."
            
        except Exception as e:
            logger.error(f"Grok4 API exception: {e}")
            return f"Sorry, I'm having trouble connecting to Grok right now. Error: {str(e)}"

class ClaudeProvider(LLMProvider):
    """Claude LLM provider using Anthropic API"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "claude")
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    async def generate_response(self, messages: List[Dict], system_prompt: str = "") -> str:
        """Generate response using Claude via Anthropic API"""
        
        # Convert to Claude message format
        claude_messages = []
        
        for msg in messages:
            if msg.get('is_bot') and msg.get('agent_name'):
                role = "assistant"
            else:
                role = "user"
            
            claude_messages.append({
                "role": role,
                "content": f"{msg['author']}: {msg['content']}"
            })
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "temperature": 0.7,
            "messages": claude_messages
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "x-api-version": "2023-06-01"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["content"][0]["text"]
                else:
                    logger.error(f"Claude API error {response.status_code}: {response.text}")
                    return f"Sorry, I encountered an error communicating with Claude (HTTP {response.status_code})"
                    
        except Exception as e:
            logger.error(f"Claude API exception: {e}")
            return f"Sorry, I'm having trouble connecting to Claude right now. Error: {str(e)}"

class GeminiProvider(LLMProvider):
    """Gemini LLM provider using Google AI API"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "gemini")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    async def generate_response(self, messages: List[Dict], system_prompt: str = "") -> str:
        """Generate response using Gemini via Google AI API"""
        
        # Build conversation context
        context = ""
        if system_prompt:
            context += f"System: {system_prompt}\n\n"
        
        # Add conversation history
        for msg in messages:
            context += f"{msg['author']}: {msg['content']}\n"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": context
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1000,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    logger.error(f"Gemini API error {response.status_code}: {response.text}")
                    return f"Sorry, I encountered an error communicating with Gemini (HTTP {response.status_code})"
                    
        except Exception as e:
            logger.error(f"Gemini API exception: {e}")
            return f"Sorry, I'm having trouble connecting to Gemini right now. Error: {str(e)}"

def create_llm_provider(llm_type: str, api_key: str, **kwargs) -> LLMProvider:
    """Factory function to create appropriate LLM provider"""
    
    if llm_type.lower() == 'grok4':
        enable_search = kwargs.get('enable_search', True)
        return Grok4Provider(api_key, enable_search=enable_search)
    elif llm_type.lower() == 'claude':
        return ClaudeProvider(api_key)
    elif llm_type.lower() == 'gemini':
        return GeminiProvider(api_key)
    else:
        raise ValueError(f"Unsupported LLM type: {llm_type}")