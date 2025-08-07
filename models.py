from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any, cast 
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
Role = Literal["system", "user", "assistant", "tool", "function", "developer"]

class ChatMessage(BaseModel):
    # role: Role
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None


# Request schema
class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    
    @property
    def system_prompt(self) -> str:
        return (
            "You are a helpful assistant developed by Digilog (https://digilog.pk/). "
            "You can read and recommend products from the Digilog Shopify store. Respond only in text. "
            "Do not access or process personal data or company private details. "
            "If asked for such data, respond with 'Not eligible.'"
        )
        
    @property
    def vector_review_prompt(self) -> str:
        return """
            Carefully examine the retrieved product data chunks from the vector database.

            Do NOT assume that the highest similarity score means the product is relevant.
            Vector similarity can return partially related or misleading results, so you must:

            1. Fully understand the user's query and intent.
            2. Critically evaluate each product chunk and determine if it directly addresses the user's needs.
            3. Ignore or deprioritize chunks that are top-ranked but irrelevant to the query.
            4. Once the best match is identified, use its `metadata.handle` field to fetch complete and up-to-date product data for a richer, more immersive response.
            5. Use get_product_via_handle function on all relevant products to fetch their all data.

            Only recommend or describe products that you're confident are genuinely aligned with the user's goal.
        """
        
    @staticmethod
    def format_chat_message(msg: ChatMessage): # -> ChatCompletionMessageParam
        base = {
            "role": msg.role,
            "content": msg.content,
        }

        if msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
            base["tool_calls"] = msg.tool_calls  # Should be a List[ChatCompletionMessageToolCall]
            base["content"] = None  # Must be null if tool_calls present

        elif msg.role == "tool":
            base.update({
                "tool_call_id": msg.tool_call_id,
                "name": msg.name,
            })

        # return cast(ChatCompletionMessageParam, base)
        return base
    
    @property
    def openai_messages(self) -> List[ChatCompletionMessageParam]:
        """Return full OpenAI-compatible message list including history and user input."""
        history = self.history or []
        # print(history)
        messages = [{"role": "system", "content": self.system_prompt}]
        
        for msg in history:
            messages.append(self.format_chat_message(msg))
        # try:
        #     print("vector_review_prompt :","len(history) > 2",len(history) > 1, "history[-1].role", history[-1].role if history else None)
        #     if len(history) > 1 and history[-1].role == "tool":
        #         messages.append({"role": "system", "content": self.vector_review_prompt})
        # except IndexError:
        #     # If history is empty, we don't need to append the vector review prompt
        #     pass
        
        messages.append( {"role": "user", "content": self.message.strip()})   
        

        return cast(List[ChatCompletionMessageParam], messages)
    
    def append_message(self,
        role: Role, 
        content: Optional[str] = None,
        tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None,
        tool_call_id: Optional[str] = None,
        function_name: Optional[str] = None ) -> None:
        """Append a tool message to the History Queue."""
        
        if tool_calls :
            tool_msg = ChatMessage(
                role=role,
                tool_calls=tool_calls,
                content=content
            )
            self.history.append(tool_msg)
            
        elif tool_call_id and function_name :
            tool_msg = ChatMessage(
                role=role,
                tool_call_id=tool_call_id,                
                name=function_name,
                content=content
            )
            self.history.append(tool_msg)
        else:
            msg = ChatMessage(
                role=role,
                content=content
            )
            self.history.append(msg)

# Response schema
class ChatResponse(BaseModel):
    reply: str | List[Dict[str, Any]]
    history: List[ChatCompletionMessageParam] = Field(default_factory=list)