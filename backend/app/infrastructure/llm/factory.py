from app.application.interfaces.llm import LLMProvider
from app.infrastructure.config.settings import Settings
from app.infrastructure.llm.mock_provider import MockLLMProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    provider_name = settings.llm_provider.lower()
    if provider_name == "mock":
        return MockLLMProvider(model=settings.llm_model)
    if provider_name == "openai":
        from app.infrastructure.llm.openai_provider import OpenAILLMProvider

        return OpenAILLMProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
