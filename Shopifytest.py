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
      "handle": "100pcs-2-watt-5-resistor-in-pakistan-copy",
      # "variant":"Default Title",
      "variant":"1R---B2 / Red",
      "qty": 7
    },
    {
      "handle": "red-snowboard",
      # "variant":"Default Title",
      "variant":"Yellow / Pealed",
      
      "qty": 8
    }
  ]
  return await store.create_cart(list_q)
try:
  print(asyncio.run(test()))
except Exception as e:
  print("wow got error", e)