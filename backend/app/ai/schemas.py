from pydantic import BaseModel, Field


class AIRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=8000)


class AIResponse(BaseModel):
    content: str
    model: str
    provider: str


class StructuredAIResponse(BaseModel):
    answer: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
