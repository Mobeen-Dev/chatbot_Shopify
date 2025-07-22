from pydantic import BaseModel, Field
from typing import Optional, List, Literal, cast
from openai.types.chat import ChatCompletionMessageParam

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str




# Request schema
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = Field(default_factory=list)
    
    @property
    def system_prompt(self) -> str:
        return (
            "You are a helpful assistant developed by Digilog (https://digilog.pk/). "
            "You can read and recommend products from the Digilog Shopify store. Respond only in text. "
            "Do not access or process personal data or company private details. "
            "If asked for such data, respond with 'Not eligible.'"
        )
    
    @property
    def openai_messages(self) -> List[ChatCompletionMessageParam]:
        """Return full OpenAI-compatible message list including history and user input."""
        history = self.history or []
        print(history)
        messages = [
            {"role": "system", "content": self.system_prompt},
            *[{"role": msg.role, "content": msg.content} for msg in history],
            {"role": "user", "content": self.message.strip()},
        ]

        return cast(List[ChatCompletionMessageParam], messages)

# Response schema
class ChatResponse(BaseModel):
    reply: str
    