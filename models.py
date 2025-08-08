import json 
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any, cast 
from openai.types.chat import ChatCompletionMessageToolCall, ChatCompletionMessageParam

Role = Literal["system", "user", "assistant", "tool", "function", "developer"]
class Chatmsg(BaseModel):
    # role: Role
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None

# Request schema
class ChatRequest(BaseModel):
    session_id: Optional[str] = None                            # Session ID for tracking conversation
    message: str                                                # Client Asked Question
    history: List[Chatmsg] = Field(default_factory=list)    # Chat History From Redis
    n_history: List[ChatCompletionMessageParam] = Field(default_factory=list)    # Chat History From Redis

    def n_Serialize_chat_history(self, chat_history: List[ChatCompletionMessageParam]) -> str:
        """Converts a list of Chatmsg objects to a JSON string."""
        list_of_dicts = []        
        for msg in chat_history:
            
            if msg["role"] == "developer":
                dict_msg = {
                    "role": "developer",
                    "content": msg["content"],
                    "name": msg.get("name", ''),
                }
                list_of_dicts.append(dict_msg)
                
            elif msg["role"] == "system":
                dict_msg = {
                    "role": "system",
                    "content": msg["content"],
                    "name": msg.get("name", ''),
                }
                list_of_dicts.append(dict_msg)
                
            elif msg["role"] == "user":
                dict_msg = {
                    "role": "user",
                    "content": msg["content"],
                    "name": msg.get("name", ''),
                }
                list_of_dicts.append(dict_msg)
                
            elif msg["role"] == "assistant":
                dict_msg: Dict[str, Any] = {
                "role": "assistant"
                }

                # Optional fields
                if "content" in msg and msg["content"] is not None:
                    dict_msg["content"] = msg["content"]

                if "tool_calls" in msg and msg["tool_calls"]:
                    dict_msg["tool_calls"] = [self.serialize_tool_call(tc) for tc in msg["tool_calls"]]

                if "function_call" in msg and msg["function_call"] is not None:
                    # Deprecated, include only if needed
                    dict_msg["function_call"] = msg["function_call"]

                if "audio" in msg and msg["audio"] is not None:
                    dict_msg["audio"] = msg["audio"]

                if "name" in msg and msg["name"] is not None:
                    dict_msg["name"] = msg["name"]

                if "refusal" in msg and msg["refusal"] is not None:
                    dict_msg["refusal"] = msg["refusal"]

                
                list_of_dicts.append(dict_msg)
                
            elif msg["role"] == "tool":
                dict_msg = {
                    "role": "tool",
                    "content": msg["content"],
                    "tool_call_id": msg["tool_call_id"],
                }
                list_of_dicts.append(dict_msg)
                
            elif msg["role"] == "function":
                dict_msg = {
                    "role": "function",
                    "content": msg["content"],
                    "name": msg["name"],
                }
                list_of_dicts.append(dict_msg)
                
            else:
                list_of_dicts.append(dict(msg))
        
        
        return json.dumps({"data":list_of_dicts})
    
    def n_Deserialize_chat_history(self, json_str: str) -> List[Dict[str, Any]]:
        """Converts a JSON string from Redis back into a list of ChatCompletionMessageParam-like dicts."""
        obj = json.loads(json_str)
        chat_list = []

        for msg in obj.get("data", []):
            role = msg.get("role")

            if role == "developer":
                chat_list.append({
                    "role": "developer",
                    "content": msg["content"],
                    "name": msg.get("name"),
                })

            elif role == "system":
                chat_list.append({
                    "role": "system",
                    "content": msg["content"],
                    "name": msg.get("name"),
                })

            elif role == "user":
                chat_list.append({
                    "role": "user",
                    "content": msg["content"],
                    "name": msg.get("name"),
                })

            elif role == "assistant":
                restored: dict[str, Any] = {
                    "role": "assistant"
                }

                if "content" in msg:
                    restored["content"] = msg["content"]

                if "tool_calls" in msg:
                    restored["tool_calls"] = [self.deserialize_tool_call(tc) for tc in msg["tool_calls"]]

                if "audio" in msg:
                    restored["audio"] = msg["audio"]

                if "name" in msg:
                    restored["name"] = msg["name"]

                if "refusal" in msg:
                    restored["refusal"] = msg["refusal"]

                chat_list.append(restored)

            elif role == "tool":
                chat_list.append({
                    "role": "tool",
                    "content": msg["content"],
                    "tool_call_id": msg["tool_call_id"]
                })

            elif role == "function":
                chat_list.append({
                    "role": "function",
                    "content": msg["content"],
                    "name": msg["name"]
                })

            else:
                # Fallback — trust the data if unknown role
                chat_list.append(msg)

        return chat_list

    def serialize_function(self, function: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": function["name"],
            "arguments": function["arguments"]
        }

    def serialize_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": tool_call["id"],
            "type": tool_call["type"],
            "function": self.serialize_function(tool_call["function"])
        }
    
    def deserialize_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": tool_call["id"],
            "type": tool_call["type"],
            "function": {
                "name": tool_call["function"]["name"],
                "arguments": tool_call["function"]["arguments"],
            }
        }

    def append_msg(self,
        role: Role, 
        content: Optional[str] = None,
        tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None,
        
        tool_call_id: Optional[str] = None,
        function_name: Optional[str] = None ) -> None:
        """Append a tool msg to the History Queue."""
        
        if tool_calls :
            tool_msg = Chatmsg(
                role=role,
                tool_calls=tool_calls,
                content=content
            )
            self.history.append(tool_msg)
            
        elif tool_call_id and function_name :
            tool_msg = Chatmsg(
                role=role,
                tool_call_id=tool_call_id,                
                name=function_name,
                content=content
            )
            self.history.append(tool_msg)
        else:
            msg = Chatmsg(
                role=role,
                content=content
            )
            self.history.append(msg)
            
        return

    @staticmethod
    def format_chat_msg(msg: Chatmsg): # -> ChatCompletionmsgParam
        base = {
            "role": msg.role,
            "content": msg.content,
        }

        if msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
            base["tool_calls"] = msg.tool_calls  # Should be a List[ChatCompletionmsgToolCall]
            base["content"] = msg.content  # Must be null if tool_calls present

        elif msg.role == "tool":
            base.update({
                "tool_call_id": msg.tool_call_id,
                "name": msg.name,
            })

        # return cast(ChatCompletionmsgParam, base)
        return base
    
    @property
    def openai_msgs(self) -> List[ChatCompletionMessageParam]:
        """Return full OpenAI-compatible msg list including history and user input."""
        history = self.history or []
        # print(history)
        messages = []
        if not self.history:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in history:
            messages.append(self.format_chat_msg(msg))
        # try:
        #     print("vector_review_prompt :","len(history) > 2",len(history) > 1, "history[-1].role", history[-1].role if history else None)
        #     if len(history) > 1 and history[-1].role == "tool":
        #         msgs.append({"role": "system", "content": self.vector_review_prompt})
        # except IndexError:
        #     # If history is empty, we don't need to append the vector review prompt
        #     pass
        
        messages.append( {"role": "user", "content": self.message.strip()})   
        return cast(List[ChatCompletionMessageParam], messages)
    
    @staticmethod
    def extract_chat_history(json_string) -> List[Chatmsg]:
        """Converts a JSON string back into a list of Chatmsg objects."""
        # list_of_dicts = json.loads(json_string)
        list_of_dicts = json_string.get("data", [])  # Handle both format
        return [Chatmsg(**d) for d in list_of_dicts]
    
    @staticmethod
    def Serialize_chat_history(chat_history: List[ChatCompletionMessageParam]) -> str:
        """Converts a list of Chatmsg objects to a JSON string."""
        # Use Pydantic's model_dump to convert each object to a dictionary
        list_of_dicts = []
        
        for msg in chat_history:
            if msg["role"] == "tool" or msg["role"] == "function" or msg["role"] == "developer":
                continue
                # Convert tool_calls to a list of dictionaries
            elif msg["role"] == "assistant":
                if msg["content"] is None: # type: ignore
                    continue
            else:
                list_of_dicts.append(dict(msg))
        # Then use json.dumps to get the final JSON string
        return json.dumps({"data":list_of_dicts})

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

# Response schema
class ChatResponse(BaseModel):
    reply: str | List[Dict[str, Any]]
    history: list = Field(default_factory=list)
    session_id: Optional[str] = None