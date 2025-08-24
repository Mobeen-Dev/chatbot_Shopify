from Shopify import Shopify
from config import settings
import asyncio
# #####################################################################
# ################## Helper Functions Start ###########################
# #####################################################################
from config import NO_IMAGE_URL
# @ App level create a reference for Shopify API client
store = Shopify(settings.store, "ShopifyClient")

async def test():
  
  mutation = """
    mutation {
      cartCreate(
        input: {lines: [{quantity: 1, merchandiseId: "gid://shopify/ProductVariant/50399177539862"}], buyerIdentity: {email: "example@example.com", countryCode: CA, deliveryAddressPreferences: {oneTimeUse: false, deliveryAddress: {address1: "150 Elgin Street", address2: "8th Floor", city: "Ottawa", province: "Ontario", country: "CA", zip: "K2P 1L4"}}, preferences: {delivery: {deliveryMethod: PICK_UP}}}, attributes: {key: "cart_attribute", value: "This is a cart attribute"}}
      ) {
        cart {
          id
          checkoutUrl
          createdAt
          updatedAt
          lines(first: 10) {
            edges {
              node {
                id
                merchandise {
                  ... on ProductVariant {
                    id
                  }
                }
              }
            }
          }
          buyerIdentity {
            deliveryAddressPreferences {
              __typename
            }
            preferences {
              delivery {
                deliveryMethod
              }
            }
          }
          attributes {
            key
            value
          }
          cost {
            totalAmount {
              amount
              currencyCode
            }
            subtotalAmount {
              amount
              currencyCode
            }
            totalTaxAmount {
              amount
              currencyCode
            }
            totalDutyAmount {
              amount
              currencyCode
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
  """
  var = {}
  return await store.send_storefront_mutation(mutation, var)

print(asyncio.run(test()))
