from models import ChatRequest
import json
from config import settings, embeddind_model
from logger import get_logger
from wrapper_chroma import ChromaRetriever
from Shopify import Shopify


class Controller:
    """
    Controller class for handling product-related operations.
    This class interacts with the vector store and product store to fetch product data.
    """

    def __init__(self):
        self.vector_store = ChromaRetriever()
        self.store = Shopify(settings.store, "ShopifyClient")
        self.logger = get_logger("MCP - Controller")

    def get_products_data(self, query: str, top_k: int = 5) -> str:
        """
        Function for fetching product data based on a query.
        This interact with a Comapany Vector database.
        """
        results = self.vector_store.query_chroma(query=query, top_k=top_k+3)
        return json.dumps(results) 

    async def get_product_via_handle(self, handle: str) -> str:
        """
        Function to fetch complete product data using the product handle.
        This is used to get the most up-to-date product information.
        """
        product = await self.store.get_product_by_handle(handle)
        if not product:
            return json.dumps({"error": "Product not found."})
        product = self.store.format_product(product)
        return str(product)

    async def function_execution(self, chat_request: ChatRequest, tool_calls) -> ChatRequest:
        vector_db_flag = False
        shopify_flag = False
    
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            if function_name == "get_products_data":
                query = arguments["query"]
                top_k = arguments.get("top_k_result", 7)

                # Call the actual function
                tool_output = self.get_products_data(query, top_k)

                # Append tool response to messages
                chat_request.append_tool_response(tool_output, tool_call.id)
                
                vector_db_flag = True
                
            elif function_name == "get_product_via_handle":
                handle = arguments["handle"]
                
                # Call the actual function
                tool_output = await self.get_product_via_handle(handle)

                # Append tool response to messages
                chat_request.append_tool_response(tool_output, tool_call.id)
                
                shopify_flag = True
        
        if vector_db_flag:
            chat_request.append_vectorDb_prompt()
        if shopify_flag:
            chat_request.append_stuctural_output_prompt()
            
        return chat_request

    async def get_order_via_order_number(self, order_number: str) -> str:
        """
        Fetch and format an order by its order number.
        Ensures order number starts with '#'.
        Returns structured data ready for LLM.
        """
        # Ensure order number starts with "#"
        if not order_number.startswith("#"):
            order_number = f"#{order_number}"

        # Fetch from store
        data = await self.store.fetch_order_by_name(order_number)
        if not data:
            return str({"success": False, "message": f"No order found for {order_number}"})

        # Format for LLM
        formatted = Shopify.format_order_for_llm(data)
        
        return formatted

