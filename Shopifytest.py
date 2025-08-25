from Shopify import Shopify
from config import settings
import asyncio
# #####################################################################
# ################## Helper Functions Start ###########################
# #####################################################################
from config import NO_IMAGE_URL
# @ App level create a reference for Shopify API client
# store = await Shopify(settings.store, "ShopifyClient")

async def test():
  store = Shopify(settings.store, "ShopifyClient")

  list_q =  [
    {
      "qty": 7,
      "handle": "gid://shopify/ProductVariant/40516002512982"
    },
    {
      "qty": 8,
      "handle": "gid://shopify/ProductVariant/40516001267798"
    }
  ]
  return await store.create_cart(list_q)

print(asyncio.run(test()))
