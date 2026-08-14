import json
import re
import sys
import time
from pathlib import Path

from openai import APIConnectionError, APIError, APITimeoutError, AuthenticationError, OpenAI, PermissionDeniedError, RateLimitError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings


def _extract_json_object(raw_text: str) -> dict:
    text = str(raw_text or "").strip()
    if not text:
        raise RuntimeError("LLM JSON check returned empty content.")

    # Handle fenced payloads first.
    if "```" in text:
        fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
        for block in reversed(fenced):
            candidate = block.strip()
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

    # Fallback: decode the first JSON object embedded in mixed text.
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    raise RuntimeError("LLM JSON check did not return a valid JSON object.")


def _build_client() -> OpenAI:
    api_key = settings.LLM_API_KEY
    if not api_key:
        raise RuntimeError("No LLM API key configured. Set DEEPSEEK_API_KEY.")

    return OpenAI(
        api_key=api_key,
        base_url=settings.LLM_BASE_URL,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=0,
    )


def _create_completion(client: OpenAI, **kwargs):
    max_retries = max(1, int(settings.LLM_MAX_RETRIES or 1))
    last_error = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except (AuthenticationError, PermissionDeniedError) as exc:
            raise RuntimeError("LLM authentication failed. Check DEEPSEEK_API_KEY permissions and validity.") from exc
        except RateLimitError as exc:
            last_error = exc
            if attempt >= max_retries - 1:
                raise RuntimeError("LLM rate limit exceeded during connectivity checks.") from exc
            wait_seconds = min(15 * (attempt + 1), 60)
            print(f"[check_llm] rate limited, retrying in {wait_seconds}s", flush=True)
            time.sleep(wait_seconds)
        except (APIConnectionError, APITimeoutError) as exc:
            last_error = exc
            if attempt >= max_retries - 1:
                raise RuntimeError("LLM connectivity check timed out after retries.") from exc
            print(f"[check_llm] connection timed out on attempt {attempt + 1}, retrying", flush=True)
            time.sleep(min(2 ** attempt, 4))
        except APIError as exc:
            last_error = exc
            if attempt >= max_retries - 1:
                raise RuntimeError(f"LLM connectivity check failed after retries: {exc}") from exc
            print(f"[check_llm] API error on attempt {attempt + 1}, retrying", flush=True)
            time.sleep(min(2 ** attempt, 4))

    raise RuntimeError("LLM connectivity check failed without a recoverable response.") from last_error


def run_checks() -> dict[str, object]:
    client = _build_client()

    chat_completion = _create_completion(
        client,
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with exactly: pong"},
        ],
    )
    chat_content = (chat_completion.choices[0].message.content or "").strip()
    if not chat_content:
        raise RuntimeError("LLM plain-text check returned empty content.")

    json_completion = _create_completion(
        client,
        model=settings.LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Return a JSON object with exactly two fields: "
                    '{"status":"ok","lang":"zh"}'
                ),
            },
            {"role": "user", "content": "Generate the JSON object now."},
        ],
        response_format={"type": "json_object"},
    )
    json_content = json_completion.choices[0].message.content or ""
    parsed_json = _extract_json_object(json_content)

    return {
        "llm_ready": True,
        "model": settings.LLM_MODEL,
        "plain_text_sample": chat_content,
        "json_mode_sample": parsed_json,
    }


def main() -> None:
    result = run_checks()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
