from Shopify import Shopify
import json
from config import settings
import asyncio
store = Shopify(settings.store, "ShopifyClient")

async def get_order_via_OrderNumber(order_number: str):
    data = await store.fetch_order_by_name(order_number)
    if not data:
        return []
    # product = store.format_product(product)
    # print(product   )
    return Shopify.format_order_for_llm(data)




# # Example usage
order_data = asyncio.run(get_order_via_OrderNumber("#51994"))
print(order_data)

# print( ) # Example order number

# data = "+923214355751"
# print(len(data))
# encrypted_data = '0'+data[3:6] + "*" *4 + data[-3:]
# print(encrypted_data)



# # Example usage
# print(mask_email("happyever4ever@yahoo.com"))   # happ*****4ever@yahoo.com
# print(mask_email("john.doe@gmail.com"))         # joh***oe@gmail.com
# print(mask_email("ab@xyz.com"))                 # ab@xyz.com (too short, no mask)