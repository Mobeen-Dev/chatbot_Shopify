# from openai.types.chat import ChatCompletionToolParam # Depreciated
from openai.types.responses.tool_param import ParseableToolParam
from openai.types.responses.file_search_tool_param import FileSearchToolParam
from openai.types.responses.function_tool_param import FunctionToolParam

from openai.types.responses.tool_param import ToolParam
from config import settings

tools_list: list[ToolParam] = [
    FileSearchToolParam(
        type="file_search",
        vector_store_ids=[settings.vector_store_id],
        max_num_results=20,
    ),
    FunctionToolParam(
        type="function",
        name="get_product_via_handle",
        description="Fetch the complete and up-to-date product details directly from Shopify using the product's handle.",
        parameters={
            "type": "object",
            "properties": {
                "handle": {
                    "type": "string",
                    "description": "The unique Shopify product handle (e.g., 'solar-wifi-device-solar-wifi-dongle-in-pakistan'). This is used to identify and retrieve the full product data.",
                }
            },
            "required": ["handle"],
            "additionalProperties": False,
        },
        strict=(True),
    ),
    FunctionToolParam(
        type="function",
        name="get_order_via_order_number",
        description="Retrieve and format Shopify order details using an order number.",
        parameters={
            "type": "object",
            "properties": {
                "order_number": {
                    "type": "string",
                    "description": "The Shopify order number (with or without #, e.g., '#1234' or '1234').",
                }
            },
            "required": ["order_number"],
            "additionalProperties": False,
        },
        strict=True,
    ),
]

vector_db_features = [
    {
        "type": "function",
        "function": {
            "name": "get_products_data",
            "description": "Get product data for a given query using vector similarity search in the product database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query describing the product in the context as keyword as possible, e.g., 'wireless noise-canceling headphones'",
                    },
                    "top_k_result": {
                        "type": "integer",
                        "description": "The number of top similar products to return.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    }
]

agentic_feature = [
    {
        "type": "function",
        "function": {
            "name": "create_new_cart_with_items",
            "description": "Create a new shopping cart with initial items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "List of products to add to the new cart.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "handle": {
                                    "type": "string",
                                    "description": "The unique product handle.",
                                },
                                "variant": {
                                    "type": "string",
                                    "description": "The product variant title or identifier.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "The number of items to add.",
                                },
                            },
                            "required": ["handle", "variant", "quantity"],
                            "additionalProperties": False,
                        },
                    },
                    "session_id": {
                        "type": "string",
                        "description": "A unique session identifier for the cart. Defaults to 'default'.",
                    },
                },
                "required": ["items", "session_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_cart",
            "description": "Retrieve the current state of a shopping cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {
                        "type": "string",
                        "description": "The unique identifier of the cart to fetch.",
                    }
                },
                "required": ["cart_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_cartline_items",
            "description": "Add one or more line items to an existing shopping cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {
                        "type": "string",
                        "description": "The unique identifier of the cart to update.",
                    },
                    "line_items": {
                        "type": "array",
                        "description": "List of products to add to the cart.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "handle": {
                                    "type": "string",
                                    "description": "The unique product handle.",
                                },
                                "variant": {
                                    "type": "string",
                                    "description": "The product variant title or identifier.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "The number of items to add.",
                                },
                            },
                            "required": ["handle", "variant", "quantity"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["cart_id", "line_items"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_cartline_items",
            "description": "Update one or more line items in a shopping cart (e.g., adjust quantity or variant).",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {
                        "type": "string",
                        "description": "The unique identifier of the cart to update.",
                    },
                    "line_items": {
                        "type": "array",
                        "description": "List of line items to update in the cart.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "handle": {
                                    "type": "string",
                                    "description": "The unique product handle.",
                                },
                                "variant": {
                                    "type": "string",
                                    "description": "The product variant title or identifier.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "The updated quantity for this line item.",
                                },
                            },
                            "required": ["handle", "variant", "quantity"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["cart_id", "line_items"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_cartline_items",
            "description": "Remove one or more line items from a shopping cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {
                        "type": "string",
                        "description": "The unique identifier of the cart to update.",
                    },
                    "line_items": {
                        "type": "array",
                        "description": "List of line items to remove from the cart.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "handle": {
                                    "type": "string",
                                    "description": "The unique product handle.",
                                },
                                "variant": {
                                    "type": "string",
                                    "description": "The product variant title or identifier.",
                                },
                            },
                            "required": ["handle", "variant"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["cart_id", "line_items"],
                "additionalProperties": False,
            },
        },
    },
]
