"""
check_setup.py - System Health Check Script

Validates that all components are properly configured.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")


def check_mark(success: bool) -> str:
    """Return checkmark or X based on success."""
    return "✅" if success else "❌"


def check_python_version() -> bool:
    """Check Python version is 3.11+."""
    major, minor = sys.version_info[:2]
    return major >= 3 and minor >= 11


def check_env_file() -> bool:
    """Check if .env file exists."""
    return (project_root / ".env").exists()


def check_llm_provider() -> tuple[bool, str]:
    """Check LLM provider configuration."""
    provider = os.getenv("LLM_PROVIDER", "").lower()
    
    if not provider:
        return False, "LLM_PROVIDER not set"
    
    key_map = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY"
    }
    
    if provider not in key_map:
        return False, f"Unknown provider: {provider}"
    
    key = os.getenv(key_map[provider], "")
    if not key or key.startswith("your-"):
        return False, f"Missing/invalid {key_map[provider]}"
    
    return True, f"{provider} configured"


def check_weaviate() -> tuple[bool, str]:
    """Check Weaviate configuration."""
    url = os.getenv("WEAVIATE_URL", "")
    key = os.getenv("WEAVIATE_API_KEY", "")
    
    if not url or url.startswith("your-"):
        return False, "WEAVIATE_URL not set"
    
    if not key or key.startswith("your-"):
        return False, "WEAVIATE_API_KEY not set"
    
    return True, "Weaviate configured"


def check_weaviate_connection() -> tuple[bool, str]:
    """Test actual Weaviate connection."""
    try:
        from src.storage.weaviate_client import WeaviateClient
        
        with WeaviateClient() as client:
            health = client.health_check()
            
        if health.get("status") == "healthy":
            count = health.get("object_count", 0)
            return True, f"Connected ({count} chunks indexed)"
        else:
            return False, "Connection unhealthy"
            
    except Exception as e:
        return False, f"Connection failed: {str(e)[:50]}"


def check_llm_connection() -> tuple[bool, str]:
    """Test actual LLM connection."""
    try:
        provider = os.getenv("LLM_PROVIDER", "groq").lower()
        
        if provider == "groq":
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=5
            )
            return True, "Groq API working"
            
        elif provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-flash")
            model.generate_content("Say 'OK'")
            return True, "Gemini API working"
            
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=5
            )
            return True, "OpenAI API working"
        
        return False, "Unknown provider"
        
    except Exception as e:
        return False, f"API error: {str(e)[:50]}"


def check_dependencies() -> tuple[bool, str]:
    """Check if required packages are installed."""
    required = [
        "fastapi", "uvicorn", "weaviate", "groq", 
        "pydantic", "dotenv", "tiktoken"
    ]
    
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            # Try alternate names
            alt_names = {"dotenv": "python_dotenv"}
            try:
                __import__(alt_names.get(pkg, pkg))
            except ImportError:
                missing.append(pkg)
    
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    
    return True, "All dependencies installed"


def check_data_directory() -> tuple[bool, str]:
    """Check if data directory structure exists."""
    dirs = ["data/raw", "data/processed", "data/test"]
    
    missing = []
    for d in dirs:
        if not (project_root / d).exists():
            missing.append(d)
    
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    
    return True, "Data directories exist"


def run_checks():
    """Run all system checks."""
    print("\n" + "=" * 60)
    print("🔍 ComplianceGPT System Health Check")
    print("=" * 60 + "\n")
    
    checks = [
        ("Python Version (3.11+)", check_python_version, None),
        (".env File", check_env_file, None),
        ("Dependencies", check_dependencies, None),
        ("Data Directory", check_data_directory, None),
        ("LLM Provider", check_llm_provider, None),
        ("Weaviate Config", check_weaviate, None),
    ]
    
    # Run basic checks
    all_passed = True
    
    for name, check_func, msg_func in checks:
        if msg_func is None:
            result = check_func()
            if isinstance(result, tuple):
                passed, msg = result
            else:
                passed, msg = result, ""
        else:
            passed, msg = check_func()
        
        status = check_mark(passed)
        print(f"  {status} {name}: {msg if msg else ('OK' if passed else 'FAILED')}")
        
        if not passed:
            all_passed = False
    
    # Connection tests (only if config passed)
    print("\n--- Connection Tests ---\n")
    
    llm_ok, llm_msg = check_llm_provider()
    if llm_ok:
        llm_connected, llm_result = check_llm_connection()
        print(f"  {check_mark(llm_connected)} LLM API: {llm_result}")
        if not llm_connected:
            all_passed = False
    else:
        print("  ⏭️ LLM API: Skipped (config missing)")
    
    weaviate_ok, _ = check_weaviate()
    if weaviate_ok:
        wv_connected, wv_result = check_weaviate_connection()
        print(f"  {check_mark(wv_connected)} Weaviate: {wv_result}")
        if not wv_connected:
            all_passed = False
    else:
        print("  ⏭️ Weaviate: Skipped (config missing)")
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All checks passed! System is ready.")
    else:
        print("⚠️ Some checks failed. Please review above.")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_checks())
