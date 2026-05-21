from collections.abc import Iterator
from openai import OpenAI

from app.application.interfaces.llm import LLMProvider
from app.domain.models.llm import LLMCompletionResult, LLMUsage


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str | None, model: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(
        self,
        message: str,
        system_prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> LLMCompletionResult:
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        response = self.client.responses.create(
            model=self.model,
            input=messages,
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

    def stream(
        self,
        message: str,
        system_prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> Iterator[str]:
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    yield content
