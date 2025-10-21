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
    return await store.fetch_mapping_products()
    await store.init_handle_id_table()
    return store.id_table


# print(asyncio.run(test()))

async def generate_mapping():
    products = await test()
    data : dict[str,ProductEntry] = {}

    for product in products:
        handle = product.get("handle","404")
        variants = product.get("variants",{}).get("nodes",[])

        variant_count  = len(variants)
        is_single_variant = variant_count==1
        var = {}
        for v in variants:
            var[v["title"]] = {"vid": v["id"]}
        data[handle] = ProductEntry(
            have_single_variant= is_single_variant,
            variants=var,
        )


    # save
    with open("bucket/products.pkl", "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

# if __name__ == "__main__":
#     asyncio.run(generate_mapping())

# load
with open("bucket/products.pkl", "rb") as f:
    dataw = pickle.load(f)
    print(len(dataw))
    print((dataw["esp8266-ch340-lolin-nodemcu-wifi-development-board-pakistan"]))
    print("\n\n\n\n")
    print((dataw["red-snowboard"]))


# Retrival Samples:

#                                Uni Variant Product

#  ProductEntry(
#     "have_single_variant=True",
#     "variants="{
#        "Default Title":{
#           "vid":"gid://shopify/ProductVariant/41571880042582"
#        }
#     }
# )

#                                Multi Variant Product

#  ProductEntry(
#     "have_single_variant=False",
#     "variants="{
#        "1R---B2 / Yellow":{
#           "vid":"gid://shopify/ProductVariant/42394067566678"
#        },
#        "1R---B2 / Red":{
#           "vid":"gid://shopify/ProductVariant/42394067632214"
#        },
#        "1.5R---B2 / Yellow":{
#           "vid":"gid://shopify/ProductVariant/42394067697750"
#        },
#        "1.5R---B2 / Red":{
#           "vid":"gid://shopify/ProductVariant/42394067763286"
#        },
#        "2.2R---B3 / Yellow":{
#           "vid":"gid://shopify/ProductVariant/42394067828822"
#        },
#        "2.2R---B3 / Red":{
#           "vid":"gid://shopify/ProductVariant/42394067894358"
#        },
#        "2.7R---B4 / Yellow":{
#           "vid":"gid://shopify/ProductVariant/42394067959894"
#        },
#        "2.7R---B4 / Red":{
#           "vid":"gid://shopify/ProductVariant/42394068025430"
#        },
#        "3.3R---B5 / Yellow":{
#           "vid":"gid://shopify/ProductVariant/42394068090966"
#        },
#        "3.3R---B5 / Red":{
#           "vid":"gid://shopify/ProductVariant/42394068156502"
#        },
#        "3.9R---B6 / Yellow":{
#           "vid":"gid://shopify/ProductVariant/42394068222038"
#        },
#        "3.9R---B6 / Red":{
#           "vid":"gid://shopify/ProductVariant/42394068287574"
#        }
#     }
#  )
