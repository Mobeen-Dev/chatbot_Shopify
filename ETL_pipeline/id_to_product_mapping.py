from Shopify import Shopify
import asyncio
import os
import pickle
import json
from config import settings

store = Shopify(settings.store)


async def test():
    products = await store.fetch_all_products()
    # print(products[:12])
    formatted_product = {}
    for product in products:
        formatted_product[product["id"]] = store.format_product(product, True)

    with open("data.pkl", "wb") as f:
        pickle.dump(formatted_product, f, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    asyncio.run(test())
