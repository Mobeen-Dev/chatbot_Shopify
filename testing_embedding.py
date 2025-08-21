from Shopify import Shopify
import json
from config import settings
import asyncio
store = Shopify(settings.store, "ShopifyClient")

async def get_order_via_OrderNumber(order_number: str) -> str:
    product = await store.fetch_order_by_name(order_number)
    if not product:
        return json.dumps({"error": "Product not found."})
    # product = store.format_product(product)
    return str(product)

print(asyncio.run(get_order_via_OrderNumber("#1234")) ) # Example order number