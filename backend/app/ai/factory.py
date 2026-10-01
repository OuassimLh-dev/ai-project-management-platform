from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIProvider, ProviderNotConfigured
from app.core.config import Settings


def get_ai_provider(settings: Settings) -> AIProvider:
    if (settings.ai_provider != "openai" or not settings.ai_model.strip()
            or settings.openai_api_key is None or not settings.openai_api_key.get_secret_value().strip()):
        raise ProviderNotConfigured()
    return OpenAIProvider(settings.ai_model.strip(), settings.openai_api_key, settings.ai_timeout_seconds)
