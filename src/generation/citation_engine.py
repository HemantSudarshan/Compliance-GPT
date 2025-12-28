"""
citation_engine.py - Citation-Based Answer Generation

Uses RAG with multiple LLM providers (OpenAI, Gemini, Groq) for grounded answers.
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
env_paths = [
    Path(__file__).parent.parent.parent / ".env",
    Path.cwd() / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)
        break

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import from storage
from src.storage.retriever import HybridRetriever, RetrievalResult
from src.generation.prompts import (
    get_system_prompt,
    format_query_prompt,
    get_no_context_response
)

# Get config values from env
class Config:
    llm_provider = os.getenv("LLM_PROVIDER", "groq").lower()
    top_k = int(os.getenv("TOP_K", "5"))
    hybrid_alpha = float(os.getenv("HYBRID_ALPHA", "0.3"))
    
    @property
    def llm_model(self):
        models = {
            "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "gemini": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            "groq": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        }
        return models.get(self.llm_provider, models["groq"])
    
    def get_api_key(self):
        keys = {
            "openai": os.getenv("OPENAI_API_KEY", ""),
            "gemini": os.getenv("GEMINI_API_KEY", ""),
            "groq": os.getenv("GROQ_API_KEY", ""),
        }
        return keys.get(self.llm_provider, "")

config = Config()


@dataclass
class Citation:
    """Represents a citation to a source document."""
    
    citation_id: int
    text: str
    source_file: str
    page_numbers: list
    regulation: str
    chunk_id: str
    
    def to_dict(self) -> dict:
        return {
            "citation_id": self.citation_id,
            "text": self.text,
            "source_file": self.source_file,
            "page_numbers": self.page_numbers,
            "regulation": self.regulation,
            "chunk_id": self.chunk_id
        }
    
    def format_reference(self) -> str:
        """Format as a readable reference."""
        pages = ", ".join(str(p) for p in self.page_numbers)
        return f"[{self.citation_id}] {self.regulation} - {self.source_file}, Page(s) {pages}"


@dataclass
class CitedResponse:
    """Represents a response with citations."""
    
    answer: str
    citations: list[Citation]
    query: str
    has_context: bool
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "citations": [c.to_dict() for c in self.citations],
            "query": self.query,
            "has_context": self.has_context,
            "metadata": self.metadata
        }
    
    def format_full_response(self) -> str:
        """Format the complete response with sources section."""
        if not self.citations:
            return self.answer
        
        sources_section = "\n\n---\n**Sources:**\n"
        for citation in self.citations:
            sources_section += f"\n{citation.format_reference()}"
        
        return self.answer + sources_section


# =============================================================================
# LLM Provider Classes
# =============================================================================

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        return response.choices[0].message.content


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider (FREE TIER)."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=None  # Will be set per request
        )
        self.model_name = model
    
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        import google.generativeai as genai
        
        # Create model with system instruction
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1500
            )
        )
        
        response = model.generate_content(user_prompt)
        return response.text


class GroqProvider(BaseLLMProvider):
    """Groq provider (FREE TIER)."""
    
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
    
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        return response.choices[0].message.content


def get_llm_provider(
    provider: str = None,
    api_key: str = None,
    model: str = None
) -> BaseLLMProvider:
    """
    Factory function to get the appropriate LLM provider.
    
    Args:
        provider: Provider name (openai, gemini, groq)
        api_key: API key for the provider
        model: Model name override
        
    Returns:
        LLM provider instance
    """
    provider = provider or config.llm_provider
    api_key = api_key or config.get_api_key()
    model = model or config.llm_model
    
    if not api_key:
        raise ValueError(f"No API key found for provider '{provider}'. Check your .env file.")
    
    providers = {
        "openai": lambda: OpenAIProvider(api_key, model),
        "gemini": lambda: GeminiProvider(api_key, model),
        "groq": lambda: GroqProvider(api_key, model),
    }
    
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}. Use: openai, gemini, or groq")
    
    logger.info(f"Using LLM provider: {provider} with model: {model}")
    return providers[provider]()


# =============================================================================
# Citation Engine
# =============================================================================

class CitationEngine:
    """
    Generates answers with citations using RAG.
    
    Retrieves relevant context from Weaviate and generates
    grounded answers using configurable LLM providers.
    """
    
    def __init__(
        self,
        weaviate_client: "WeaviateClient",
        provider: str = None,
        api_key: str = None,
        model: str = None,
        top_k: int = None,
        alpha: float = None
    ):
        """
        Initialize the citation engine.
        
        Args:
            weaviate_client: Connected WeaviateClient instance
            provider: LLM provider (openai, gemini, groq)
            api_key: API key for the provider
            model: Model name
            top_k: Number of chunks to retrieve
            alpha: Hybrid search alpha
        """
        self.weaviate_client = weaviate_client
        self.retriever = HybridRetriever(
            weaviate_client,
            top_k=top_k or config.top_k,
            alpha=alpha if alpha is not None else config.hybrid_alpha
        )
        
        self.llm = get_llm_provider(provider, api_key, model)
        self.system_prompt = get_system_prompt()
        self.provider_name = provider or config.llm_provider
        self.model_name = model or config.llm_model
    
    def query(
        self,
        question: str,
        regulation_filter: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> CitedResponse:
        """
        Answer a compliance question with citations.
        
        Args:
            question: User's question
            regulation_filter: Filter by regulation name
            top_k: Override number of chunks to retrieve
            
        Returns:
            CitedResponse with answer and citations
        """
        logger.info(f"Processing query: {question[:50]}...")
        
        # Step 1: Retrieve relevant context
        results = self.retriever.search(
            query=question,
            top_k=top_k,
            regulation_filter=regulation_filter
        )
        
        if not results:
            logger.info("No context found for query")
            return CitedResponse(
                answer=get_no_context_response(),
                citations=[],
                query=question,
                has_context=False
            )
        
        # Step 2: Build context and citations
        context, citations = self._build_context(results)
        
        # Step 3: Generate answer
        answer = self._generate_answer(question, context)
        
        return CitedResponse(
            answer=answer,
            citations=citations,
            query=question,
            has_context=True,
            metadata={
                "provider": self.provider_name,
                "model": self.model_name,
                "num_sources": len(citations),
                "regulation_filter": regulation_filter
            }
        )
    
    def _build_context(
        self,
        results: list
    ) -> tuple[str, list[Citation]]:
        """Build context string and citation list from retrieval results."""
        context_parts = []
        citations = []
        
        for i, result in enumerate(results, 1):
            citation = Citation(
                citation_id=i,
                text=result.text[:500] + "..." if len(result.text) > 500 else result.text,
                source_file=result.source_file,
                page_numbers=result.page_numbers,
                regulation=result.regulation,
                chunk_id=result.chunk_id
            )
            citations.append(citation)
            
            pages = ", ".join(str(p) for p in result.page_numbers)
            context_parts.append(
                f"[{i}] Source: {result.regulation} - {result.source_file}, Page(s) {pages}\n"
                f"{result.text}\n"
            )
        
        context = "\n---\n".join(context_parts)
        return context, citations
    
    def _generate_answer(self, question: str, context: str) -> str:
        """Generate an answer using the configured LLM."""
        prompt = format_query_prompt(context, question)
        
        try:
            answer = self.llm.generate(self.system_prompt, prompt)
            logger.info(f"Generated answer with {len(answer)} characters")
            
            # Add web search fallback if answer indicates insufficient info
            try:
                from src.utils.web_search import enhance_response_with_web
                answer = enhance_response_with_web(answer, question, has_local_context=True)
            except ImportError:
                pass  # Web search not available
            except Exception as e:
                logger.warning(f"Web search enhancement failed: {e}")
            
            return answer
            
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return f"Error generating answer: {e}"


def answer_compliance_question(
    question: str,
    regulation: Optional[str] = None,
    provider: str = None,
    api_key: str = None,
    weaviate_url: Optional[str] = None,
    weaviate_api_key: Optional[str] = None
) -> CitedResponse:
    """
    Convenience function to answer a compliance question.
    
    Args:
        question: User's question
        regulation: Optional regulation filter
        provider: LLM provider (openai, gemini, groq)
        api_key: LLM API key
        weaviate_url: Optional Weaviate URL
        weaviate_api_key: Optional Weaviate API key
        
    Returns:
        CitedResponse with answer and citations
    """
    from src.storage.weaviate_client import WeaviateClient
    
    with WeaviateClient(url=weaviate_url, api_key=weaviate_api_key) as client:
        engine = CitationEngine(client, provider=provider, api_key=api_key)
        return engine.query(question, regulation_filter=regulation)


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        
        print(f"Provider: {config.llm_provider}")
        print(f"Model: {config.llm_model}")
        print(f"Question: {question}\n")
        print("=" * 60)
        
        try:
            response = answer_compliance_question(question)
            print(response.format_full_response())
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python citation_engine.py <question>")
        print("\nConfigure LLM in .env:")
        print("  LLM_PROVIDER=gemini  (free)")
        print("  GEMINI_API_KEY=your-key")
