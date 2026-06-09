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

def call_llm_structured(
    messages: list[dict[str, str]],
    response_model: Type[T],
    system_prompt: str | None = None
) -> T | None:
    """Dispatches messages to OpenAI or Groq (Option 2) depending on which API key is available."""
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    
    if not openai_key and not groq_key:
        return None
        
    try:
        from openai import OpenAI  # pyrefly: ignore [missing-import]
        
        if groq_key:
            client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1"
            )
            # Use Llama 3.3 70b on Groq
            model = "llama-3.3-70b-versatile"
        else:
            client = OpenAI(api_key=openai_key)
            model = "gpt-4o-mini"
            
        full_messages: list[dict[str, Any]] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        # Cast messages to the OpenAI SDK's expected type.
        # At runtime these are plain dicts with "role" and "content" keys,
        # which the SDK accepts — the cast just satisfies the type checker.
        typed_messages = cast(Any, full_messages)

        if not groq_key:
            # Standard OpenAI parsing
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=typed_messages,
                response_format=response_model,
            )
            return completion.choices[0].message.parsed
        else:
            # Groq JSON mode logic
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
        # Graceful fallback to deterministic/heuristic generators in case of API failure
        print(f"Structured LLM Call failed: {exc}")
        return None
