from Shopify import Shopify
from config import settings
import asyncio
# #####################################################################
# ################## Helper Functions Start ###########################
# #####################################################################
from config import NO_IMAGE_URL
# @ App level create a reference for Shopify API client
store = Shopify(settings.store, "ShopifyClient")
def format_product(product: dict) -> dict:
    """
    Function to format the product data into a specific structure.
    """
    status = product.get("status")
    print(f"Product Status: {status}")
    if status == "ACTIVE":
      edges = (product.get("media") or {}).get("edges") or []
      first_edge = edges[0] if edges else {}
      node = first_edge.get("node") or {}
      image = node.get("image") or {}
      image_url = image.get("url") or NO_IMAGE_URL

      return {
        "title": product.get("title", ""),
        "handle": product.get("handle", ""),
        "description": product.get("description", ""),
        "vendor": product.get("vendor", ""),
        "productType": product.get("productType", ""),
        
        "priceRange": {
            "CurrencyCode": product.get("priceRange", {}).get("maxVariantPrice", {}).get("currencyCode", ""),
            "max_price": product.get("priceRange", {}).get("maxVariantPrice", {}).get("amount", 0)[:-2],
            "min_price": product.get("priceRange", {}).get("minVariantPrice", {}).get("amount", 0)[:-2],
        },
        "totalInventory": product.get("totalInventory", 0),
        "image_url": image_url,
        "variants_options": product.get("options", []),
    }
    else:
      return {
        "Note": "This product is not active or available for sale at the moment."
      }

print(format_product(asyncio.run(store.get_product_by_handle("line-following-robot-2wd-with-l298"))))

