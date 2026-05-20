from openai import OpenAI

from app.application.interfaces.llm import LLMProvider
from app.domain.models.llm import LLMCompletionResult, LLMUsage


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str | None, model: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, message: str, system_prompt: str) -> LLMCompletionResult:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
        )
        usage = getattr(response, "usage", None)
        return LLMCompletionResult(
            text=response.output_text,
            model=self.model,
            usage=LLMUsage(
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            ),
        )
