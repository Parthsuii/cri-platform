from __future__ import annotations

import json
import os
from typing import Any, Type, TypeVar, cast
from pydantic import BaseModel  # pyrefly: ignore [missing-import]

T = TypeVar("T", bound=BaseModel)

# Load .env file manually if present
env_path = os.path.join(os.getcwd(), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

def _get_available_providers() -> list[tuple[str, str | None, str]]:
    """Get all active LLM provider configurations in priority order.

    Priority: OpenRouter → Groq → OpenAI.
    Returns list of (api_key, base_url, model).
    """
    providers: list[tuple[str, str | None, str]] = []

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key and openrouter_key != "sk-or-v1-your-key-here":
        providers.append((openrouter_key, "https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free"))

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        providers.append((groq_key, "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"))

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        providers.append((openai_key, None, "gpt-4o-mini"))

    return providers


def call_llm_structured(
    messages: list[dict[str, str]],
    response_model: Type[T],
    system_prompt: str | None = None
) -> T | None:
    """Dispatches messages to the first successful LLM provider.

    Provider priority: OpenRouter (free) → Groq → OpenAI → None.
    If a provider fails (e.g. rate limit, api error), it falls back to the next.
    """
    providers = _get_available_providers()

    if not providers:
        print("No active LLM providers found.")
        return None

    from openai import OpenAI  # pyrefly: ignore [missing-import]

    for api_key, base_url, model in providers:
        provider_name = "OpenRouter" if "openrouter" in (base_url or "") else ("Groq" if "groq" in (base_url or "") else "OpenAI")
        try:
            client_kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            client = OpenAI(**client_kwargs)

            full_messages: list[dict[str, Any]] = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            # Cast messages to the OpenAI SDK's expected type.
            typed_messages = cast(Any, full_messages)

            if not base_url:
                # Standard OpenAI structured-output parsing
                completion = client.beta.chat.completions.parse(
                    model=model,
                    messages=typed_messages,
                    response_format=response_model,
                )
                return completion.choices[0].message.parsed
            else:
                # Groq / OpenRouter — use JSON mode with explicit schema prompt
                json_messages: list[dict[str, Any]] = [
                    {
                        "role": "system",
                        "content": f"You MUST respond ONLY with a raw JSON object matching the JSON Schema: {json.dumps(response_model.model_json_schema())}"
                    },
                    *full_messages,
                ]

                completion = client.chat.completions.create(
                    model=model,
                    messages=cast(Any, json_messages),
                    response_format=cast(Any, {"type": "json_object"}),
                )
                content = completion.choices[0].message.content
                if content:
                    return response_model.model_validate_json(content)
        except Exception as exc:
            print(f"LLM Call via {provider_name} failed: {exc}. Trying next fallback...")
            continue

    # Graceful fallback to deterministic/heuristic generators in case of API failure
    print("All LLM providers failed.")
    return None
