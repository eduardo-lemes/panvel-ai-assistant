from app.application.interfaces.llm import LLMProvider
from app.domain.models.llm import LLMCompletionResult, LLMUsage


class MockLLMProvider(LLMProvider):
    def __init__(self, model: str) -> None:
        self.model = model

    def complete(self, message: str, system_prompt: str) -> LLMCompletionResult:
        del system_prompt
        text = (
            f"Resposta simulada para '{message}'. "
            "A integracao com RAG, tools e chamadas de modelo real sera evoluida nas proximas etapas."
        )
        input_tokens = len(message.split())
        output_tokens = len(text.split())
        return LLMCompletionResult(
            text=text,
            model=self.model,
            usage=LLMUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
        )
