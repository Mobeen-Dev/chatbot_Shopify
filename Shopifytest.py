from Shopify import Shopify
from config import settings
import asyncio
# #####################################################################
# ################## Helper Functions Start ###########################
# #####################################################################

# @ App level create a reference for Shopify API client
store = Shopify(settings.store, "ShopifyClient")

print(asyncio.run(store.get_product_by_handle("14-watt-quarter-1-resistor-pakistan")))

required_field = """

title
handle
description
vendor
productType
status
'priceRange':
  {
    'minVariantPrice':
    {
      'amount': '750000.0',
      'currencyCode': 'PKR'
    },
    'maxVariantPrice':
    {
      'amount': '750000.0',
      'currencyCode': 'PKR'
    }
  },
'totalInventory': 38,
'media':
  {
    'edges': [
    {
      'node':
      {
        'image':
        {
          'id': 'gid://shopify/ImageSource/40274466832662',
          'altText': 'Inverterzone Solar Wifi Device Solar wifi Dongle In Pakistan - Solar inverter',
          'url': 'https://cdn.shopify.com/s/files/1/0744/0764/1366/files/inverterzone-solar-wifi-device-dongle-pakistan-inverter-956.webp?v=1741256410',
          'width': 1024,
          'height': 1024
        }
      }
    }]
    

"""