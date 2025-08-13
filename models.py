import json 
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any, cast, Mapping, Tuple
from openai.types.chat import ChatCompletionMessageToolCall, ChatCompletionMessageParam, ChatCompletionToolMessageParam,  ChatCompletionMessage, ChatCompletionSystemMessageParam
import re

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
    session_id: Optional[str] = None                            # Session ID for tracking conversation
    message: str                                                # Client Asked Question
    history: List[ChatMessage] = Field(default_factory=list)    # Chat History From Redis
    n_history: List[ChatCompletionMessageParam] = Field(default_factory=list)    # Chat History From Redis
    is_vector_review_prompt_added : bool = False
    is_structural_output_prompt_added : bool = False

    def n_Serialize_chat_history(self, chat_history: List[ChatCompletionMessageParam]) -> str:
        """Converts a list of Chatmsg objects to a JSON string."""
        list_of_dicts = []        
        for msg in chat_history:
            
            if msg["role"] == "developer":
                dict_msg = {
                    "role": "developer",
                    "content": msg["content"],
                }
                list_of_dicts.append(dict_msg)
                
            elif msg["role"] == "system":
                if msg["content"] != self.system_prompt:
                    continue  # Skip system prompts that are not the initial one
                dict_msg = {
                    "role": "system",
                    "content": msg["content"],
                }
                list_of_dicts.append(dict_msg)
                
            elif msg["role"] == "user":
                dict_msg = {
                    "role": "user",
                    "content": msg["content"],
                    "name": msg.get("name", 'Customer'),
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
                msg = self.serialize_tool_response(msg)
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
    
    @staticmethod
    def serialize_tool_response(msg: ChatCompletionToolMessageParam) -> ChatCompletionToolMessageParam:
        msg["content"] = "Only metadata and score are retained; the content is omitted for model efficiency. If you need the content, retrieve it using the tool with metadata.handle."
        return msg
    
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

    def serialize_tool_call(self, tool_call: Mapping[str, Any]) -> Dict[str, Any]:
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

    def load_history(self, session_data: str) -> None:
        self.n_history = cast(
            List[ChatCompletionMessageParam], 
            self.n_Deserialize_chat_history(session_data)
        )
    
    def append_msg(self,
        role: Role, 
        content: Optional[str] = None,
        tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None,
        
        tool_call_id: Optional[str] = None,
        function_name: Optional[str] = None ) -> None:
        """Append a tool msg to the History Queue."""
        
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
            
        return

    @staticmethod
    def format_chat_msg(msg: ChatMessage): # -> ChatCompletionmsgParam
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
    
    def append_tool_response(self, content:str, tool_call_id:str):
        tool_msg: ChatCompletionToolMessageParam = {
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call_id
        }
        self.n_history.append(tool_msg)
    
    def append_vectorDb_prompt(self):
        if self.is_vector_review_prompt_added:
            return
        
        tool_prompt: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": self.vector_review_prompt
        }
        
        self.n_history.append(tool_prompt)
        self.is_vector_review_prompt_added = True
        
    def append_stuctural_output_prompt(self):
        if self.is_structural_output_prompt_added:
            return
        
        tool_prompt: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": self.stuctural_output_prompt
        }
        
        self.n_history.append(tool_prompt)
        self.is_structural_output_prompt_added = True
        
    def append_message(self, data: dict[str, Any]):
        msg_dict = cast(ChatCompletionMessageParam, data)
        self.n_history.append(msg_dict)
    
    @staticmethod
    def extract_product_json_list(text: str) -> Tuple[List[dict[str, Any]], str]:
        _CURRENCY_SYMBOLS = "€£$₹"
        _CURRENCY_CODE = r"[A-Z]{2,5}"

        _price_leading = re.compile(
            rf"^(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])\s*\d+(?:,\d{{3}})*(?:\.\d+)?$"
        )
        _price_trailing = re.compile(
            rf"^\d+(?:,\d{{3}})*(?:\.\d+)?\s*(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])$"
        )

        def _valid_price(s: str) -> bool:
            s = s.strip()
            return bool(_price_leading.match(s) or _price_trailing.match(s))

        def _valid_product(obj: Any) -> bool:
            if not isinstance(obj, dict):
                return False
            required = {"link", "imageurl", "title", "price", "description"}
            if set(obj.keys()) != required:
                return False
            # All single-line strings
            if not all(isinstance(v, str) and "\n" not in v for v in obj.values()):
                return False
            # https links
            if not (obj["link"].startswith("https://") and obj["imageurl"].startswith("https://")):
                return False
            # price format (accepts code/symbol before or after)
            if obj["price"].strip() and not _valid_price(obj["price"]):
                return False
            return True

        # ---------- Text utilities ----------

        def _remove_spans(s: str, spans: List[Tuple[int, int]]) -> str:
            """Remove [start, end) spans from s in one pass."""
            if not spans:
                return s
            spans = sorted(spans)
            out, prev = [], 0
            for a, b in spans:
                out.append(s[prev:a])
                prev = b
            out.append(s[prev:])
            return "".join(out)

        def _find_json_objects(text: str) -> List[Tuple[int, int, str]]:
            """
            Return list of (start, end, json_str) for JSON objects found via brace scanning.
            Ignores braces inside quoted strings and handles escapes.
            """
            results: List[Tuple[int, int, str]] = []
            stack = 0
            in_str = False
            esc = False
            start = -1

            for i, ch in enumerate(text):
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                else:
                    if ch == '"':
                        in_str = True
                    elif ch == "{":
                        if stack == 0:
                            start = i
                        stack += 1
                    elif ch == "}":
                        if stack > 0:
                            stack -= 1
                            if stack == 0 and start != -1:
                                end = i + 1
                                results.append((start, end, text[start:end]))
                                start = -1
            return results

        results: List[dict[str, Any]] = []
        remove_spans: List[Tuple[int, int]] = []

        # 1) First handle fenced ```json blocks
        fenced = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
        for m in fenced.finditer(text):
            raw = m.group(1)
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if _valid_product(obj):
                results.append(obj)
                remove_spans.append((m.start(), m.end()))

        # Remove fenced now so indices for the next pass are clean
        intermediate = _remove_spans(text, remove_spans)

        # 2) Find unfenced JSON objects via brace scanning
        spans2: List[Tuple[int, int]] = []
        for s, e, raw in _find_json_objects(intermediate):
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if _valid_product(obj):
                results.append(obj)
                spans2.append((s, e))

        cleaned_text = _remove_spans(intermediate, spans2).strip()

        if len(cleaned_text) < 100:
            cleaned_text = re.sub(r"\[\s*\]", "",cleaned_text)
            #  += ("\nCheckout the products Below." if cleaned_text else "Checkout the products Below.")

        return results, cleaned_text

    @property
    def n_openai_msgs(self) -> List[ChatCompletionMessageParam]:
        """Return full OpenAI-compatible msg list including history and user input."""
        
        if len(self.n_history) == 0:
            chat = cast(ChatCompletionMessageParam, {"role": "system", "content": self.system_prompt})
            self.n_history.append(chat)
            
        # for msg in history:
        #     messages.append(self.format_chat_msg(msg))
        # try:
        #     print("vector_review_prompt :","len(history) > 2",len(history) > 1, "history[-1].role", history[-1].role if history else None)
        #     if len(history) > 1 and history[-1].role == "tool":
        #         msgs.append({"role": "system", "content": self.vector_review_prompt})
        # except IndexError:
        #     # If history is empty, we don't need to append the vector review prompt
        #     pass
    
        chat = cast(ChatCompletionMessageParam, {"role": "user", "content": self.message.strip()})
        
        copy_history = self.n_history.copy()
        copy_history.append(chat)
        return copy_history
    
    @staticmethod
    def extract_chat_history(json_string) -> List[ChatMessage]:
        """Converts a JSON string back into a list of Chatmsg objects."""
        # list_of_dicts = json.loads(json_string)
        list_of_dicts = json_string.get("data", [])  # Handle both format
        return [ChatMessage(**d) for d in list_of_dicts]
    
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
        return """
            > You are a helpful assistant created by Digilog ([https://digilog.pk/](https://digilog.pk/)).
            > Your role is to read and recommend products from the Digilog Shopify store, providing responses in text only.
            > You must not access, request, or process any personal data or confidential company information.
            > If such information is requested, reply strictly with: **"Not eligible."**
        """
        
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
    
    
    @property
    def stuctural_output_prompt(self) -> str:
        return """
            > You must provide product details **only** in the following JSON structure.
            > **Every field is mandatory.**
            > **No extra fields, no changes to key names, no formatting outside JSON.**
            > If a value is unknown, you must use an empty string (`""`) — do not omit the field.
            > If this exact format is not followed, the system will reject the input and terminate processing.

            ```json
            {
            "link": "https://digilog.pk/products/product-page",
            "imageurl": "https://digilog.pk/cdn/shop/files/product-image.wenbp?v=1234567890&width=1400",
            "title": "Exact Product Title Here",
            "price": "99.99 CurrencyCode",
            "description": "Clear, concise product description here."
            }
            ```

            **Rules**:

            1. `"link"` → Direct URL to the product page (must be a valid HTTPS link).
            2. `"imageurl"` → Direct URL to the product image (must be a valid HTTPS link).
            3. `"title"` → Exact name of the product, no extra words.
            4. `"price"` → Must include currency symbol and numeric value (e.g., `"$19.99"`).
            5. `"description"` → Short, clear, factual description.
            6. **No additional fields** — only the above 5.
            7. **No line breaks inside values** — all values must be single-line strings.

            **Example of VALID input**:

            ```json
            {
            "link": "https://digilog.pk/products/solar-wifi-device-solar-wifi-dongle-in-pakistan",
            "imageurl": "https://digilog.pk/cdn/shop/files/Untitled_design_144dd069-c4ec-4b66-a8f8-0db6cdf38d2e.webp?v=1741255473&width=1400",
            "title": "Inverterzone Solar Wifi Device Solar wifi Dongle In Pakistan",
            "price": "7,500 PKR",
            "description": "The Inverterzone Solar WiFi Dongle is the ultimate solution for solar-powered homes, enabling real-time monitoring, efficient load consumption management, and scheduling of energy usage to maximize solar efficiency"
            }
            ```
        """

# Response schema
class ChatResponse(BaseModel):
    reply: str | List[Dict[str, Any]]
    history: list = Field(default_factory=list)
    products: List[Dict[str, Any]] = []
    session_id: Optional[str] = None