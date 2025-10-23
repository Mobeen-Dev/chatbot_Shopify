import re
import json
from dataclasses import dataclass
from utils.PromptManager import PromptManager
from pydantic import BaseModel, Field, PrivateAttr
from typing import Optional, List, Literal, Dict, Any, cast, Mapping, Tuple
from openai.types.chat import (
    ChatCompletionMessageToolCall,
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionSystemMessageParam,
)

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


# Request schema
class ChatRequest(BaseModel):
    session_id: Optional[str] = None  # Session ID for tracking conversation
    ip_address: Optional[str] = None  # Session ID for tracking conversation
    message: str  # Client Asked Question
    metadata: dict = Field(
        default_factory=dict
    )  # Extensible for AI cost tracking, cart links, product references, etc.
    history: List[ChatMessage] = Field(default_factory=list)  # Chat History From Redis
    n_history: List[ChatCompletionMessageParam] = Field(
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
            previous_cost.get("completion_tokens", 0) + usage_info.completion_tokens
        )
        new_cost_prompt = (
            previous_cost.get("prompt_tokens", 0) + usage_info.prompt_tokens
        )
        new_cost_total = previous_cost.get("total_tokens", 0) + usage_info.total_tokens
        self.metadata["tokens_usage"] = {
            "completion_tokens": new_cost_completion,
            "prompt_tokens": new_cost_prompt,
            "total_tokens": new_cost_total,
        }

    def n_Serialize_chat_history(
        self, chat_history: List[ChatCompletionMessageParam]
    ) -> str:
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
                dict_msg = {
                    "role": "system",
                    "content": msg["content"],
                }
                list_of_dicts.append(dict_msg)

            elif msg["role"] == "user":
                dict_msg = {
                    "role": "user",
                    "content": msg["content"],
                    "name": msg.get("name", "Customer"),
                }
                list_of_dicts.append(dict_msg)

            elif msg["role"] == "assistant":
                dict_msg: Dict[str, Any] = {"role": "assistant"}

                # Optional fields
                if "content" in msg and msg["content"] is not None:
                    dict_msg["content"] = msg["content"]

                if "tool_calls" in msg and msg["tool_calls"]:
                    dict_msg["tool_calls"] = [
                        self.serialize_tool_call(tc) for tc in msg["tool_calls"]
                    ]

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
            role = msg.get("role")

            if role == "developer":
                chat_list.append(
                    {
                        "role": "developer",
                        "content": msg["content"],
                        "name": msg.get("name"),
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
                        "name": msg.get("name"),
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

                if "name" in msg:
                    restored["name"] = msg["name"]

                if "refusal" in msg:
                    restored["refusal"] = msg["refusal"]

                chat_list.append(restored)

            elif role == "tool":
                chat_list.append(
                    {
                        "role": "tool",
                        "content": msg["content"],
                        "tool_call_id": msg["tool_call_id"],
                    }
                )

            elif role == "function":
                chat_list.append(
                    {"role": "function", "content": msg["content"], "name": msg["name"]}
                )

            else:
                # Fallback — trust the data if unknown role
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
        self.n_history = cast(
            List[ChatCompletionMessageParam],
            self.n_Deserialize_chat_history(session_data),
        )

    def append_msg(
        self,
        role: Role,
        content: Optional[str] = None,
        tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None,
        tool_call_id: Optional[str] = None,
        function_name: Optional[str] = None,
    ) -> None:
        """Append a tool msg to the History Queue."""

        if tool_calls:
            tool_msg = ChatMessage(role=role, tool_calls=tool_calls, content=content)
            self.history.append(tool_msg)

        elif tool_call_id and function_name:
            tool_msg = ChatMessage(
                role=role,
                tool_call_id=tool_call_id,
                name=function_name,
                content=content,
            )
            self.history.append(tool_msg)
        else:
            msg = ChatMessage(role=role, content=content)
            self.history.append(msg)

        return

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
        tool_msg: ChatCompletionToolMessageParam = {
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call_id,
        }
        self.n_history.append(tool_msg)

    def append_vectorDb_prompt(self):
        if self.is_vector_review_prompt_added:
            return

        tool_prompt: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": self.vector_review_prompt,
        }
        self.n_history.append(tool_prompt)

        tool_prompt: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": self.product_recomendation_prompt,
        }
        self.n_history.append(tool_prompt)

        self.is_vector_review_prompt_added = True

    def append_stuctural_output_prompt(self):
        if self.is_structural_output_prompt_added:
            return

        tool_prompt: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": self.product_output_prompt,
        }

        self.n_history.append(tool_prompt)
        self.is_structural_output_prompt_added = True

    def append_cart_output_prompt(self):
        if self.is_cart_instructions_added:
            return

        tool_prompt: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": self.cart_output_prompt,
        }

        self.n_history.append(tool_prompt)
        self.is_cart_instructions_added = True

    def append_order_output_prompt(self):
        if self.is_order_instructions_added:
            return

        tool_prompt: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": self.order_output_prompt,
        }

        self.n_history.append(tool_prompt)
        self.is_order_instructions_added = True

    def append_message(self, data: dict[str, Any]):
        msg_dict = cast(ChatCompletionMessageParam, data)
        self.n_history.append(msg_dict)

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

    def openai_msgs(self) -> List[ChatCompletionMessageParam]:
        """Return full OpenAI-compatible msg list including history and user input."""

        if len(self.n_history) == 0:
            chat = cast(
                ChatCompletionMessageParam,
                {"role": "system", "content": self.configurable_prompt},
            )
            self.n_history.append(chat)
            chat = cast(
                ChatCompletionMessageParam,
                {"role": "system", "content": self.system_prompt},
            )
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

        chat = cast(
            ChatCompletionMessageParam,
            {"role": "user", "content": self.message.strip()},
        )

        copy_history = self.n_history.copy()
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
            > You are a helpful assistant created by Digilog ([https://digilog.pk/](https://digilog.pk/)).
            >
            > Your primary purpose is to provide **accurate, relevant, and helpful information exclusively about the Digilog Store**, its listed products, their features, specifications, pricing, availability, and usage. You must recommend products based on user queries and assist with navigation or product comparisons — all within the scope of the Digilog Store.
            > The ideal conversation flow should follow this structure: **user query → product recommendation → add to cart.**
            > **Do not respond to** any questions or engage in discussions unrelated to the Digilog Store or its product offerings. This includes political topics, health advice, trivia, or general knowledge questions. If a user asks something off-topic, do not improvise. Instead, politely redirect the conversation.
            > **Always include a clickable product link in every product-related response**, regardless of where the product is mentioned. This ensures users can easily verify and access the product directly.
            > Example response for off-topic questions:
            > **“I'm here to assist you with products available on Digilog.pk. Let me know what you're looking for!”**
            >
            > You must not access, request, or process any personal data or confidential company information. If such information is requested out of scope of regular customer like analytics bulk order data, reply strictly with:
            > **"Not eligible."**
            >
            > ### Limitations
            >
            > * Do not discuss politics, health, or non-product topics
            > * Do not generate or explain trivia or general world knowledge
            > * Do not give opinions on matters outside Digilog products
            > * Do not make assumptions about user needs outside shopping context
            >
            > ### Fallback Logic
            >
            > If the user question is not related to the Digilog Store or its products:
            >
            > * Do not guess or fabricate answers
            > * For Any task Beyond Digilog Website, straight reject the query
            > * Politely redirect them back to store-related queries using the fallback message above
            >
            > ### Tone and Voice
            >
            > * Keep tone **professional, friendly, and concise**
            > * Avoid slang, jokes, or overly casual phrasing
            > * Stay informative, neutral, and helpful at all times
            >
            > ### Function Calling Procedures
            
            1. **Default Function → `get_products_data`**

            * Always use `get_products_data` as the **primary retrieval source**.
            * It queries the vector DB with all products aligned to Shopify API data.
            * This function should handle most cases — from product searches, comparisons, availability checks, and recommendations.
            * You can call it multiple times with slightly different query variations.
            * If results seem too narrow or incomplete, **increase the parameter `k`** to expand recall and improve results.

            2. **Special Case → `get_product_via_handle`**

            * Only use this function when the user explicitly provides a **direct product link/handle**.
            * If the user does not provide a link, **do not use** this function.
            * This ensures efficient lookups without unnecessary API calls.

            3. **Query Handling Rules**

            * If the query is about a product, always try `get_products_data` first unless a handle/link is provided.
            * Do not mix up the two functions — each has a clear use case.
            * For vague or incomplete queries, re-run `get_products_data` with adjusted query text or a higher `k`.
            * Never invent, guess, or hallucinate product data — rely only on function outputs.



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
