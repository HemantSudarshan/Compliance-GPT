"""
ComplianceGPT API Package

FastAPI-based REST API for regulatory compliance Q&A.
"""

__all__ = ["app"]


def __getattr__(name: str):
    """Lazy-load the FastAPI app to avoid import-time dependency coupling."""
    if name == "app":
        from api.main import app
        return app
    raise AttributeError(f"module 'api' has no attribute '{name}'")
