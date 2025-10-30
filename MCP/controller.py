from models import ChatRequest
import json
from typing import List, Dict, Any, Union
from config import settings, embedding_model, order_prefix
from utils.logger import get_logger
from database import vectorDB
from Shopify import Shopify


class Controller:
    """
    Controller class for handling product-related operations.
    This class interacts with the vector store and product store to fetch product data.
    """
    def __init__(self):
        self.vector_store = vectorDB()
        self.store = Shopify(settings.store, "ShopifyClient")
        self.logger = get_logger("MCP - Controller")
        

    async def function_execution(self, chat_request: ChatRequest, tool_calls) -> ChatRequest:
        vector_db_flag = False
        shopify_flag = False
        cart_flag = False
        order_flag = False
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            self.logger.info(f"\nFunction to Execute : {function_name} parameters : {arguments}\n")
            
            if function_name == "get_products_data":
                chat_request.activity_record += " -> get_products_data"
                
                query = arguments["query"]
                top_k = arguments.get("top_k_result", 6)

                # Call the actual function
                tool_output = await self.get_products_data(query, top_k)

                # Append tool response to messages
                chat_request.append_tool_response(tool_output, tool_call.id)
                
                vector_db_flag = True
                
            elif function_name == "get_product_via_handle":
                handle = arguments["handle"]
                chat_request.activity_record += " -> get_product_via_handle"
                
                # Call the actual function
                tool_output = await self.get_product_via_handle(handle)

                # Append tool response to messages
                chat_request.append_tool_response(tool_output, tool_call.id)
                
                shopify_flag = True
                
            elif function_name == "get_order_via_order_number":
                order_number = arguments["order_number"]
                chat_request.activity_record += " -> get_order_via_order_number"
                
                # Call the actual function
                tool_output = await self.get_order_via_order_number(order_number)

                # Append tool response to messages
                chat_request.append_tool_response(tool_output, tool_call.id)
                
                order_flag = True
                
            elif function_name == "create_new_cart_with_items":
                items = arguments["items"]
                session_id = arguments.get("session_id", "default")
                chat_request.activity_record += " -> create_new_cart_with_items"

                tool_output = await self.create_new_cart_with_items(items, session_id)
                cart_flag = True
                chat_request.append_tool_response(str(tool_output), tool_call.id)

    # Agentic Abilities
            
            elif function_name == "query_cart":
                cart_id = arguments["cart_id"]
                chat_request.activity_record += " -> query_cart"
                
                tool_output = await self.query_cart(cart_id)
                cart_flag = True
                chat_request.append_tool_response(str(tool_output), tool_call.id)

            elif function_name == "add_cartline_items":
                cart_id = arguments["cart_id"]
                line_items = arguments["line_items"]
                chat_request.activity_record += " -> add_cartline_items"

                tool_output = await self.add_cartline_items(cart_id, line_items)
                cart_flag = True
                chat_request.append_tool_response(str(tool_output), tool_call.id)

            elif function_name == "update_cartline_items":
                cart_id = arguments["cart_id"]
                line_items = arguments["line_items"]
                chat_request.activity_record += " -> update_cartline_items"

                tool_output = await self.update_cartline_items(cart_id, line_items)
                cart_flag = True
                chat_request.append_tool_response(str(tool_output), tool_call.id)

            elif function_name == "remove_cartline_items":
                cart_id = arguments["cart_id"]
                line_items = arguments["line_items"]
                chat_request.activity_record += " -> remove_cartline_items"

                tool_output = await self.removeCartline_items(cart_id, line_items)
                cart_flag = True
                chat_request.append_tool_response(str(tool_output), tool_call.id)

            else:
                raise ReferenceError
        if vector_db_flag:
            chat_request.append_vectorDb_prompt()
            chat_request.append_stuctural_output_prompt()  # Instruction to return product in Stucture Format
        if shopify_flag:
            chat_request.append_stuctural_output_prompt()
        if cart_flag:
            chat_request.append_cart_output_prompt()
        if order_flag:
            chat_request.append_order_output_prompt()
        
        return chat_request

# Vector DB
    async def get_products_data(self, query: str, top_k: int = 5) -> str:
        """
        Function for fetching product data based on a query.
        This interact with a Comapany Vector database.
        """
        if top_k < 5 and top_k > 2:
            top_k += 3
        results = await self.vector_store.query(query=query, top_k=top_k)
        results = json.dumps(results, indent=2)
        results = "#VectorDB-"+results  # Added Identifier for future Actions
        return results 

# Admin API
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

    async def get_order_via_order_number(self, order_number: str) -> str:
        """
        Fetch and format an order by its order number.
        Ensures order number starts with '#'.
        Returns structured data ready for LLM.
        """
        # Ensure order number starts with "#"
        if not order_number.startswith(str(order_prefix)):
            order_number = f"{order_prefix}{order_number}"

        # Fetch from store
        data = await self.store.fetch_order_by_name(order_number)
        if not data:
            return str({"success": False, "message": f"No order found for {order_number}"})

        # Format for LLM
        formatted = Shopify.format_order_for_llm(data)
        
        return formatted

# StoreFront API
    async def create_new_cart_with_items(self, items: List[Dict[str, Union[str, int]]], session_id: str = "default") -> Dict[str, Any]:
        await self.store.init_handle_id_table()
        """
        Create a new shopping cart with initial items.

        Args:
            items (List[Dict[str, Union[str, int]]]): 
                A list of dictionaries, where each dictionary must include:
                    - "handle" (str): The unique product handle.
                    - "variant" (str): The variant title or identifier.
                    - "quantity" (int): The number of items to add.

                Example:
                [
                    {
                        "handle": "anycubic-full-metal-i3-mega-3d-printer-with-ultrabase-heatbed-and-3-5-inch-touch-screen",
                        "variant": "Default Title",
                        "quantity": 1
                    }
                ]

            session_id (str): A unique session identifier for the cart. This will be provided in User Query

        Returns:
            dict: A structured response with one of the following formats:
                - On success:
                    {
                        "success": True,
                        "cart": { ...created cart object... }
                    }
                - On failure:
                    {
                        "success": False,
                        "message": "Cannot create cart at this moment",
                        "errors": [ ...list of error messages... ]
                    }

        Example:
            result = await cart_service.create_cart(items, session_id="user123")
            if result["success"]:
                print(result["cart"])
            else:
                print(result["errors"])

        Notes:
            - This function is designed for AI/MCP execution, ensuring deterministic input/output.
            - All errors are returned as structured JSON, not raw exceptions.
            - If `userErrors` are returned from the store, they will be included in `errors`.
        """
        try:
            # Call store method to create cart
            data = await self.store.create_cart(items, session_id)

            # Handle failure (empty response)
            if not data:
                return {
                    "success": False,
                    "message": "Cannot create cart at this moment",
                    "errors": ["Unknown error - empty response from store"]
                }

            # Handle store-level user errors
            if "userErrors" in data and data["userErrors"]:
                return {
                    "success": False,
                    "message": "Cannot create cart at this moment",
                    "errors": data["userErrors"]
                }

            # Success response
            return {
                "success": True,
                "message": 'Your Request is fulfilled please check the cart details in "cart" ',
                "cart": data.get("cart", data)  # fallback if "cart" not explicitly returned
            }

        except Exception as e:
            # Ensure AI always gets structured error
            return {
                "success": False,
                "message": "Unexpected error while creating cart",
                "errors": [str(e)]
            }

    async def query_cart(self, cart_id: str) -> Dict[str, Any]:
        """
        Retrieve the current state of a shopping cart.

        Args:
            cart_id (str): Unique identifier of the cart to fetch.

        Returns:
            dict: A structured response with one of the following formats:
                - On success:
                    {
                        "success": True,
                        "cart": { ...cart object with items, totals, etc... }
                    }
                - On failure:
                    {
                        "success": False,
                        "message": "Cannot get cart at this moment",
                        "errors": [ ...list of error messages... ]
                    }

        Example:
            result = await cart_service.query_cart("gid://shopify/Cart/12345")
            if result["success"]:
                print(result["cart"])
            else:
                print(result["errors"])

        Notes:
            - This function is designed for AI/MCP execution, ensuring deterministic input/output.
            - All errors are returned as structured JSON, not raw exceptions.
            - If `userErrors` are returned from the store, they will be included in `errors`.
        """
        try:
            # Fetch cart data from store
            data = await self.store.query_cart(cart_id)

            # Handle failure (empty response)
            if not data:
                return {
                    "success": False,
                    "message": "Cannot get cart at this moment Try Again Later",
                    "errors": ["Unknown error - empty response from store Try Again Later"]
                }

            # Handle store-level user errors
            if "userErrors" in data and data["userErrors"]:
                return {
                    "success": False,
                    "message": "Cannot get cart at this moment Try Again Later",
                    "errors": data["userErrors"]
                }

            # Success response
            return {
                "success": True,
                "cart": data
            }

        except Exception as e:
            # Ensure AI always gets structured error
            return {
                "success": False,
                "message": "Unexpected error while querying cart Try Again Later",
                "errors": [str(e)]
            }

    async def add_cartline_items(self, cart_id: str, line_items: List[Dict[str, Union[str, int]]]) -> Dict[str, Any]:
        await self.store.init_handle_id_table()
        """
        Add one or more line items to a shopping cart.

        Args:
            cart_id (str): Unique identifier of the cart to which items should be added.
            line_items (List[Dict[str, Union[str, int]]]): 
                A list of dictionaries, where each dictionary must include:
                    - "handle" (str): The unique product handle.
                    - "variant" (str): The variant title or identifier.
                    - "quantity" (int): The number of items to add.

                Example:
                [
                    {
                        "handle": "anycubic-full-metal-i3-mega-3d-printer-with-ultrabase-heatbed-and-3-5-inch-touch-screen",
                        "variant": "Default Title",
                        "quantity": 1
                    }
                ]

        Returns:
            dict: A structured response with one of the following formats:
                - On success:
                    {
                        "success": True,
                        "cart": { ...updated cart object... }
                    }
                - On failure:
                    {
                        "success": False,
                        "message": "Cannot add product(s) to your cart",
                        "errors": [ ...list of error messages... ]
                    }

        Notes:
            - This function is designed for AI/MCP execution, ensuring deterministic input/output.
            - All errors are returned as structured JSON, not raw exceptions.
            - If `userErrors` are returned from the store, they will be included in `errors`.
        """
        try:
            # Call store method to add line items
            data = await self.store.addCartLineItems(cart_id, line_items)

            # Handle failure (empty response)
            if not data:
                return {
                    "success": False,
                    "message": "Cannot add product(s) to your cart Try Again Later",
                    "errors": ["Unknown error - empty response from store Try Again Later"]
                }

            # Handle store-level user errors
            if "userErrors" in data and data["userErrors"]:
                return {
                    "success": False,
                    "message": "Cannot add product(s) to your cart Try Again Later",
                    "errors": data["userErrors"]
                }

            # Success response
            return {
                "success": True,
                "cart": data.get("cart", data)  # fallback if "cart" not explicitly returned
            }

        except Exception as e:
            # Ensure AI always gets structured error
            return {
                "success": False,
                "message": "Unexpected error while adding cart items Try Again Later",
                "errors": [str(e)]
            }

    async def update_cartline_items(self, cart_id: str, line_items: List[Dict[str, Union[str, int]]]) -> Dict[str, Any]:
        await self.store.init_handle_id_table()
        """
        Update one or more line items in a shopping cart.
        This can be used to change quantity or variant of products already in the cart.

        Args:
            cart_id (str): Unique identifier of the cart to update.
            line_items (List[Dict[str, Union[str, int]]]): 
                A list of dictionaries, where each dictionary must include:
                    - "handle" (str): The unique product handle.
                    - "variant" (str): The variant title or identifier.
                    - "quantity" (int): The updated quantity for this line item.

                Example:
                [
                    {
                        "handle": "anycubic-full-metal-i3-mega-3d-printer-with-ultrabase-heatbed-and-3-5-inch-touch-screen",
                        "variant": "Default Title",
                        "quantity": 2
                    }
                ]

        Returns:
            dict: A structured response with one of the following formats:
                - On success:
                    {
                        "success": True,
                        "cart": { ...updated cart object... }
                    }
                - On failure:
                    {
                        "success": False,
                        "message": "Cannot update product(s) in your cart",
                        "errors": [ ...list of error messages... ]
                    }

        Notes:
            - This function is designed for AI/MCP execution, ensuring deterministic input/output.
            - All errors are returned as structured JSON, not raw exceptions.
            - If `userErrors` are returned from the store, they will be included in `errors`.
        """
        try:
            # Call store method to update line items
            data = await self.store.updateCartLineItems(cart_id, line_items)

            # Handle failure (empty response)
            if not data:
                return {
                    "success": False,
                    "message": "Cannot update product(s) in your cart Try Again Later",
                    "errors": ["Unknown error - empty response from store Try Again Later"]
                }

            # Handle store-level user errors
            if "userErrors" in data and data["userErrors"]:
                return {
                    "success": False,
                    "message": "Cannot update product(s) in your cart Try Again Later",
                    "errors": data["userErrors"]
                }

            # Success response
            return {
                "success": True,
                "cart": data.get("cart", data)  # fallback if "cart" not explicitly returned
            }

        except Exception as e:
            # Ensure AI always gets structured error
            return {
                "success": False,
                "message": "Unexpected error while updating cart items",
                "errors": [str(e)]
            }

    async def removeCartline_items(self,  cart_id: str, line_items: List[Dict[str, str]])  -> Dict[str, Any]:
        await self.store.init_handle_id_table()
        """
        Remove one or more line items from a shopping cart.

        Args:
            cart_id (str): Unique identifier of the cart from which items need to be removed.
            line_items (List[Dict[str, str]]): 
                A list of dictionaries, where each dictionary must include:
                    - "handle" (str): The unique product handle.
                    - "variant" (str): The variant title or identifier.

                Example:
                [
                    {
                        "handle": "anycubic-full-metal-i3-mega-3d-printer-with-ultrabase-heatbed-and-3-5-inch-touch-screen",
                        "variant": "Default Title"
                    },
                    {
                        "handle": "3-5-inch-touch-screen",
                        "variant": "Samsung"
                    }
                ]

        Returns:
            dict: A structured response with one of the following formats:
                - On success:
                    {
                        "success": True,
                        "cart": { ...updated cart object... }
                    }
                - On failure:
                    {
                        "success": False,
                        "message": "Cannot remove product(s) from your cart",
                        "errors": [ ...list of error messages... ]
                    }

        Notes:
            - This function is designed for AI/MCP execution, ensuring deterministic input/output.
            - All errors are returned as structured JSON, not raw exceptions.
        """
        try:
            # Call store method to remove line items
            data = await self.store.removeCartLineItems(cart_id, line_items)

            # Handle failure
            if not data:
                return {
                    "success": False,
                    "message": "Cannot remove product(s) from your cart Try Again Later",
                    "errors": ["Unknown error - empty response from store"]
                }

            # Handle store-level user errors
            if "userErrors" in data and data["userErrors"]:
                return {
                    "success": False,
                    "message": "Cannot remove product(s) from your cart Try Again Later",
                    "errors": data["userErrors"]
                }

            # Success response
            return {
                "success": True,

                "cart": data.get("cart", data)  # fallback if "cart" not explicitly returned
            }

        except Exception as e:
            # Ensure AI always gets structured error
            return {
                "success": False,
                "message": "Unexpected error while removing cart items Try Again Later",
                "errors": [str(e)]
            }

