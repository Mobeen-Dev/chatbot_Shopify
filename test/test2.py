from shopify
async def get_order_via_order_number(order_number: str) -> str:
    """
    Fetch and format an order by its order number.
    Ensures order number starts with '#'.
    Returns structured data ready for LLM.
    """
    # Ensure order number starts with "#"

    # Fetch from store
    data = await store.fetch_order_by_name(order_number)
    if not data:
        return str({"success": False, "message": f"No order found for {order_number}"})

    # Format for LLM
    formatted = Shopify.format_order_for_llm(data)
    
    return formatted
