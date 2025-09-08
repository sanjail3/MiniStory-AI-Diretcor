import os
from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel
from langchain_community.llms.replicate import Replicate

# Add Gemini provider
llm_providers = {
    "gpt": "openai",
    "claude": "anthropic",
    "gemini": "google_genai",
}


def get_llm_model(model_name: str, model_args: dict = None, **kwargs) -> BaseChatModel:

    def get_provider():
        # Replicate models are detected by having "/" in the name
        if "/" in model_name:
            return "replicate"

        # Match provider keywords
        provider = [
            value for key, value in llm_providers.items() if key in model_name.lower()
        ]
        if provider:
            return provider[0]

        raise ValueError(f"Unable to detect provider for model: {model_name}")

    provider = get_provider().lower()
    model_args = model_args or {}

    # Handle Replicate
    if provider == "replicate":
        if not (
            "replicate_api_token" in kwargs
            or any("replicate_api_token" in key.lower() for key in os.environ)
        ):
            raise ValueError("replicate_api_token not provided in kwargs or environment")

        return Replicate(model=model_name, **model_args, **kwargs)

    # Handle OpenAI, Anthropic, Gemini (via init_chat_model)
    if not (
        any("api_key" in key.lower() for key in kwargs.keys())
        or any("api_key" in key.lower() for key in os.environ)
    ):
        raise ValueError(f"API key not provided for provider: {provider}")

    return init_chat_model(
        model=model_name,
        model_provider=provider,
        **model_args,
        **kwargs,
    )
