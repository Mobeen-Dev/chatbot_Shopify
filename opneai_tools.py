from openai.types.chat import ChatCompletionToolParam

tools_list: list[ChatCompletionToolParam] = [
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
                "description": "Search query describing the product, e.g., 'wireless noise-canceling headphones'"
            },
            "top_k_result": {
                "type": "integer",
                "description": "The number of top similar products to return."
            }
        },
        "required": ["query"],
        "additionalProperties": False
      }
    }
  },
  {
    "type": "function",
    "function": {
        "name": "get_product_via_handle",
        "description": "Fetch the complete and up-to-date product details directly from Shopify using the product's handle.",
        "parameters": {
            "type": "object",
            "properties": {
                "handle": {
                    "type": "string",
                    "description": "The unique Shopify product handle (e.g., 'solar-wifi-device-solar-wifi-dongle-in-pakistan'). This is used to identify and retrieve the full product data."
                }
            },
            "required": ["handle"],
            "additionalProperties": False
        }
    }
}

]