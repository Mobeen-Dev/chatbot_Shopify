from Shopify import Shopify
from config import settings
import asyncio 

store = Shopify(settings.store)


asyncio.run(store.fetch_all_products(True))
# print(data)
# for product in data:
#   print(product.title)
#   print(product.handle)
#   print(product.title)
#   print(product.title)
#   print(product.title)
  