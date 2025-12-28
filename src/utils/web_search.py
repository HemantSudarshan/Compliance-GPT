"""
web_search.py - Enhanced Web Search for ComplianceGPT

Provides curated web search with compliance-specific sources.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Curated compliance resources
TRUSTED_SOURCES = {
    "ico.org.uk": {"name": "UK ICO", "icon": "🇬🇧", "type": "Regulatory Authority"},
    "edpb.europa.eu": {"name": "EDPB", "icon": "🇪🇺", "type": "EU Data Protection Board"},
    "gdpr-info.eu": {"name": "GDPR Info", "icon": "📖", "type": "Reference"},
    "oag.ca.gov": {"name": "CA Attorney General", "icon": "🇺🇸", "type": "Regulatory Authority"},
    "nist.gov": {"name": "NIST", "icon": "🔒", "type": "Security Framework"},
    "enisa.europa.eu": {"name": "ENISA", "icon": "🛡️", "type": "Security Agency"},
    "iapp.org": {"name": "IAPP", "icon": "📚", "type": "Privacy Association"},
    "eur-lex.europa.eu": {"name": "EUR-Lex", "icon": "⚖️", "type": "Official Law"},
}


@dataclass
class SearchResult:
    """Web search result with metadata."""
    title: str
    url: str
    snippet: str
    source_name: str = "Web"
    source_icon: str = "🔗"
    source_type: str = "General"
    is_trusted: bool = False


def get_source_info(url: str) -> tuple[str, str, str, bool]:
    """Get source information from URL."""
    for domain, info in TRUSTED_SOURCES.items():
        if domain in url.lower():
            return info["name"], info["icon"], info["type"], True
    return "Web Source", "🔗", "General", False


def search_web(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Search the web for compliance information.
    
    Falls back to curated resources if search fails.
    """
    try:
        from duckduckgo_search import DDGS
        
        results = []
        
        # Simple query without site restrictions (faster)
        enhanced_query = f"{query} GDPR compliance official"
        
        with DDGS(timeout=5) as ddg:
            for r in ddg.text(enhanced_query, max_results=max_results):
                url = r.get("href", "")
                name, icon, stype, trusted = get_source_info(url)
                
                results.append(SearchResult(
                    title=r.get("title", "")[:80],
                    url=url,
                    snippet=r.get("body", "")[:250],
                    source_name=name,
                    source_icon=icon,
                    source_type=stype,
                    is_trusted=trusted
                ))
        
        # Sort: trusted sources first
        results.sort(key=lambda x: (not x.is_trusted, x.title))
        
        logger.info(f"Found {len(results)} web results")
        return results[:max_results]
        
    except Exception as e:
        logger.warning(f"Web search failed: {e}, using fallback resources")
        return get_fallback_resources(query)


def get_fallback_resources(query: str) -> list[SearchResult]:
    """Provide curated fallback resources when search fails."""
    query_lower = query.lower()
    
    resources = []
    
    if "gdpr" in query_lower or "data" in query_lower or "privacy" in query_lower:
        resources.extend([
            SearchResult(
                title="ICO Guide to GDPR",
                url="https://ico.org.uk/for-organisations/guide-to-data-protection/guide-to-the-general-data-protection-regulation-gdpr/",
                snippet="Comprehensive guide from the UK's data protection authority covering all aspects of GDPR compliance.",
                source_name="UK ICO", source_icon="🇬🇧", source_type="Regulatory Authority", is_trusted=True
            ),
            SearchResult(
                title="EDPB Guidelines & Recommendations",
                url="https://edpb.europa.eu/our-work-tools/general-guidance/guidelines-recommendations-best-practices_en",
                snippet="Official guidance from the European Data Protection Board on GDPR interpretation.",
                source_name="EDPB", source_icon="🇪🇺", source_type="EU Data Protection Board", is_trusted=True
            ),
            SearchResult(
                title="GDPR.info - Full Regulation Text",
                url="https://gdpr-info.eu/",
                snippet="Complete GDPR text with article-by-article explanations and recitals.",
                source_name="GDPR Info", source_icon="📖", source_type="Reference", is_trusted=True
            ),
        ])
    
    if "ccpa" in query_lower or "california" in query_lower or "consumer" in query_lower:
        resources.append(SearchResult(
            title="California Attorney General - CCPA",
            url="https://oag.ca.gov/privacy/ccpa",
            snippet="Official CCPA regulations, FAQs, and enforcement information from the CA Attorney General.",
            source_name="CA AG", source_icon="🇺🇸", source_type="Regulatory Authority", is_trusted=True
        ))
    
    if "security" in query_lower or "encryption" in query_lower or "technical" in query_lower:
        resources.append(SearchResult(
            title="NIST Cybersecurity Framework",
            url="https://www.nist.gov/cyberframework",
            snippet="Industry-standard security framework for implementing appropriate technical measures.",
            source_name="NIST", source_icon="🔒", source_type="Security Framework", is_trusted=True
        ))
    
    return resources[:4]


def format_web_results(results: list[SearchResult]) -> str:
    """Format web results with better styling."""
    if not results:
        return ""
    
    # Count trusted sources
    trusted_count = sum(1 for r in results if r.is_trusted)
    
    formatted = "\n\n---\n\n"
    formatted += "🌐 **Additional Resources**"
    if trusted_count > 0:
        formatted += f" ({trusted_count} from official sources)"
    formatted += "\n\n"
    
    for r in results:
        # Trusted badge
        badge = "✅ " if r.is_trusted else ""
        
        formatted += f"**{r.source_icon} [{r.title}]({r.url})**\n"
        formatted += f"   {badge}*{r.source_name}* — {r.snippet}\n\n"
    
    formatted += "---\n"
    formatted += "*💡 Tip: For definitive answers, always consult the official regulation text or your Data Protection Officer.*"
    
    return formatted


def enhance_response_with_web(
    original_response: str,
    query: str,
    has_local_context: bool
) -> str:
    """
    Enhance a response with web search results if needed.
    """
    # Trigger phrases that indicate more info could be helpful
    trigger_phrases = [
        "cannot find sufficient information",
        "not contain enough information",
        "no relevant context",
        "outside the scope",
        "require additional",
        "specialized guidance",
        "consult with"
    ]
    
    needs_web_search = any(phrase in original_response.lower() for phrase in trigger_phrases)
    
    # Also trigger for complex topics
    complex_topics = ["ml ", "machine learning", "ai ", "artificial intelligence", 
                      "cloud", "cross-border", "international", "biometric"]
    is_complex = any(topic in query.lower() for topic in complex_topics)
    
    if not needs_web_search and not is_complex and has_local_context:
        return original_response
    
    # Perform web search
    web_results = search_web(query, max_results=3)
    
    if web_results:
        web_section = format_web_results(web_results)
        return original_response + web_section
    
    return original_response


# Quick test
if __name__ == "__main__":
    print("Testing enhanced web search...")
    results = search_web("GDPR biometric data requirements")
    
    print(f"\nFound {len(results)} results:\n")
    for r in results:
        trust = "✅ TRUSTED" if r.is_trusted else ""
        print(f"{r.source_icon} {r.source_name} {trust}")
        print(f"   {r.title}")
        print(f"   {r.url}")
        print()
