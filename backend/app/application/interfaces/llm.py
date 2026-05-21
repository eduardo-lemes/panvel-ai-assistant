from abc import ABC, abstractmethod

from app.domain.models.llm import LLMCompletionResult


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        message: str,
        system_prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> LLMCompletionResult:
        """Return a model completion for the given user message, optionally with conversation history."""

