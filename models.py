import re
import json
from dataclasses import dataclass
from utils.PromptManager import PromptManager
from pydantic import BaseModel, Field, PrivateAttr
from typing import Optional, List, Literal, Dict, Any, cast, Mapping, Tuple
from openai.types.chat import (
    ChatCompletionMessageToolCall,
    ChatCompletionToolMessageParam,
    ChatCompletionSystemMessageParam,
)
from openai.types.responses.response_input_param import FunctionCallOutput
from openai.types.responses.response_input_param import ResponseInputItemParam
from openai.types.responses.response_custom_tool_call_param import (
    ResponseCustomToolCallParam,
)
from openai.types.responses.response_input_param import ResponseInputParam
from openai.types.responses.easy_input_message_param import EasyInputMessageParam

Role = Literal["system", "user", "assistant", "tool", "function", "developer"]


class ChatMessage(BaseModel):
    # role: Role
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None


# Response schema
class ChatResponse(BaseModel):
    reply: str | List[Dict[str, Any]]
    history: list = Field(default_factory=list)
    stuctural_data: List[dict[str, Any]] = []
    session_id: Optional[str] = None
    cart_id: Optional[str] = None


@dataclass
class ProductEntry:
    have_single_variant: bool
    variants: dict[str, dict[str, str]]
    # "Large": {
    #    "vid": "gid://shopify/ProductVariant/40516000219222",
    # },

class UsageInfo:
    def __init__(self, output_tokens, input_tokens):
        self.output_tokens = output_tokens
        self.input_tokens = input_tokens
        self.total_tokens = output_tokens + input_tokens

# Request schema
class ChatRequest(BaseModel):
    session_id: Optional[str] = None  # Session ID for tracking conversation
    ip_address: Optional[str] = None  # Session ID for tracking conversation
    message: str  # Client Asked Question
    metadata: dict = Field(
        default_factory=dict
    )  # Extensible for AI cost tracking, cart links, product references, etc.
    history: List[ResponseInputItemParam] = Field(
        default_factory=list
    )  # Chat History From Redis
    activity_record: str = ""
    is_vector_review_prompt_added: bool = False
    is_structural_output_prompt_added: bool = False
    is_cart_instructions_added: bool = False
    is_order_instructions_added: bool = False

    _manager: Optional[PromptManager] = PrivateAttr(default=None)

    def set_manager(self, manager: PromptManager):
        """Attach a PromptManager instance to this ChatRequest."""
        self._manager = manager

    def added_total_tokens(self, usage_info):
        previous_cost = self.metadata.get("tokens_usage", {})
        new_cost_completion = (
            previous_cost.get("completion_tokens", 0) + usage_info.output_tokens
        )
        new_cost_prompt = (
            previous_cost.get("prompt_tokens", 0) + usage_info.input_tokens
        )
        new_cost_total = previous_cost.get("total_tokens", 0) + usage_info.total_tokens
        self.metadata["tokens_usage"] = {
            "completion_tokens": new_cost_completion,
            "prompt_tokens": new_cost_prompt,
            "total_tokens": new_cost_total,
        }
        
    def chat_history_to_text(self):
        """
        Convert List[ResponseInputItemParam] into a single plain text string
        in a consistent prompt format.
        """
        parts = []
        for msg in self.history:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", "")

            # content may be list or string depending on API versions
            if isinstance(content, list):
                text_parts = []
                for section in content:
                    # Extract string content from nested types
                    if hasattr(section, "text"):
                        text_parts.append(section.text)
                    elif isinstance(section, str):
                        text_parts.append(section)
                content = "\n".join(text_parts)

            parts.append(f"{role.upper()}: {content}")

        return "\n".join(parts)


    def n_Serialize_chat_history(
        self, chat_history: List[ResponseInputItemParam]
    ) -> str:
        """Converts a list of Chatmsg objects to a JSON string."""
        list_of_dicts: List[Dict[str, Any]] = []

        for msg in chat_history:
            if isinstance(msg, dict) and "role" in msg:
                if msg["role"] == "developer":
                    dict_msg = {
                        "role": "developer",
                        "content": msg["content"],
                    }
                    list_of_dicts.append(dict_msg)

                elif msg["role"] == "system":
                    dict_msg = {
                        "role": "system",
                        "content": msg["content"],
                    }
                    list_of_dicts.append(dict_msg)

                elif msg["role"] == "user":
                    dict_msg = {
                        "role": "user",
                        "content": msg["content"],
                    }
                    list_of_dicts.append(dict_msg)

                elif msg["role"] == "assistant":
                    dict_msg: Dict[str, Any] = {"role": "assistant"}

                    # Optional fields
                    if "content" in msg and msg["content"] is not None:
                        dict_msg["content"] = msg["content"]

                    if "refusal" in msg and msg["refusal"] is not None:
                        dict_msg["refusal"] = msg["refusal"]

                    list_of_dicts.append(dict_msg)

            # elif isinstance(msg, dict) and "call_id" in msg:

            #     if msg["type"] == "custom_tool_call_output":
            #         # msg = self.serialize_tool_response(msg)
            #         dict_msg = {
            #             "type": "custom_tool_call_output",
            #             "output": msg["output"],
            #             "call_id": msg["call_id"],
            #         }
            #         list_of_dicts.append(dict_msg)

            # elif msg["role"] == "function":
            #     dict_msg = {
            #         "role": "function",
            #         "content": msg["output"],
            #     }
            #     list_of_dicts.append(dict_msg)

            else:
                continue
                list_of_dicts.append(dict(msg))

        return json.dumps({"data": list_of_dicts, "metadata": self.metadata})

    def parse_into_json_prompt(self):
        pass

    @staticmethod
    def serialize_tool_response(
        msg: ChatCompletionToolMessageParam,
    ) -> ChatCompletionToolMessageParam:
        content = str(msg["content"]) or "No content provided"
        # msg["content"] = f"{content[:100]}....{content[-100:]}" if len(content) > 200 else content  // TODO Re-write hybrid Approach
        if content[:10] == "#VectorDB-":
            objs = json.loads(content[10:])
            msg["content"] = str([obj["metadata"] for obj in objs])
        elif content[:15] == "#ShopifyProduct-":
            objs = json.loads(content[15:])
            # msg["content"] = str([obj["metadata"] for obj in objs])
            # TODO remove description from product as that is no more required after response
        else:
            msg["content"] = content
        # TODO Remove unstuctured chunks from each tool output and only keep most relevant and stuctured part to Efficienlty use Chat Limits
        return msg

    def n_Deserialize_chat_history(self, obj: dict) -> List[Dict[str, Any]]:
        """Converts a JSON string from Redis back into a list of ChatCompletionMessageParam-like dicts."""

        chat_list = []
        self.metadata = obj.get("metadata", {})

        for msg in obj.get("data", []):
            role = msg.get("role", "NULL")
            _type = msg.get("type", "NULL")

            if role == "developer":
                chat_list.append(
                    {
                        "role": "developer",
                        "content": msg["content"],
                    }
                )

            elif role == "system":
                chat_list.append(
                    {
                        "role": "system",
                        "content": msg["content"],
                    }
                )

            elif role == "user":
                chat_list.append(
                    {
                        "role": "user",
                        "content": msg["content"],
                    }
                )

            elif role == "assistant":
                restored: dict[str, Any] = {"role": "assistant"}

                if "content" in msg:
                    restored["content"] = msg["content"]

                if "tool_calls" in msg:
                    restored["tool_calls"] = [
                        self.deserialize_tool_call(tc) for tc in msg["tool_calls"]
                    ]

                if "audio" in msg:
                    restored["audio"] = msg["audio"]

                if "refusal" in msg:
                    restored["refusal"] = msg["refusal"]

                chat_list.append(restored)

            if _type == "custom_tool_call_output":
                chat_list.append(
                    {
                        "type": "custom_tool_call_output",
                        "output": msg["output"],
                        "call_id": msg["call_id"],
                    }
                )

            elif role == "function":
                chat_list.append(
                    {"role": "function", "content": msg["content"], "name": msg["name"]}
                )

            else:
                # Fallback — trust the data if unknown role
                continue
                chat_list.append(msg)

        return chat_list

    def serialize_function(self, function: Dict[str, Any]) -> Dict[str, Any]:
        return {"name": function["name"], "arguments": function["arguments"]}

    def serialize_tool_call(self, tool_call: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "id": tool_call["id"],
            "type": tool_call["type"],
            "function": self.serialize_function(tool_call["function"]),
        }

    def deserialize_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": tool_call["id"],
            "type": tool_call["type"],
            "function": {
                "name": tool_call["function"]["name"],
                "arguments": tool_call["function"]["arguments"],
            },
        }

    def load_history(self, session_data: Dict) -> None:
        self.history = cast(
            List[ResponseInputItemParam],
            self.n_Deserialize_chat_history(session_data),
        )

    @staticmethod
    def format_chat_msg(msg: ChatMessage):  # -> ChatCompletionmsgParam
        base = {
            "role": msg.role,
            "content": msg.content,
        }

        if msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
            base["tool_calls"] = (
                msg.tool_calls
            )  # Should be a List[ChatCompletionmsgToolCall]
            base["content"] = msg.content  # Must be null if tool_calls present

        elif msg.role == "tool":
            base.update(
                {
                    "tool_call_id": msg.tool_call_id,
                    "name": msg.name,
                }
            )

        # return cast(ChatCompletionmsgParam, base)
        return base

    def append_tool_response(self, content: str, tool_call_id: str):
        tool_msg: FunctionCallOutput = {
            "type": "function_call_output",
            "output": content,
            "call_id": tool_call_id,
        }
        self.history.append(tool_msg)

    def append_vectorDb_prompt(self):
        if self.is_vector_review_prompt_added:
            return

        _prompt: EasyInputMessageParam = {
            "role": "system",
            "content": self.vector_review_prompt,
        }
        self.history.append(_prompt)

        _prompt: EasyInputMessageParam = {
            "role": "system",
            "content": self.product_recomendation_prompt,
        }
        self.history.append(_prompt)

        self.is_vector_review_prompt_added = True

    def append_stuctural_output_prompt(self):
        if self.is_structural_output_prompt_added:
            return

        _prompt: EasyInputMessageParam = {
            "role": "system",
            "content": self.product_output_prompt,
        }

        self.history.append(_prompt)
        self.is_structural_output_prompt_added = True

    def append_cart_output_prompt(self):
        if self.is_cart_instructions_added:
            return

        _prompt: EasyInputMessageParam = {
            "role": "system",
            "content": self.cart_output_prompt,
        }

        self.history.append(_prompt)
        self.is_cart_instructions_added = True

    def append_order_output_prompt(self):
        if self.is_order_instructions_added:
            return

        _prompt: EasyInputMessageParam = {
            "role": "system",
            "content": self.order_output_prompt,
        }

        self.history.append(_prompt)
        self.is_order_instructions_added = True

    def append_message(self, data: dict[str, Any]):
        msg = cast(EasyInputMessageParam, data)
        self.history.append(msg)

    @staticmethod
    def extract_json_objects(text: str) -> Tuple[List[dict[str, Any]], str]:
        _CURRENCY_SYMBOLS = "€£$₹"
        _CURRENCY_CODE = r"[A-Z]{2,5}"

        _price_leading = re.compile(
            rf"^(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])\s*\d+(?:,\d{{3}})*(?:\.\d+)?$"
        )
        _price_trailing = re.compile(
            rf"^\d+(?:,\d{{3}})*(?:\.\d+)?\s*(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])$"
        )
        _price_range = re.compile(
            rf"^\d+(?:,\d{{3}})*(?:\.\d+)?\s*-\s*\d+(?:,\d{{3}})*(?:\.\d+)?\s*(?:{_CURRENCY_CODE}|[{_CURRENCY_SYMBOLS}])$"
        )

        def _valid_price(s: str) -> bool:
            s = s.strip()
            return bool(
                _price_leading.match(s)
                or _price_trailing.match(s)
                or _price_range.match(s)
            )

        def _valid_product(obj: Any) -> bool:
            if not isinstance(obj, dict):
                return False
            required = {"link", "imageurl", "title", "price", "description"}
            if not required.issubset(obj.keys()):
                return False
            if not all(
                isinstance(obj[k], str) and "\n" not in obj[k] for k in required
            ):
                return False
            if not (
                obj["link"].startswith("https://")
                and obj["imageurl"].startswith("https://")
            ):
                return False
            if obj["price"].strip() and not _valid_price(obj["price"]):
                return False
            return True

        def _valid_cart(obj: Any) -> bool:
            if not isinstance(obj, dict):
                return False
            required = {"id", "checkoutUrl", "subtotalAmount", "lineItems"}
            if not required.issubset(obj.keys()):
                return False
            if not all(
                isinstance(obj[k], str) and "\n" not in obj[k]
                for k in ["id", "checkoutUrl", "subtotalAmount"]
            ):
                return False
            if not obj["id"].startswith("gid://shopify/Cart/"):
                return False
            if not obj["checkoutUrl"].startswith("https://"):
                return False
            if obj["subtotalAmount"].strip() and not _valid_price(
                obj["subtotalAmount"]
            ):
                return False
            if not isinstance(obj["lineItems"], list):
                return False
            if not all(isinstance(item, dict) for item in obj["lineItems"]):
                return False
            return True

        def _valid_order(obj: Any) -> bool:
            """Lenient check for order JSON."""
            if not isinstance(obj, dict):
                return False
            orderish_keys = {
                "OrderID",
                "FinancialStatus",
                "FulfillmentStatus",
                "CustomerName",
                "CustomerPhone",
                "CustomerEmail",
                "Items",
                "ShippingAddress",
                "Total",
            }
            return any(k in obj for k in orderish_keys)

        # ---------- Text utilities ----------
        def _remove_spans(s: str, spans: List[Tuple[int, int]]) -> str:
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

        # 1) Handle fenced blocks
        fenced = re.compile(r"```(product|cart|order)\s*(.*?)```", re.DOTALL)
        for m in fenced.finditer(text):
            block_type = m.group(1).lower()
            block_content = m.group(2).strip()

            try:
                obj = json.loads(block_content)
            except json.JSONDecodeError:
                continue

            if block_type == "product" and _valid_product(obj):
                obj["type"] = "Product"
                results.append(obj)
                remove_spans.append((m.start(), m.end()))
            elif block_type == "cart" and _valid_cart(obj):
                obj["type"] = "Cart"
                results.append(obj)
                remove_spans.append((m.start(), m.end()))
            elif block_type == "order" and _valid_order(obj):
                obj["type"] = "Order"
                results.append(obj)
                remove_spans.append((m.start(), m.end()))

        intermediate = _remove_spans(text, remove_spans)

        # 2) Unfenced JSON objects
        spans2: List[Tuple[int, int]] = []
        for s, e, raw in _find_json_objects(intermediate):
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if _valid_product(obj):
                obj["type"] = "Product"
                results.append(obj)
                spans2.append((s, e))
            elif _valid_cart(obj):
                obj["type"] = "Cart"
                results.append(obj)
                spans2.append((s, e))
            elif _valid_order(obj):
                obj["type"] = "Order"
                results.append(obj)
                spans2.append((s, e))

        cleaned_text = _remove_spans(intermediate, spans2).strip()
        cleaned_text = re.sub(r"\[\s*\]", "", cleaned_text)
        cleaned_text = re.sub(r"\[\s*(?:,\s*)*\]", "", cleaned_text)
        cleaned_text = re.sub(
            r"```(?:json|product|cart|order)?\s*```",
            "",
            cleaned_text,
            flags=re.MULTILINE,
        )

        return results, cleaned_text.strip()

    def openai_msgs(self) -> List[ResponseInputItemParam]:
        """Return full OpenAI-compatible msg list including history and user input."""

        if len(self.history) == 0:
            chat = cast(
                ResponseInputItemParam,
                {"role": "system", "content": self.configurable_prompt},
            )
            self.history.append(chat)
            chat = cast(
                ResponseInputItemParam,
                {"role": "system", "content": self.system_prompt},
            )
            self.history.append(chat)

        # for msg in history:
        #     messages.append(self.format_chat_msg(msg))
        # try:
        #     print("vector_review_prompt :","len(history) > 2",len(history) > 1, "history[-1].role", history[-1].role if history else None)
        #     if len(history) > 1 and history[-1].role == "tool":
        #         msgs.append({"role": "system", "content": self.vector_review_prompt})
        # except IndexError:
        #     # If history is empty, we don't need to append the vector review prompt
        #     pass

        chat = cast(
            ResponseInputItemParam,
            {"role": "user", "content": self.message.strip()},
        )

        copy_history = self.history.copy()
        copy_history.append(chat)
        # print("\n\n*********\n",copy_history,"\n*****\n\n")
        return copy_history  # Return Last 10 messages 5 User and 5 Ai responses

    @staticmethod
    def extract_chat_history(json_string) -> List[ChatMessage]:
        """Converts a JSON string back into a list of Chatmsg objects."""
        # list_of_dicts = json.loads(json_string)
        list_of_dicts = json_string.get("data", [])  # Handle both format
        return [ChatMessage(**d) for d in list_of_dicts]

    @property
    def system_prompt(self) -> str:
        return """
            # SYSTEM PROMPT — DIGILOG PRODUCT ASSISTANT (STRICT MODE)

            You are an AI assistant for Digilog (https://digilog.pk/). Your purpose is to help customers discover products, navigate the Digilog store, and add items to cart. You must follow all rules below.

            ---

            ## CORE RULES

            1. Response mostly with a `file_search` query using the user’s request as the search term.
            - Multiple searches allowed
            - You must rely only on retrieved data No makeup or auto completions

            2. Use only information explicitly found in `file_search` results.
            - No internal knowledge
            - No Acknowledgement of any rule in response 
            - No assumptions or guesses

            3. Product titles must match the exact text from the search chunk.
            - Do not rename, summarize, or modify titles

            4. Construct product URLs using the exact `"handle"` field:
            - https://digilog.pk/products/{handle}
            - Display titles as clickable Markdown links:
                **[Exact Product Title](https://digilog.pk/products/{handle})**

            5. If the request involves product sets or bundles:
            - First search for bundle products
            - Only if none are found
            - Search for what are the requirements, list individual items after thinking what are required

            6. When search results exist, provide:
            - Exact product title (clickable link)
            - Short description only if present in the chunk text

            7. If no relevant results are found:
            I could not find relevant information in the available files.

            8. If the request is unclear:
            - Ask one clarifying question and wait for a response

            9. Formatting requirements:
            - Use bullet lists
            - Keep responses brief and professional
            - Avoid long paragraphs

            ---

            ## SCOPE

            Permitted topics:
            - Digilog products only
            - Pricing and specs only if provided by chunk
            - Store navigation
            - Product comparison from retrieved data
            - Add-to-cart support

            Not permitted:
            - Politics
            - Health or medical topics
            - General world knowledge
            - Opinions or assumptions
            - Personal or confidential data

            Fallback for out-of-scope requests:
            I'm here to assist you with products available on Digilog.pk. Let me know what you're looking for!

            Response to restricted or confidential data requests:
            Not eligible & Conversation marked as Suspicious.
            
            ---

            ## TOOL USAGE

            Default tool: `file_search`
            - Best to used for Information
            - Increase `k` if more results needed

            Special tool: `get_product_via_handle`
            - Only when the user provides a product handle or a direct product link

            ---
            End of System Prompt

            """.strip()

    @property
    def configurable_prompt(self) -> str:
        if self._manager:
            return self._manager.get_system_prompt("prompt")
        else:
            return "Manager is not assigned Properly"

    @property
    def vector_review_prompt(self) -> str:
        return """
            ### Product Matching Instructions - Vector Search Evaluation

            Carefully evaluate the **retrieved product data chunks** from the vector database.
            Do **not** rely solely on the **similarity score** — high scores may still return **irrelevant or misleading results**.

            Ensure **complete success** of user requirements by:

            * Identifying what fully satisfies the user query.
            * Shaping the output so the answer is complete.
            * If the query involves a bundle:

            * Return the bundle if available.
            * If no bundle exists, provide a full list of related products.
            * Always include follow-up questions if results are incomplete, guiding the user to a complete product list.

            Follow these steps to ensure accurate and useful product recommendations:

            ####  Step-by-Step Evaluation Process

            1. **Understand the User's Intent**
            Analyze the user's query deeply. Focus on **what the user actually wants** — not just keyword matches.

            2. **Critically Review All Retrieved Chunks**
            Examine each product data chunk to determine if it **truly matches** the user's intent.
            ✘ Do not assume top-ranked chunks are always relevant.
            ✔ Use logic, product context, and query alignment.

            3. **Filter Out Irrelevant Chunks**
            If a chunk is not directly useful to the query — **deprioritize or discard it**, even if it's top-ranked.

            4. Structured Response with Product Details from Relevant Matches
            Once relevant products are identified, the assistant must use the provided product list to construct a well-structured response that effectively addresses and satisfies the user's query.

            5. **Use Only Verified Product Data in Your Response**
            Recommend or describe **only** the products you are confident meet the user's needs, based on full data retrieval — not just partial matches.

            ### Do Not:

            * Do not guess based on similarity scores alone
            * Do not recommend irrelevant or loosely related products
            * Do not skip data fetching for relevant matches
            
            ### Goal:

            Deliver product recommendations that are **highly accurate, aligned with user intent**, and backed by complete product data.

        """.strip()

    @property
    def product_output_prompt(self) -> str:
        return """
            > All structured outputs must be wrapped in fenced code blocks.  
            > Use exactly ```product for product outputs.  
            > You must provide product details **only** in the following JSON structure.
            > **Every field is mandatory.**
            > **No extra fields, no changes to key names, no formatting outside JSON.**
            > If a value is unknown, you must use an empty string (`""`) — do not omit the field.
            > If this exact format is not followed, the system will reject the input and terminate processing.

            ```product
            {
            "link": "https://digilog.pk/products/product-page",
            "imageurl": "https://digilog.pk/cdn/shop/files/product-image.wenbp?v=1234567890&width=1400",
            "title": "Exact Product Title Here",
            "price": "99.99 CurrencyCode",
            "variants_options" : Contains valid product variants that must be communicated to the customer during chat to ensure clarity at the time of cart creation and to prevent any potential issues later.
            "description": "Rewrite the product description in a concise, buyer-focused style. Avoid long sentences. Present information as short bullet points that highlight only the most important specifications and benefits a buyer would consider before making a purchase. The tone should be clear, persuasive, and designed to elevate the product's value. Focus on properties that drive buying decisions (e.g., performance, durability, compatibility, size, unique advantages, price/value)."
            }
            ```

            **Rules**:

            1. `"link"` → Direct URL to the product page (must be a valid HTTPS link).
            2. `"imageurl"` → Direct URL to the product image (must be a valid HTTPS link).
            3. `"title"` → Exact name of the product, no extra words.
            4. `"price"` → Must include currency symbol and numeric value (e.g., `"19.99 PKR"`).
            5. "description" → Brief, precise, fact-focused summary.
            6. "variants_options" : "Pass the List exactly as received — no modifications, no renaming, no restructuring."
            7. **No additional fields** — only the above 6.
            8. **No line breaks inside values** — all values must be single-line strings.

            **Example of VALID input**:

            ```product
            {
            "link": "https://digilog.pk/products/solar-wifi-device-solar-wifi-dongle-in-pakistan",
            "imageurl": "https://digilog.pk/cdn/shop/files/Untitled_design_144dd069-c4ec-4b66-a8f8-0db6cdf38d2e.webp?v=1741255473&width=1400",
            "title": "Inverterzone Solar Wifi Device Solar wifi Dongle In Pakistan",
            "price": "7,500 PKR",
            "variants_options" : ["Metal_body", "Plastic_body"]
            "description": "The Inverterzone Solar WiFi Dongle is the ultimate solution for solar-powered homes, enabling real-time monitoring, efficient load consumption management, and scheduling of energy usage to maximize solar efficiency"
            }
            ```
        """.strip()

    @property
    def product_recomendation_prompt(self) -> str:
        if self._manager:
            return self._manager.get_recommend_product_prompt("prompt")
        else:
            return "Manager is not assigned Properly"

    @property
    def cart_output_prompt(self) -> str:
        return """
            > All structured outputs must be wrapped in fenced code blocks.  
            > Use exactly ```cart for cart outputs.  
            > You must provide cart details **only** in the following JSON structure.
            > **Every field is mandatory.**
            > **No extra fields, no changes to key names, no formatting outside JSON.**
            > If a value is unknown, you must use an empty string (`""`) — do not omit the field.
            > If this exact format is not followed, the system will reject the input and terminate processing.

            ```cart
            {
                "id": "gid://shopify/Cart/abc123?key=xyz789",
                "checkoutUrl": "https://store.com/cart/c/xyz789?key=123456",
                "subtotalAmount": "123.45 PKR",
                "lineItems":[{"merchandise_title": "Clay Toy small", "quantity": 12, "merchandise_price": "12.99 PKR"}, {"merchandise_title": "Lego Block Toy Empire State Building" , "quantity": 1, "merchandise_price": "1200.0 PKR"}]
            }
            ```

            ### **Rules**

            1. `"id"` → Shopify cart ID.
            * Must be a valid Shopify GID string.
            * Format: `"gid://shopify/Cart/<cart_id>?key=<key>"`.

            2. `"checkoutUrl"` → Direct checkout URL.
            * Must be a valid `https://` link.
            * No spaces or line breaks.

            3. `"subtotalAmount"` → Cart subtotal.
            * Must include numeric value **and** standard currency.
            * Example: `"1180.00 PKR"`.

            4. `"lineItems"` → Line items dictionary.
            * **Pass it exactly as received.**
            * Do not alter field names, structure, or values.

            5. **No additional fields** — Only the 4 keys above.
            6. **All values must be single-line strings.**

            **Example of VALID input**:

            ```cart
            {
                "id": "gid://shopify/Cart/hWN2VMsRlxJ6NFxkDHvupfec?key=e8b1bedbf1d5f8b1d4abe21d1613d286",
                "checkoutUrl": "https://store-mobeen-pk.myshopify.com/cart/c/hWN2VMsRlxJ6NFxkDHvupfec?key=e8b1bedbf1d5f8b1d4abe21d1613d286",
                "subtotalAmount": "1180.00 PKR",
                "lineItems": [{"merchandise_title": "Clay Toy small", "quantity": 12, "merchandise_price": "12.99 PKR"}, {"merchandise_title": "Lego Block Toy Empire State Building" , "quantity": 1, "merchandise_price": "1200.0 PKR"}]
            }
            ```
        """.strip()

    @property
    def order_output_prompt(self) -> str:
        return """
            > All structured outputs must be wrapped in fenced code blocks.  
            > Use exactly ```json for order outputs.  
            > You must provide order details **only** in the following JSON structure.
            > **Every field is mandatory.**
            > **No extra fields, no changes to key names, no formatting outside JSON.**
            > If a value is unknown, you must use an empty string (`""`) — do not omit the field.
            > If this exact format is not followed, the system will reject the input and terminate processing.

            ```json
            {
                "OrderID": "#12341",
                "FinancialStatus": "Paid",
                "FulfillmentStatus": "Shipped",
                "CustomerName": "Syed Raza Gufran",
                "CustomerPhone": "0321******51",
                "CustomerEmail": "dev**********gmail.com",
                "Items" : " - Surfing Product, Qty: 12, UnitPrice : 234 PKR "
                "ShippingAddress" "st 12 house no 234 main colony newyork sector d "
                "Total": "123.14 PKR"
            }
            ```

            ### **Rules**

            1. `"OrderID"` → Shopify Order Number.
            * Must be a valid Shopify Order string.
            * Format: `"[identifier i.e. #, !, 💙][number i.e. 123 42531]"`.

            2. `"FinancialStatus"` → Payment status of the order (e.g., Paid, Pending, Refunded).
            * Must be written in a single line without spaces or breaks.

            3. `"FulfillmentStatus"` → Shipping/Delivery status of the order (e.g., Shipped, Unshipped, Partially Shipped).
            * Must be written in a single line without spaces or breaks.
            
            4. "CustomerName", "CustomerPhone", "CustomerEmail", "ShippingAddress"→ These fields contain the customer’s personal details. Sometimes part of the information may be hidden (e.g., masked with *), but you must still pass them exactly as received.
            
            5. "Total"
            * Must include numeric value **and** standard currency.
            * Example: `"1180.00 PKR"`.

            6. `"Items"` → Line items multilines data.
            * **Pass it exactly as received.**
            * Do not alter field names, structure, or values.

            5. **No additional fields** — Only the 4 keys above.
            6. **All values must be single-line strings.**

            **Example of VALID input**:

            ```json
            {
                "OrderID": "#12341",
                "FinancialStatus": "Paid",
                "FulfillmentStatus": "Shipped",
                "CustomerName": "Syed Raza Gufran",
                "CustomerPhone": "0321******51",
                "CustomerEmail": "dev**********gmail.com",
                "Items": " - Surfing Product, Qty: 12, UnitPrice : 234 PKR",
                "ShippingAddress": "st 12 house no 234 main colony newyork sector d",
                "Total": "$249.99"
            }
            ```
        """.strip()
