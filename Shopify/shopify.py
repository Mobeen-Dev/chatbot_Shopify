
import re
import aiohttp
import asyncio
from typing import List, Dict
from logger import get_logger
from config import NO_IMAGE_URL, llm_model, product_dict_file_location
from models import ProductEntry
import asyncio
import pickle
from concurrent.futures import ThreadPoolExecutor

class Shopify:
  def __init__(self, store:dict[str,str], logger_name:str="Shopify"):
    self.__ACCESS_TOKEN = store["api_secret"]
    self.__STOREFRONT_ACCESS_TOKEN = store["storefront_secret"]
    self.__API_VERSION = store["api_version"]
    self.__SHOPIFY_STORE = store["store_name"]
    self.URL = f"https://{self.__SHOPIFY_STORE}.myshopify.com/admin/api/{self.__API_VERSION}/graphql.json"
    self.__HEADER = {
      "Content-Type": "application/json",
      "X-Shopify-Access-Token": self.__ACCESS_TOKEN
    }
    self.__id_table = {"state":"not_build"}  
    self.logger = get_logger(logger_name)
  
  async def init_handle_id_table(self) -> bool:
    try:
      self.__id_table = await self.load_handle_id_table()
      return True
    except Exception:
      return False  
  
  async def load_handle_id_table(self) -> dict[str,str]:
    def load_data():
      with open(product_dict_file_location, "rb") as f:
        products = pickle.load(f)
        return products
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
      return await loop.run_in_executor(pool, load_data)
  
  async def send_storefront_mutation(self, mutation: str, variables: dict, receiver: str = "child"):
    URL = f"https://{self.__SHOPIFY_STORE}.myshopify.com/api/{self.__API_VERSION}/graphql.json"
    HEADER = {
      "Content-Type": "application/json",
      "X-Shopify-Storefront-Access-Token": self.__STOREFRONT_ACCESS_TOKEN
    }
    try:
      async with aiohttp.ClientSession() as session:
        async with session.post(
            URL,
            headers=HEADER,
            json={"query": mutation, "variables": variables}
        ) as resp:
          resp.raise_for_status()
          result = await resp.json()
      
      # 3. Top-level GraphQL errors
      if "errors" in result:
        await asyncio.sleep(25)
        return await self.send_storefront_mutation(mutation, variables, receiver)
      
      data = result.get("data")
      if not data:
        raise RuntimeError(f"No 'data' field in response: {result}")
      if receiver == "# Some Defualt Json Mining #":
        ps = data.get("productSet") or {}
        if ps is None:
          pass
          # Could be completely null if the mutation itself wasn't found, or input invalid
          # raise RuntimeError(f"No 'productSet' returned in response: {result}")
        
        # 4. Collect userErrors on the root and operation
        root_errors = ps.get("userErrors") or []
        op = ps.get("productSetOperation") or {}
        op_errors = op.get("userErrors") or []
        
        if root_errors:
          product_handle = ""
          code = root_errors[0].get("code")

          if code == 'HANDLE_NOT_UNIQUE':
            msg = root_errors[0]['message']
            match = re.search(r"Handle '([^']+)'", msg)
            if match:
              product_handle = match.group(1)
              await self.handle_product_duplication(product_handle)
              return await self.send_graphql_mutation(mutation, variables, receiver)
              
          
        if op_errors:
          pass
          # raise RuntimeError(f"User errors: {op_errors}"
        
        # 5. Success — return the productSet payload
        return ps
      return result
    except Exception as err:
      self.logger.exception(str(err))
      return {}
  
  def handle_to_id(self, handle:str, variant_title:str):
    obj:ProductEntry = self.__id_table.get(handle, {})  # type: ignore
    if obj.have_single_variant :
      return obj.variants["Default Title"]["vid"], ""
    try:
      vid = obj.variants[variant_title]["vid"]
      return vid, ""
    except KeyError :
      return None, obj.variants.keys() # variants titles
  
  async def create_cart(self, items: list[dict[str, str | int]], session_id:str="default"): # [ {"handle": "product-alpha", "variant":"Default Title", "qty" : 123 } ]
    # The amount, before taxes and cart-level discounts, for the customer to pay.
    mutation = """
    mutation cartCreate($lines: [CartLineInput!]!, $buyerIdentity: CartBuyerIdentityInput, $attributes: [AttributeInput!], $note: String) {
      cartCreate(
        input: {lines: $lines, buyerIdentity: $buyerIdentity, attributes: $attributes, note: $note}
      ) {
      cart {
        cost {
          subtotalAmount {
            amount
            currencyCode
          }
          subtotalAmountEstimated
        }

        id
        checkoutUrl
        createdAt
        updatedAt
        lines(first: 249) {
          edges {
            node {
              quantity
              id
              merchandise {
                ... on ProductVariant {
                  id
                  title
                  price {
                    amount
                    currencyCode
                  }
                  product {
                    title
                  }
                }
              }
            }
          }
        }
        buyerIdentity {
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
        }
      }
      userErrors {
        field
        message
      }
    }
  }
  """
    lines = []
    variant_error = False
    errors = []
    
    for obj in items:
      
      handle = str(obj["handle"])
      variant = str(obj["variant"])

      merchandise_id, message = self.handle_to_id(handle, variant)
      qty = int(obj["quantity"])
      if merchandise_id:
          lines.append({
              "quantity": qty,
              "merchandiseId": merchandise_id
          })
      else:
        variant_error = True
        errors.append({
          "handle": handle,
          "message": "Selected Variant doesnot exist. Please select one from below options.",
          "options":message
        })
            
    if variant_error:
      raise KeyError(str(errors))

    variables = {
      "lines": lines,
      # "buyerIdentity": {
      #   "email": "info@digilog.pk",
      #   "countryCode": "PK",
      #   "deliveryAddressPreferences": {
      #     "oneTimeUse": False,
      #     "deliveryAddress": {
      #       "address1": "13Th Regal chowk, Shahrah-e-Quaid-e-Azam, Mozang Chungi",
      #       "address2": "",
      #       "city": "Lahore",
      #       "province": "Pubjab",
      #       "country": "PK",
      #       "zip": "54000"
      #     }
      #   },
      #   "preferences": {
      #     "delivery": {
      #       "deliveryMethod": "PICK_UP"
      #     }
      #   }
      # },
      "attributes": [
        {
          "key": "Chat #",
          "value": f"{session_id}"
        }
      ],
      "note" : "This order was created with the help of Ai."
    }
    result = await self.send_storefront_mutation(mutation, variables)
    cart = result.get("data",{}).get("cartCreate",{}).get("cart",{})
    # print(variables,"\n\n")
    return self.format_cart(cart, pretify_line_items=True)

  async def query_cart(self, id:str, dict_format=False) -> dict:
    query = """
      query getCart($id: ID!) {
        cart(id: $id) {
          note
          cost {
            subtotalAmount {
              amount
              currencyCode
            }
            subtotalAmountEstimated
          }

          id
          checkoutUrl
          createdAt
          updatedAt
          lines(first: 249) {
            edges {
              node {
                quantity
                id
                merchandise {
                  ... on ProductVariant {
                  id
                  title
                  price {
                    amount
                    currencyCode
                  }
                  product {
                    title
                  }
                  }
                }
              }
            }
          }

          buyerIdentity {
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
          }
        }
      }

    """
    variables = {
      "id": id,
    }
    result = await self.send_storefront_mutation(query, variables)
    cart = result.get("data",{}).get("cart",{})
    
    # print(cart,"\n\n")
    return self.format_cart(cart, dict_format, pretify_line_items=True)

  async def addCartLineItems(self, cartId:str, lineItems:List[dict[str,str|int]]):
    mutation = """
      mutation cartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
        cartLinesAdd(cartId: $cartId, lines: $lines) {
        cart {
          cost {
            subtotalAmount {
              amount
              currencyCode
            }
            subtotalAmountEstimated
          }

          id
          checkoutUrl
          createdAt
          updatedAt
          lines(first: 249) {
            edges {
              node {
                quantity
                id
                merchandise {
                  ... on ProductVariant {
                    id
                  title
                  price {
                    amount
                    currencyCode
                  }
                  product {
                    title
                  }
                  }
                }
              }
            }
          }
          buyerIdentity {
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
          }
        }
        userErrors {
          field
          message
        }
        warnings {
          target
          code
          message
        }
      }
    }
  """
    
    lines = []
    variant_error = False
    errors = []
    
    for obj in lineItems:
      
      handle = str(obj["handle"])
      variant = str(obj["variant"])
      qty = int(obj["quantity"])

      merchandise_id, message = self.handle_to_id(handle, variant)
      
      if merchandise_id:
          lines.append({
              "quantity": qty,
              "merchandiseId": merchandise_id
          })
      else:
        variant_error = True
        errors.append({
          "handle": handle,
          "message": "Selected Variant doesnot exist. Please select one from below options.",
          "options":message
        })
            
    if variant_error:
      raise KeyError(str(errors))

    variables = {
      "cartId": cartId,
      "lines": lines
    }
    result = await self.send_storefront_mutation(mutation, variables)
    
    cart = result.get("data",{}).get("cartLinesAdd",{}).get("cart",{})
    # print(cart,"\n\n")
    return self.format_cart(cart, pretify_line_items=True)

  async def removeCartLineItems(self, cartId:str, lineItems:List[dict[str,str]]):
    cart = await self.query_cart(cartId, True)
    # print("$$$$$ cart",cart,"\n\n\n\n")

    cart_lines = cart["lineItems"]
    mutation = """
      mutation cartLinesRemove($cartId: ID!, $lineIds: [ID!]!) {
        cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
        cart {
          cost {
            subtotalAmount {
              amount
              currencyCode
            }
            subtotalAmountEstimated
          }

          id
          checkoutUrl
          createdAt
          updatedAt
          lines(first: 249) {
            edges {
              node {
                quantity
                id
                merchandise {
                  ... on ProductVariant {
                    id
                  title
                  price {
                    amount
                    currencyCode
                  }
                  product {
                    title
                  }
                  }
                }
              }
            }
          }
          buyerIdentity {
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
          }
        }
        userErrors {
          field
          message
        }
        warnings {
          target
          code
          message
        }
      }
    }
  """
    
    lines = []
    variant_error = False
    errors = []

    for obj in lineItems:      
      handle = obj["handle"]
      variant = obj["variant"]

      merchandise_id, message = self.handle_to_id(handle, variant)
      # print("$$$$$ mid",merchandise_id,"\n\n\n\n")
      cart_line_id = cart_lines.get(merchandise_id, None)
      # print("$$$$$ cli",cart_line_id,"\n\n\n\n")
      
      if cart_line_id:
          lines.append( cart_line_id["id"] )
      else:
        variant_error = True
        errors.append({
          "handle": handle,
          "message": "Selected Variant doesnot exist. Please select one from below options.",
          "options":message
        })
            
    if variant_error:
      raise KeyError(str(errors))
      
    variables = {
      "cartId": cartId,
      "lineIds": lines
    }
    result = await self.send_storefront_mutation(mutation, variables)
    
    cart = result.get("data",{}).get("cartLinesRemove",{}).get("cart",{})
    # print(cart,"\n\n")
    return self.format_cart(cart, pretify_line_items=True)
  
  async def updateCartLineItems(self, cartId:str, lineItems:List[dict[str,str|int]]):
    cart = await self.query_cart(cartId, True)
    cart_lines = cart["lineItems"]
    mutation = """
      mutation cartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
        cartLinesUpdate(cartId: $cartId,  lines: $lines) {
        cart {
          cost {
            subtotalAmount {
              amount
              currencyCode
            }
            subtotalAmountEstimated
          }

          id
          checkoutUrl
          createdAt
          updatedAt
          lines(first: 249) {
            edges {
              node {
                quantity
                id
                merchandise {
                  ... on ProductVariant {
                    id
                  title
                  price {
                    amount
                    currencyCode
                  }
                  product {
                    title
                  }
                  }
                }
              }
            }
          }
          buyerIdentity {
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
          }
        }
        userErrors {
          field
          message
        }
        warnings {
          target
          code
          message
        }
      }
    }
  """
    
    lines = []
    variant_error = False
    errors = []

    for obj in lineItems:      
      handle = str(obj["handle"])
      variant = str(obj["variant"])

      merchandise_id, message = self.handle_to_id(handle, variant)
      cart_line_id = cart_lines.get(merchandise_id, None)
      if cart_line_id:
          lines.append({
            "id": cart_line_id["id"],
            "quantity": obj["quantity"],
            "merchandiseId": merchandise_id
          })
      else:
        variant_error = True
        errors.append({
          "handle": handle,
          "message": "Selected Variant doesnot exist. Please select one from below options.",
          "options":message
        })
            
    if variant_error:
      raise KeyError(str(errors))
      
    variables = {
      "cartId": cartId,
      "lines": lines
    }
    result = await self.send_storefront_mutation(mutation, variables)
    
    cart = result.get("data",{}).get("cartLinesUpdate",{}).get("cart",{})
    # print(cart,"\n\n")
    return self.format_cart(cart, pretify_line_items=True)

  async def fetch_mapping_products(self):
    all_products:list = []
    query= self.mapping_products_query()
    query_params={
      "after": None
    }

    hasNextPage = True
    while hasNextPage :
      try:
        result = await self.send_graphql_mutation(query, query_params, "GetProductsAndVariants")
        result = result['data']['products']
      except Exception as e:  # noqa: F841
        await asyncio.sleep(25)
        continue
      # Pagination Control
      pageInfo = result["pageInfo"]
      hasNextPage = pageInfo["hasNextPage"]
      # hasNextPage = False
      query_params['after'] = pageInfo["endCursor"]
      # Product Handling Logic
      products:list = result["nodes"]
      # for product in products:
      #   product["admin_graphql_api_id"] = product["id"]
      #   product["id"] = self.extract_id_from_gid(product["id"])
      all_products.extend(products)
    return all_products   

  async def fetch_all_products(self, test_mode=False):
    all_products:list = []
    query= self.all_products_query()
    query_params={
      "after": None
    }

    hasNextPage = True
    while hasNextPage :
      try:
        result = await self.send_graphql_mutation(query, query_params, "GetProductsAndVariants")
        result = result['data']['products']
      except Exception as e:  # noqa: F841
        await asyncio.sleep(25)
        continue
      # Pagintion Control
      pageInfo = result["pageInfo"]
      hasNextPage = pageInfo["hasNextPage"]
      if test_mode:
        hasNextPage = False
      query_params['after'] = pageInfo["endCursor"]
      # Product Handling Logic
      products:list = result["nodes"]
      for product in products:
        product["admin_graphql_api_id"] = product["id"]
        product["id"] = self.extract_id_from_gid(product["id"])
      all_products.extend(products)
    return all_products   

  async def fetch_product_by_id(self, product_id: int):
    product_gid = f"gid://shopify/Product/{product_id}"
    
    query = """
    query GetProductById($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        description
        descriptionHtml
        vendor
        productType
        status
        createdAt
        updatedAt
        tags
        options {
          name
          values
        }
        priceRangeV2 {
          minVariantPrice {
            amount
            currencyCode
          }
          maxVariantPrice {
            amount
            currencyCode
          }
        }
        compareAtPriceRange {
          minVariantCompareAtPrice {
            amount
            currencyCode
          }
          maxVariantCompareAtPrice {
            amount
            currencyCode
          }
        }
        totalInventory
        variants(first: 249) {
          edges {
            node {
              id
              title
              sku
              taxable
              price
              compareAtPrice
              inventoryQuantity
              availableForSale
              barcode
              createdAt
              updatedAt
              inventoryPolicy
              inventoryItem {
                id
                tracked
                measurement {
                  weight {
                    value
                    unit
                  }
                }
                unitCost {
                  amount
                  currencyCode
                }
                countryCodeOfOrigin
                harmonizedSystemCode
                requiresShipping
              }
              image {
                width
                height
                id
                altText
                url
                width
                height
              }
            }
          }
        }
        images(first: 50) {
          edges {
            node {
              id
              altText
              url
              width
              height
            }
          }
        }
        media(first: 20) {
          edges {
            node {

              ... on MediaImage {
                image {
                  id
                  altText
                  url
                  width
                  height
                }
              }
            }
          }
        }


      }
    }

    """
    variables = {"id": product_gid}
    self.logger.info(f"Fetching product by id {product_gid}")
    response = await self.send_graphql_mutation(query, variables, "product")
    
    if errs := response.get("errors"):
      self.logger.error(f"fetch_product_by_id::GraphQL errors: {errs}")  # optional
      return None
      
    return response.get("data", {}).get("product")   
  
  async def fetch_order_by_name(self, order_name: str):
    query = self.order_query_by_order_name()
    
    after_cursor = None  # first page has no cursor
    query_string = f"name:{order_name} "
    
    variables = { 
      "startCursor": after_cursor,
      "query": query_string
    }
    self.logger.info(f"Fetching order by Name: {order_name}")
    response = await self.send_graphql_mutation(query, variables, "OrderByName")
    
    # drill into the GraphQL data safely
    orders_conn = response.get("data", {}).get("orders", {})
    edges = orders_conn.get("edges", [])
    nodes = []
    for edge in edges:
        node = edge.get("node")
        if node is not None:
          nodes.append(node)

    return nodes  
  
  async def product_id_by_handle(self, product_handle: str):
    
    query = self.product_query_by_identifier()
    query_params = {
      "identifier": {
        "handle": f"{product_handle}"
      }
    }
    result = await self.send_graphql_mutation(query, query_params, "product")
    product = result.get("data", {}).get("product",{})
    id = product.get("id", None)
    
    return id
    # self.logger.info(str(result))
  
  async def get_product_by_handle(self, product_handle: str):
    
    query = self.full_product_query_by_identifier()
    query_params = {
      "identifier": {
        "handle": f"{product_handle}"
      }
    }
    result = await self.send_graphql_mutation(query, query_params, "product")
    # print(f"get_product_by_handle :: {result}")
    product = result.get("data", {}).get("product",{})
    if product:
      id = product.get("id", None)
      
      return product
    else:
      return {"error": "Product not found."}
    # self.logger.info(str(result))
  
  async def delete_product_by_id(self, product_graphql_id: str):
   
    mutation = self.product_delete_mutation()
    query_params = {
      "id":product_graphql_id,
    }
    result = await self.send_graphql_mutation(mutation, query_params, "id")  # noqa: F841
    # self.logger.info(str(result))
  
  async def send_graphql_mutation(self, mutation: str, variables: dict, receiver: str = "child"):

    try:
      async with aiohttp.ClientSession() as session:
        async with session.post(
            self.URL,
            headers=self.__HEADER,
            json={"query": mutation, "variables": variables}
        ) as resp:
          resp.raise_for_status()
          result = await resp.json()
      
      # 3. Top-level GraphQL errors
      if "errors" in result:
        await asyncio.sleep(25)
        return await self.send_graphql_mutation(mutation, variables, receiver)
      
      data = result.get("data")
      if not data:
        raise RuntimeError(f"No 'data' field in response: {result}")
      if receiver == "child":
        ps = data.get("productSet") or {}
        if ps is None:
          pass
          # Could be completely null if the mutation itself wasn't found, or input invalid
          # raise RuntimeError(f"No 'productSet' returned in response: {result}")
        
        # 4. Collect userErrors on the root and operation
        root_errors = ps.get("userErrors") or []
        op = ps.get("productSetOperation") or {}
        op_errors = op.get("userErrors") or []
        
        if root_errors:
          product_handle = ""
          code = root_errors[0].get("code")

          if code == 'HANDLE_NOT_UNIQUE':
            msg = root_errors[0]['message']
            match = re.search(r"Handle '([^']+)'", msg)
            if match:
              product_handle = match.group(1)
              await self.handle_product_duplication(product_handle)
              return await self.send_graphql_mutation(mutation, variables, receiver)
              
          
        if op_errors:
          pass
          # raise RuntimeError(f"User errors: {op_errors}"
        
        # 5. Success — return the productSet payload
        return ps
      return result
    except Exception as err:
      self.logger.exception(str(err))
      return {}
    
  async def handle_product_duplication(self, product_handle:str):
    product_id = await self.product_id_by_handle(product_handle)
    if product_id:
      await self.delete_product_by_id(product_id)

  async def sync_product(self, p_id: int = 404, child_p_id: int = 404):
    product = await self.fetch_product_by_id(p_id) or {}
    # print(product)
    query_params = self.parse_into_query_params(product, f"gid://shopify/Product/{child_p_id}")
    updated_query_params = self.update_params(query_params)
    # query_params = parse_response_to_query(product, "gid://shopify/Product/8872805433568") #Update
    mutation = self.product_clone_update_mutation(child_p_id != 404)

    new_product = await self.send_graphql_mutation(mutation, updated_query_params)
    return new_product
    # print(wow)
  
  async def set_product_status(self, id: int = 404, status: str = "DRAFT"):
    mutation = self.product_status_update_mutation()
    query_params = {
      "id": f"gid://shopify/Product/{id}",
      "status": status
    }
    # query_params = parse_response_to_query(product, "gid://shopify/Product/8872805433568") #Update
    result = await self.send_graphql_mutation(mutation, query_params)  # noqa: F841
    # self.logger.info(str(result))
  
  async def update_product(self, query_params):
    mutation = self.product_clone_update_mutation()
    # query_params = self.parse_into_query_params(product_data, f"gid://shopify/Product/{child_pid}")
    updated_product = await self.send_graphql_mutation(mutation, query_params)
    return updated_product
  
  async def create_product(self, query_params):
    mutation = self.product_clone_update_mutation(False) # False for creating Product
    new_product = await self.send_graphql_mutation(mutation, query_params)
    return new_product
  
  async def make_new_customer(self, customer: dict):
    mutation = self.customer_create_mutation()
    address = customer["default_address"]
    variables = {
      "input": {
        "firstName": customer["first_name"],
        "lastName": customer["last_name"],
        "email": customer["email"],
        "phone": customer["phone"],
        "addresses": [
          {
            "address1": address["address1"],
            "phone": address["phone"],
            "city": address["city"],
            "country": address["country"],
            "zip": address["zip"],
            
          }
        ]
      }
    }

    try:
      data = await self.send_graphql_mutation(mutation, variables, "Parent")
      new_customer = data["data"]["customerCreate"]["customer"]
      if new_customer:
        # print("id ay gayi")
        return new_customer["id"]
      else:
        return await self.process_customer(customer)
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
      self.logger.warning(f"fetch_product_by_id :: Failed to create new customer ::{e}")
      return None
  
  async def process_customer(self, customer, phone_no=None):
    query = """
    query GetCustomersByContact(
    $first: Int = 100,
    $after: String,
    $filter: String!
    ) {
      customers(first: $first, after: $after, query: $filter) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
        id
        firstName
        lastName
        createdAt
        defaultEmailAddress{
          emailAddress
        }
        defaultPhoneNumber{
          phoneNumber
        }

      }
      }
    }
    """
    variables = {
      "first": 5,
      "after": None,
    }

    filters = ""
    mail = customer.get("email")
    phone = customer.get("phone")
    if mail:
      filters += f"email:{mail}"
    if phone:
      if filters != "":
        filters += " OR "
      filters += f"phone:{phone}"

    if phone_no:
      if filters != "":
        filters += " OR "
      filters += f"phone:{phone_no}"

    variables["filter"] = filters
    
    try:
      data = await self.send_graphql_mutation(query, variables, "Parent")
      data = data["data"]["customers"]["nodes"]

      for node in data:
        node_email = node.get("defaultEmailAddress", {})
        if node_email:
          node_email = node_email.get("emailAddress", None)
        node_phone_number = node.get("defaultPhoneNumber",{})
        if node_phone_number:
          node_phone_number = node_phone_number.get("phoneNumber", None)
        if mail and node_email == mail:
          return node["id"]
        elif node_phone_number == phone and phone:
          return node["id"]
        elif node_phone_number == phone_no and phone_no:
          return node["id"]
      
      return await self.make_new_customer(customer)
    
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
      self.logger.warning(f"process_customer :: {e}")
      return None
    except Exception as e:
      self.logger.warning(f"process_customer :: Crash ::{e}")
      return None
  
  @staticmethod
  def process_shipping_address(shipping_address: dict):
    return {
      "address1": shipping_address["address1"],
      "address2": shipping_address["address2"],
      "city": shipping_address["city"],
      "company": shipping_address["company"],
      "countryCode": shipping_address["country_code"],
      "firstName": shipping_address["first_name"],
      "lastName": shipping_address["last_name"],
      "phone": shipping_address["phone"],
      "provinceCode": shipping_address["province_code"],
      "zip": shipping_address["zip"],
    }
  
  @staticmethod
  def draft_order_mutation():
    return """
      mutation draftOrderCreate($input: DraftOrderInput!) {
        draftOrderCreate(input: $input) {
          draftOrder {
            id
            name
          }
        }
      }
      """
  
  @staticmethod
  def extract_id_from_gid(gid: str) -> str:
    """
    Extract the ID from a Shopify GID string.

    Args:
        gid: Shopify GID string like 'gid://shopify/ProductVariant/40516000219222'

    Returns:
        The extracted ID as string: '40516000219222'

    """
    # Method 1: Using your suggested approach (reverse iteration)
    for i in range(len(gid) - 1, -1, -1):
      if gid[i] == '/':
        return gid[i + 1:]
    
    # Fallback: if no '/' found, return the original string
    return gid
  
  @staticmethod
  def update_params(query_params):
    variants = query_params.get("input", {}).get("variants", [])
    for variant in variants:
      del variant['title']

    return query_params
  
  @staticmethod
  def product_clone_update_mutation(update: bool = True):
    if update:
      return """
            mutation ProductCopy($input: ProductSetInput!, $synchronous: Boolean!, $identifier: ProductSetIdentifiers!) {
              productSet(input: $input, synchronous: $synchronous, identifier: $identifier) {
                product {
                  id
                  variants(first: 249) {
                    edges {
                      node {
                        title
                        id
                        sku
                        price
                        inventoryPolicy
                        inventoryItem {
                          tracked
                        }
                      }
                    }
                  }
                }
                productSetOperation {
                  id
                  status
                  userErrors {
                    code
                    field
                    message
                  }
                }
                userErrors {
                  code
                  field
                  message
                }
              }
            }
        """
    else:
      return """
            mutation ProductCopy($input: ProductSetInput!, $synchronous: Boolean!) {
              productSet(input: $input, synchronous: $synchronous) {
                product {
                  id
                  variants(first: 249) {
                    edges {
                      node {
                        title
                        id
                        sku
                        price
                        inventoryPolicy
                        inventoryItem {
                          tracked
                        }
                      }
                    }
                  }
                }
                productSetOperation {
                  id
                  status
                  userErrors {
                    code
                    field
                    message
                  }
                }
                userErrors {
                  code
                  field
                  message
                }
              }
            }
            """
  
  # status Update
  @staticmethod
  def product_status_update_mutation():
    return """
      mutation UpdateProductStatus($id: ID!, $status: ProductStatus!) {
        productSet(
          identifier: { id: $id }
          input: { status: $status }
          synchronous: true
        ) {
          product {
            id
            title
            status
          }
          userErrors {
            field
            message
          }
        }
      }
      """
  
  @staticmethod
  def product_delete_mutation():
    return """
      mutation DeleteProduct($id: ID!) {
        productDelete(input: {id: $id }) {
          deletedProductId
        }
      }
      """
  
  @staticmethod
  def product_query_by_identifier():
    return """
      query ($identifier: ProductIdentifierInput!) {
        product: productByIdentifier(identifier: $identifier) {
          id
          handle
          title
        }
      }
      """
  
  @staticmethod
  def all_products_query():
    return """
        query GetProductsAndVariants($after: String) {
          products(first: 2, after: $after) {
            nodes {
              category {
                fullName
              }
              productType
              id
              description
              title
              vendor
              handle
              media(first: 1) {
                edges {
                  node {
                    ... on MediaImage {
                      image {
                        id
                        altText
                        url
                        width
                        height
                      }
                    }
                  }
                }
              }
              priceRangeV2 {
                minVariantPrice {
                  amount
                  currencyCode
                }
                maxVariantPrice {
                  amount
                  currencyCode
                }
              }
              totalInventory
              variants(first: 249) {
                edges {
                  node {
                    id
                    title
                    sku
                    taxable
                    price
                    compareAtPrice
                    inventoryQuantity
                    availableForSale
                    barcode
                    createdAt
                    updatedAt
                    inventoryPolicy
                    inventoryItem {
                      id
                      tracked
                      measurement {
                        weight {
                          value
                          unit
                        }
                      }
                      unitCost {
                        amount
                        currencyCode
                      }
                      countryCodeOfOrigin
                      harmonizedSystemCode
                      requiresShipping
                    }
                    image {
                      width
                      height
                      id
                      altText
                      url
                      width
                      height
                    }
                  }
                }
              }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
      """
  
  @staticmethod
  def mapping_products_query():
    return """
    query GetProductsAndVariants($after: String) {
      products(first: 249, after: $after) {
        nodes {
          id 
          title
          handle
          variants(first: 249) {
            nodes {
              id
              title
              displayName
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
  
  @staticmethod
  def customer_create_mutation() -> str:
    return """
    mutation CreateCustomer($input: CustomerInput!) {
      customerCreate(input: $input) {
        customer {
          id
          firstName
          lastName
          defaultEmailAddress{
            emailAddress
          }
          defaultPhoneNumber{
            phoneNumber
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """
  
  @staticmethod
  def full_product_query_by_identifier():
    return """
      query ($identifier: ProductIdentifierInput!) {
        product: productByIdentifier(identifier: $identifier) {
          id
          title
          handle
          description
          descriptionHtml
          vendor
          productType
          status
          createdAt
          updatedAt
          tags
          options {
            name
            values
          }
          priceRangeV2 {
            minVariantPrice {
              amount
              currencyCode
            }
            maxVariantPrice {
              amount
              currencyCode
            }
          }
          compareAtPriceRange {
            minVariantCompareAtPrice {
              amount
              currencyCode
            }
            maxVariantCompareAtPrice {
              amount
              currencyCode
            }
          }
          totalInventory
          variants(first: 249) {
            edges {
              node {
                id
                title
                sku
                taxable
                price
                compareAtPrice
                inventoryQuantity
                availableForSale
                barcode
                createdAt
                updatedAt
                inventoryPolicy
                inventoryItem {
                  id
                  tracked
                  measurement {
                    weight {
                      value
                      unit
                    }
                  }
                  unitCost {
                    amount
                    currencyCode
                  }
                  countryCodeOfOrigin
                  harmonizedSystemCode
                  requiresShipping
                }
                image {
                  width
                  height
                  id
                  altText
                  url
                  width
                  height
                }
              }
            }
          }
          media(first: 1) {
            edges {
              node {
                ... on MediaImage {
                  image {
                    id
                    altText
                    url
                    width
                    height
                  }
                }
              }
            }
          }
        }
      }
      """
  
  @staticmethod
  def order_query_by_order_name():
    return """
    query GetOrdersbyName($startCursor: String, $query: String) {
      orders(first: 1, after: $startCursor, query: $query) {
        edges {
          node {
            statusPageUrl
            customer {
              displayName
              defaultPhoneNumber {
                phoneNumber
              }
              defaultEmailAddress {
                emailAddress
              }
            }
            billingAddress {
              phone
            }
            shippingAddress {
              address1
              phone
              firstName
              lastName
            }
            displayFinancialStatus
            displayFulfillmentStatus
            totalPriceSet {
              presentmentMoney {
                amount
                currencyCode
              }
            }
            name
            lineItems(first: 200) {
              edges {
                node {
                  product {
                    title
                    handle
                    priceRangeV2 {
                      maxVariantPrice {
                        amount
                      }
                      minVariantPrice {
                        amount
                      }
                    }
                  }
                  quantity
                }
              }
            }
          }
        }
      }
    }
    """
  
  @staticmethod
  def format_order_for_llm(order_data: list) -> str:
    def mask_email(email: str) -> str:
      """Dynamically mask the local part of an email address."""
      
      local, domain = email.split("@", 1)
      length = len(local)
      country_code = domain.split(".", 1)[1]
      
      if length <= 3:
          return local + "@" + '*'*(len(domain)-len(country_code))+'.'+country_code
      
      extra_characters = '*' * (length-3)
      return local[:4]+extra_characters+ "@" + domain
    lines = []
    for order in order_data:
        customer = order.get("customer", {})
        shipping = order.get("shippingAddress", {})
        price_info = order.get("totalPriceSet", {}).get("presentmentMoney", {})

        # Order meta
        lines.append(f"OrderID: {order.get('name', '')}")
        lines.append(f"FinancialStatus: {order.get('displayFinancialStatus', '')}")
        lines.append(f"FulfillmentStatus: {order.get('displayFulfillmentStatus', '')}")
        lines.append(f"Total: {price_info.get('amount', '')} {price_info.get('currencyCode', '')}")

        # Customer
        lines.append(f"CustomerName: {customer.get('displayName', 'N/A')}")
        data = None
        
        if shipping:
          data = shipping.get('phone', None)
        
        if not data:
            _data = order.get("billingAddress", {}).get("phone", None)
            if not _data :
                _data = customer.get("defaultPhoneNumber", {}).get('phoneNumber')
            data = _data
        
        if data:
          if len(data) > 10:
            phone_number = '0'+data[3:6] + "*" *4 + data[-3:]
            lines.append(f"CustomerPhone: {phone_number}")
        mail = customer.get('defaultEmailAddress', {}).get('emailAddress', None)
        if mail:
            lines.append(f"CustomerEmail: {mask_email(mail)}")

        # Shipping
        if shipping:
          lines.append(f"ShippingAddress: {shipping.get('address1', 'N/A')}")
        else:
          lines.append("ShippingAddress: SELF_PICKUP at Store")

        # Items
        lines.append("Items:")
        line_items = order.get("lineItems", {}).get("edges", [])
        for idx, item in enumerate(line_items, start=1):
            node = item.get("node", {})
            product = node.get("product")
            quantity = node.get("quantity", 0)

            if product:
                title = product.get("title", "Unknown Product")
                price = product.get("priceRangeV2", {}).get("minVariantPrice", {}).get("amount", "0")
                lines.append(f"⇒ {title}, Qty: {quantity}, UnitPrice: {price} ^break^ ")
            else:
                lines.append(f"  - Unknown Product, Qty: {quantity}")

        lines.append("")  # blank line between orders

    return "\n".join(lines)
  
  def format_product(self, product: dict) -> dict:
      """
      Function to format the product data into a specific structure.
      """
      status = product.get("status")
      inventory = product.get("totalInventory", 0),
      if inventory == 0:
        return {
          "Note": "This product is OUT OF STOCK or not available for sale at the moment."
        }
      # print(f"Product Status: {status}")
      if status == "ACTIVE" :
        edges = (product.get("media") or {}).get("edges") or []
        first_edge = edges[0] if edges else {}
        node = first_edge.get("node") or {}
        image = node.get("image") or {}
        image_url = image.get("url") or NO_IMAGE_URL
        variants = product.get("variants", {}).get("edges", [])
        return {
          "title": product.get("title", ""),
          "handle": product.get("handle", ""),
          "description": product.get("description", ""),
          "vendor": product.get("vendor", ""),
          "productType": product.get("productType", ""),
          
          "priceRange": {
              "CurrencyCode": product.get("priceRangeV2", {}).get("maxVariantPrice", {}).get("currencyCode", ""),
              "max_price": product.get("priceRangeV2", {}).get("maxVariantPrice", {}).get("amount", 0), # removing .00 so that only actual price came
              "min_price": product.get("priceRangeV2", {}).get("minVariantPrice", {}).get("amount", 0),
          },
          "totalInventory": product.get("totalInventory", 0),
          "image_url": image_url,
          "variants_options": [variant["node"]["title"] for variant in variants]
      }
      else:
        return {
          "Note": "This product is not active or not available for sale at the moment."
        }

  def format_cart(self, cart: dict, line_items_dict:bool=False, pretify_line_items=False) -> dict:
      """
      Function to format the cart data into a specific structure.
      """
      def return_lineItems(line_items):
        lines = {}
        if line_items_dict:
          for  item in line_items:
            vid = item["node"]["merchandise"]["id"]
            lines[vid] = {
              "id":item["node"]["id"], 
              "variant_id": vid,
              "quantity":item["node"]["quantity"]
            } 
          return lines
        elif pretify_line_items:
          formatted_items = []
          for  item in line_items:
            data = item["node"]["merchandise"]
            amount = data["price"]
            product_title = data["product"]["title"]
            variant_title = data["title"]
            total_price = amount["amount"]+" "+amount["currencyCode"]
            if variant_title == "Default Title":
              variant_title = " "
            else:
              product_title += ' - '
            formatted_items.append(
              {
              "merchandise_title": product_title+variant_title,
              "quantity":item["node"]["quantity"],
              "merchandise_price":total_price
              }
            )
          
          return formatted_items
        else:
          return [
              {
                "id":item["node"]["id"], 
                "variant_id":item["node"]["merchandise"]["id"],
                "quantity":item["node"]["quantity"]
              } 
                for item in line_items
            ]
        
      try:
        # cart = _cart.get("data",{}).get("cartCreate",{}).get("cart",{})
        amount = cart["cost"]["subtotalAmount"]
        line_items = cart.get("lines",{}).get("edges",[])
        dilevery_methods = cart.get("buyerIdentity", {}).get("preferences", {}).get("delivery", {}).get("deliveryMethod", [])

        return {
          "id" : cart.get("id", ""),
          "checkoutUrl": cart.get("checkoutUrl", ""),
          
          "createdAt": cart.get("createdAt", ""),
          "updatedAt": cart.get("updatedAt", ""),
          
          "lineItems": return_lineItems(line_items),
          
          "subtotalAmount": f"{amount["amount"]} {amount["currencyCode"]}",
          
          "deliveryMethod":dilevery_methods[0],
          "userErrors": cart.get("userErrors")
          
        }
      except Exception:
        return {
          "state": "Error Arrise",
          "server_response": cart,
          "info": "The server returned an empty response because the ID you provided is incorrect. Please check the ID and try again."
        }

  def parse_into_query_params(self, product: dict, child_p_id: str = ''):
    # product = await fetch_product(product_gid)
    # print("Fetched product data:")
    
    def handle_variants(vary_items):
      variants = vary_items.split(" / ")
      variant_list = []
      
      for variant in variants:
        parent_variant = [option["name"] for option in product["options"] if variant in option.get("values", [])]
        opt = {"optionName": parent_variant[0], "name": variant}
        variant_list.append(opt)
        # {"optionName": product["options"][1]["name"], "name": variant["node"]["title"].split(' / ')[1]},
      
      return variant_list
    
    query_values = {}
    try:
      variants = product.get("variants", [])
      if variants:
        variants = variants.get("edges")  
      
      images = product["media"]["edges"]
      variant_option = None  # noqa: F841
      
      query_values = {
        "synchronous": True,
        "input": {
          "title": product["title"],
          "descriptionHtml": product["descriptionHtml"],
          "vendor": product["vendor"],
          "productType": product["productType"],
          "handle": product["handle"],
          "tags": product["tags"],
          "status": product["status"],
          
          "files": [
            {
              "filename": f"1.{image["node"]["image"]["url"].split("?", 1)[0].rpartition(".")[2]}",
              "alt": "Product image",
              "contentType": "IMAGE",
              "duplicateResolutionMode": "APPEND_UUID",
              "originalSource": image["node"]["image"]["url"].split("?", 1)[0]
            }
            for image in images
          ],
          # "productOptions":product["options"],
          "productOptions": [{"name": option["name"], 'values': [{"name": value} for value in option["values"]]} for
                            option in product["options"]],
          "variants": [
            {
              "optionValues": handle_variants(variant["node"]["title"]),
              "title": variant["node"]["title"],
              "sku": variant["node"]["sku"],
              "price": variant["node"]["price"],
              "compareAtPrice": variant["node"]["compareAtPrice"],
              "inventoryPolicy": variant["node"]["inventoryPolicy"],
              "taxable": False,
              
              "inventoryQuantities": [
                {
                  "locationId": "gid://shopify/Location/106586440049",
                  
                  "name": "available",
                  "quantity": variant["node"]["inventoryQuantity"],
                }
              ],
              "inventoryItem": {
                "tracked": variant["node"]["inventoryItem"]["tracked"],
                # "cost": 12.34,
                "requiresShipping": variant["node"]["inventoryItem"]["requiresShipping"],
                "measurement": variant["node"]["inventoryItem"]["measurement"],
              }
            }
            for variant in variants
          ]
          
        }
      }
      if child_p_id:
        query_values["identifier"] = {"id": child_p_id}
    except Exception as w:
      self.logger.error(w)
    return query_values