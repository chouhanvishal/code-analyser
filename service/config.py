"""Configuration module for the autonomous code-change service."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    # Model configuration
    model_provider: str = os.getenv("LLM_PROVIDER", "auto")  # "anthropic", "openai", "gemini", "auto"
    model_name: str = os.getenv("LLM_MODEL", "")  # e.g., "claude-3-5-sonnet-20241022", "gpt-4o", "gemini-2.5-flash"
    api_key: str = os.getenv("LLM_API_KEY", "")
    api_base: str = os.getenv("LLM_API_BASE", "")
    
    # Provider-specific API keys fallback
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    
    # Docker Sandbox configuration
    docker_image: str = os.getenv("ACCEPTANCE_IMAGE", "acceptance:latest")
    use_docker: bool = os.getenv("USE_DOCKER", "1").lower() in ("1", "true", "yes")
    
    # Execution & Safety parameters
    max_turns: int = int(os.getenv("MAX_AGENT_TURNS", "25"))
    deadline_safety_buffer_s: float = float(os.getenv("DEADLINE_SAFETY_BUFFER_S", "15.0"))
    test_timeout_s: int = int(os.getenv("TEST_TIMEOUT_S", "60"))
    
    # Port / Host
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    def resolve_provider_and_key(self) -> tuple[str, str, str]:
        """Resolves the active provider, model name, and API key."""
        if self.model_provider != "auto":
            key = self.api_key
            if not key:
                if self.model_provider == "anthropic":
                    key = self.anthropic_api_key
                elif self.model_provider == "openai":
                    key = self.openai_api_key
                elif self.model_provider == "gemini":
                    key = self.gemini_api_key
            model = self.model_name
            if not model:
                if self.model_provider == "anthropic":
                    model = "claude-3-5-sonnet-20241022"
                elif self.model_provider == "openai":
                    model = "gpt-4o"
                elif self.model_provider == "gemini":
                    model = "gemini-2.5-flash"
            return self.model_provider, model, key

        # Auto detection based on available keys
        if self.anthropic_api_key:
            return "anthropic", self.model_name or "claude-3-5-sonnet-20241022", self.anthropic_api_key
        if self.openai_api_key:
            return "openai", self.model_name or "gpt-4o", self.openai_api_key
        if self.gemini_api_key:
            return "gemini", self.model_name or "gemini-2.5-flash", self.gemini_api_key
        if self.api_key:
            return "openai", self.model_name or "gpt-4o", self.api_key

        return "none", "", ""


config = Config()
