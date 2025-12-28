"""
config.py - Application Configuration

Loads environment variables and provides configuration dataclass.
Supports multiple LLM providers: OpenAI, Gemini, Groq
"""

import os
from dataclasses import dataclass
from typing import Literal
from dotenv import load_dotenv

load_dotenv()


# Supported LLM providers
LLMProvider = Literal["openai", "gemini", "groq"]


@dataclass
class Config:
    """Application configuration loaded from environment variables."""
    
    # LLM Provider Selection (openai, gemini, groq)
    llm_provider: LLMProvider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    # OpenAI (paid)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Google Gemini (FREE tier: 15 RPM, 1M tokens/day)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # Groq (FREE tier: 30 RPM)
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    
    # Weaviate
    weaviate_url: str = os.getenv("WEAVIATE_URL", "")
    weaviate_api_key: str = os.getenv("WEAVIATE_API_KEY", "")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Model settings per provider
    @property
    def llm_model(self) -> str:
        """Get the LLM model based on provider."""
        models = {
            "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "gemini": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            "groq": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        }
        return models.get(self.llm_provider, models["gemini"])
    
    @property
    def embedding_model(self) -> str:
        """Get the embedding model."""
        return os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    
    # Chunking settings
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    
    # Retrieval settings
    top_k: int = int(os.getenv("TOP_K", "5"))
    hybrid_alpha: float = float(os.getenv("HYBRID_ALPHA", "0.3"))
    
    def get_api_key(self) -> str:
        """Get the API key for the current LLM provider."""
        keys = {
            "openai": self.openai_api_key,
            "gemini": self.gemini_api_key,
            "groq": self.groq_api_key,
        }
        return keys.get(self.llm_provider, "")
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Check LLM API key
        if not self.get_api_key():
            issues.append(f"Missing API key for LLM provider '{self.llm_provider}'. Set {self.llm_provider.upper()}_API_KEY")
        
        # Check Weaviate (optional warning)
        if not self.weaviate_url:
            issues.append("WEAVIATE_URL not set - vector search will not work")
        
        return issues


config = Config()


# Print config status on import (for debugging)
if __name__ == "__main__":
    print("=" * 50)
    print("ComplianceGPT Configuration")
    print("=" * 50)
    print(f"LLM Provider: {config.llm_provider}")
    print(f"LLM Model: {config.llm_model}")
    print(f"API Key Set: {'Yes' if config.get_api_key() else 'No'}")
    print(f"Weaviate URL: {config.weaviate_url or 'Not set'}")
    print(f"Chunk Size: {config.chunk_size}")
    print(f"Hybrid Alpha: {config.hybrid_alpha}")
    
    issues = config.validate()
    if issues:
        print("\n⚠️ Configuration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ Configuration valid!")
