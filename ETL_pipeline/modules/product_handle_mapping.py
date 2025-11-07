from models import ProductEntry
from Shopify import Shopify
from config import settings, product_dict_file_location
from typing import List
import asyncio
import pickle
import argparse
from utils.logger import get_logger

logger = get_logger("Id_to_handle_mapping")
handles = [
    "esp8266-ch340-lolin-nodemcu-wifi-development-board-pakistan",
    "red-snowboard",
]


def generate_mapping(products):
    data: dict[str, ProductEntry] = {}

    for product in products:
        handle = product.get("handle", "404")
        variants = product.get("variants", {}).get("nodes", [])

        variant_count = len(variants)
        is_single_variant = variant_count == 1
        var = {}
        for v in variants:
            var[v["title"]] = {"vid": v["id"]}
        data[handle] = ProductEntry(
            have_single_variant=is_single_variant,
            variants=var,
        )

    # save
    with open(product_dict_file_location, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


async def executor():
    parser = argparse.ArgumentParser(description="Shopify Product Map")

    parser.add_argument(
        "--load_mapping",
        action="store_true",
        help="Load Mappings from pkl to Shopify Class",
    )
    parser.add_argument(
        "--build_mapping",
        action="store_true",
        help="Build and save mapping from shopify product data",
    )
    parser.add_argument(
        "--test_mapping",
        action="store_true",
        help="Retrive some ids from pkl",
    )

    args = parser.parse_args()

    build_map = args.build_mapping
    load_map = args.load_mapping
    test_map = args.test_mapping
    
    store = Shopify(settings.store, "ProductHandleMapping")
    products = await store.fetch_mapping_products()
    # logger.info(f"Products Count {len(products)} -- {products[:10]}")

    if build_map:
        generate_mapping(products)
    if load_map:
        success = await store.init_handle_id_table()
        logger.info(f"Products Mapping loaded Successfully {success}")

    if test_map:
        with open(product_dict_file_location, "rb") as f:
            mappings = pickle.load(f)
            logger.info(f"Mappings Length - {len(mappings)}")
            for handle in handles:
                logger.info(f"Mapping - {mappings.get(handle, "Not Found")}")

if __name__ == "__main__":
    asyncio.run(executor())

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
