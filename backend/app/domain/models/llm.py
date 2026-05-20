from pydantic import BaseModel


class LLMUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class LLMCompletionResult(BaseModel):
    text: str
    model: str
    usage: LLMUsage = LLMUsage()
