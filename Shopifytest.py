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
  await store.init_handle_id_table()
  list_q =  [
    {
      "qty": 7,
      "handle": "100pcs-2-watt-5-resistor-in-pakistan-copy"
    },
    {
      "qty": 8,
      "handle": "red-snowboard"
    }
  ]
  return await store.create_cart(list_q)
try:
  print(asyncio.run(test()))
except Exception as e:
  print("wow got error", e)