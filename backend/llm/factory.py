from backend import config
from backend.llm.provider import LLMProvider
from backend.llm.openai_provider import OpenAIProvider


def create_llm_provider() -> LLMProvider:
    if config.LLM_PROVIDER == "openai":
        return OpenAIProvider()
    raise ValueError(f"Unknown LLM provider: {config.LLM_PROVIDER}")
