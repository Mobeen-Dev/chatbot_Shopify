from Shopify import Shopify
from config import settings
import asyncio
from pprint import pprint
# #####################################################################
# ################## Helper Functions Start ###########################
# #####################################################################

from config import no_image_url

# @ App level create a reference for Shopify API client
# store = await Shopify(settings.store, "ShopifyClient")

async def test():
  store = Shopify(settings.store, "ShopifyClient")
  await store.init_handle_id_table()
  # ps = await store.get_product_by_handle("100pcs-2-watt-5-resistor-in-pakistan-copy")
  # return store.format_product(ps)
  
  list_q =  [
    {
      "handle": "100pcs-2-watt-5-resistor-in-pakistan-copy",
      # "variant":"Default Title",
      "variant":"2.2R---B3 / Yellow",
      "quantity": 7
    },
    # {
    #   "handle": "red-snowboard",
    #   # "variant":"Default Title",
    #   "variant":"Yellow / Pealed --",
      
    #   "quantity": 8
    # }
  ]
  # return await store.query_cart("gid://shopify/Cart/hWN2Hiq8ybacnqpIHoZgfFid?key=84eda6e4b4dc9ac81376863649d5504c") 
  # return await store.create_cart(list_q)
  id = await store.create_cart(list_q)
  id = id["id"]
  data = await store.addCartLineItems(id, [{ "quantity": 1,  "handle": "esp8266-ch340-lolin-nodemcu-wifi-development-board-pakistan", "variant":"Default Title"}  ])
  data = data["checkoutUrl"]
  print("Passed addCartLineItems")
  print(data,"\n\n")
  data = await store.updateCartLineItems(id,[{  "handle": "red-snowboard", "variant":"Yellow / Pealed", "quantity": 128}])
  data = data["checkoutUrl"]
  print(data,"\n\n")
  return await store.removeCartLineItems(id,[{"handle": "red-snowboard", "variant":"Yellow / Pealed"}])
try:
  print(asyncio.run(test()))
except Exception as e:
    print("Caught:", e)   # prevents full traceback
    
    
