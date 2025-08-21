
import re
import aiohttp
import asyncio
from logger import get_logger
from config import NO_IMAGE_URL


class Shopify:
  def __init__(self, store:dict[str,str], logger_name:str="Shopify"):
    self.ACCESS_TOKEN = store["api_secret"]
    self.API_VERSION = store["api_version"]
    self.SHOPIFY_STORE = store["store_name"]
    self.URL = f"https://{self.SHOPIFY_STORE}.myshopify.com/admin/api/{self.API_VERSION}/graphql.json"
    self.HEADER = {
      "Content-Type": "application/json",
      "X-Shopify-Access-Token": self.ACCESS_TOKEN
    }

    self.logger = get_logger(logger_name)
    
  async def fetch_all_products(self):
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
      # hasNextPage = False
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
    print(f"get_product_by_handle :: {result}")
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
            headers=self.HEADER,
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
          products(first: 249, after: $after) {
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
              images(first: 10) {
                edges {
                  node {
                    url
                  }
                }
              }
              variants(first: 249) {
                nodes {
                  inventoryItem {
                    measurement {
                      weight {
                        value
                        unit
                      }
                    }
                  }
                  displayName
                  id
                  title
                  price
                  sellableOnlineQuantity
                  image {
                    url
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
        orders(
          first: 1
          after: $startCursor
          query: $query
        ) {
        edges {
          node {
            shippingAddress {
              address1
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
      print(f"Product Status: {status}")
      if status == "ACTIVE" :
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
              "CurrencyCode": product.get("priceRangeV2", {}).get("maxVariantPrice", {}).get("currencyCode", ""),
              "max_price": product.get("priceRangeV2", {}).get("maxVariantPrice", {}).get("amount", 0), # removing .00 so that only actual price came
              "min_price": product.get("priceRangeV2", {}).get("minVariantPrice", {}).get("amount", 0),
          },
          "totalInventory": product.get("totalInventory", 0),
          "image_url": image_url,
          "variants_options": product.get("options", []),
      }
      else:
        return {
          "Note": "This product is not active or not available for sale at the moment."
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