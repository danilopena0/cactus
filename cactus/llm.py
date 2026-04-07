import json
import os
import re
from pathlib import Path

from groq import Groq
from pydantic import BaseModel

# Models — mirror banyan's primary/fallback pattern
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "llama-3.3-70b-versatile")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "llama-3.1-8b-instant")
VISION_MODEL = os.getenv("VISION_MODEL", "llama-3.2-11b-vision-preview")

SCHEMA_PATH = Path(__file__).parent.parent / "schema.md"
_TEMPERATURE = 0.1


def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable not set. "
            "Export it before running cactus."
        )
    return Groq(api_key=api_key)


def load_schema() -> str:
    if SCHEMA_PATH.exists():
        return SCHEMA_PATH.read_text(encoding="utf-8")
    return ""


def call_llm(
    *,
    system: str,
    messages: list[dict],
    max_tokens: int = 8000,
    stream_callback=None,
    model: str = PRIMARY_MODEL,
) -> str:
    """Call the LLM and return the response text. Optionally stream chunks."""
    client = get_client()
    groq_messages = [{"role": "system", "content": system}] + messages

    try:
        if stream_callback is not None:
            stream = client.chat.completions.create(
                model=model,
                messages=groq_messages,
                max_tokens=max_tokens,
                temperature=_TEMPERATURE,
                stream=True,
            )
            parts = []
            for chunk in stream:
                text = chunk.choices[0].delta.content or ""
                if text:
                    parts.append(text)
                    stream_callback(text)
            return "".join(parts)
        else:
            response = client.chat.completions.create(
                model=model,
                messages=groq_messages,
                max_tokens=max_tokens,
                temperature=_TEMPERATURE,
            )
            return response.choices[0].message.content or ""
    except Exception as e:
        if model != FALLBACK_MODEL:
            # Retry with fallback model
            return call_llm(
                system=system,
                messages=messages,
                max_tokens=max_tokens,
                stream_callback=stream_callback,
                model=FALLBACK_MODEL,
            )
        raise


def call_llm_structured(
    *,
    system: str,
    messages: list[dict],
    output_format: type[BaseModel],
    max_tokens: int = 8000,
    model: str = PRIMARY_MODEL,
) -> BaseModel:
    """Call the LLM and parse the response into a Pydantic model via JSON mode."""
    schema = output_format.model_json_schema()
    json_instruction = (
        "\n\nRespond with a valid JSON object matching this exact schema. "
        "Output ONLY the JSON object — no markdown fences, no other text.\n"
        f"Schema:\n{json.dumps(schema, indent=2)}"
    )

    patched = list(messages)
    last = patched[-1]
    if isinstance(last["content"], str):
        patched[-1] = {**last, "content": last["content"] + json_instruction}
    elif isinstance(last["content"], list):
        content = list(last["content"])
        for i in reversed(range(len(content))):
            if content[i].get("type") == "text":
                content[i] = {**content[i], "text": content[i]["text"] + json_instruction}
                break
        patched[-1] = {**last, "content": content}

    client = get_client()
    groq_messages = [{"role": "system", "content": system}] + patched

    try:
        response = client.chat.completions.create(
            model=model,
            messages=groq_messages,
            max_tokens=max_tokens,
            temperature=_TEMPERATURE,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
    except Exception:
        if model != FALLBACK_MODEL:
            return call_llm_structured(
                system=system,
                messages=messages,
                output_format=output_format,
                max_tokens=max_tokens,
                model=FALLBACK_MODEL,
            )
        raise

    # Strip markdown fences if the model ignored the instruction
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if fence:
        raw = fence.group(1)
    else:
        raw = raw.strip()
        if not raw.startswith("{"):
            start = raw.find("{")
            if start != -1:
                raw = raw[start:]

    return output_format.model_validate_json(raw)
