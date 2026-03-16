import os
import json
import logging
from anthropic import Anthropic, APIConnectionError, APITimeoutError, InternalServerError

logger = logging.getLogger(__name__)

def get_client() -> Anthropic:
    """Returns configured Anthropic client. Raises if API key missing."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY nao configurada. "
            "Adicione ao arquivo .env ou exporte como variavel de ambiente."
        )
    return Anthropic(api_key=api_key, timeout=120.0)

def call_claude(system_prompt: str, user_message: str, model: str = "claude-sonnet-4-5-20250929") -> dict:
    """
    Send a message to Claude and parse JSON response.

    Args:
        system_prompt: System prompt with schema context
        user_message: User's natural language question
        model: Claude model ID

    Returns:
        dict with 'sql' and 'explanation' keys

    Raises:
        EnvironmentError: if API key not set
        ValueError: if response cannot be parsed as JSON
    """
    client = get_client()

    max_attempts = 2
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            break
        except (APIConnectionError, APITimeoutError, InternalServerError) as e:
            last_error = e
            if attempt < max_attempts:
                logger.warning("Claude API tentativa %d/%d falhou: %s. Retentando...", attempt, max_attempts, e)
            else:
                logger.error("Claude API falhou apos %d tentativas: %s", max_attempts, e)
                raise
    raw_text = response.content[0].text

    # Try to parse as JSON
    # Claude might wrap in ```json ... ``` markdown
    text = raw_text.strip()
    if text.startswith("```"):
        # Remove markdown code fences
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: treat entire response as SQL
        result = {
            "sql": raw_text.strip(),
            "explanation": "Explicacao nao disponivel (resposta nao estava em formato JSON)."
        }

    return {
        "sql": result.get("sql", ""),
        "explanation": result.get("explanation", ""),
        "raw_response": raw_text,
    }
