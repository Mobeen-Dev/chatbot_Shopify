from models import ProductEntry
from Shopify import Shopify
from config import settings
from typing import List
import asyncio
import pickle

# @ App level create a reference for Shopify API client
# store = await Shopify(settings.store, "ShopifyClient")

async def test():
  store = Shopify(settings.store, "ProductHandleMapping")
  # return await store.fetch_mapping_products()
  await store.init_handle_id_table()
  return store.id_table


print(asyncio.run(test()))

# products = asyncio.run(test())
# data : dict[str,ProductEntry] = {}

# for product in products:
#   handle = product.get("handle","404")
#   variants = product.get("variants",{}).get("nodes",[])
  
#   variant_count  = len(variants)
#   is_single_variant = variant_count==1
#   v_id = None

#   if is_single_variant:
#     v_id = variants[0].get("id")
  
#   data[handle] = ProductEntry(
#     have_single_variant= is_single_variant,
#     options=[{"variant_title": v["title"], "vid": v["id"]} for v in variants],
#     vid=v_id
#   )



# # save
# with open("bucket/products.pkl", "wb") as f:
#     pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

# # load
# with open("bucket/products.pkl", "rb") as f:
#     dataw = pickle.load(f)
#     print(len(dataw))
#     print((dataw["high-quality-s2d0s05-n960-display-ic-for-samsung-n960"].have_single_variant))