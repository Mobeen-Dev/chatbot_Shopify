# shopify_bridge/config.py
import os
import sys
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class Settings(BaseSettings):
    # === OpenAi credentials ===
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    vector_store_id: str = Field(alias="VECTOR_STORE_ID")
    
    # === Shopify Master Store credentials ===
    shopify_api_key: str = Field(alias="SHOPIFY_API_KEY")
    shopify_api_secret: str = Field(alias="SHOPIFY_API_SECRET")
    shopify_storefront_secret: str = Field(alias="SHOPIFY_STOREFRONT_API_SECRET")
    shopify_store_name: str = Field(alias="SHOPIFY_STORE_NAME")
    shopify_api_version: str = Field(alias="SHOPIFY_API_VERSION")
    
    # === Pinecone credentials ===
    pinecone_api_key: str = Field(alias="PINECONE_API_KEY")
    
    # ── helper properties ────────────────────────────
    
    @property
    def store(self) -> dict[str, str]:
        """Handy bundle for the *parent* shop."""
        return {
            "api_key": self.shopify_api_key,
            "api_secret": self.shopify_api_secret,
            "storefront_secret": self.shopify_storefront_secret,
            "store_name": self.shopify_store_name,
            "api_version": self.shopify_api_version,
        }
    
    # == Access Point == 
    origin_regex: str = Field(alias="ALLOWED_ORIGIN_REGEX")
    origins: str = Field(alias="ALLOWED_ORIGINS")
    access_token: str = Field(alias="ACCESS_TOKEN")
    
    # === Server Settings ===
    port: int = Field(alias="PORT")
    env: str = Field(alias="ENV")
     
    
    class Config:
        # tell Pydantic to read a .env file from your project root
        env_file = "./creds/.env",
        extra = "forbid"
        # you can also specify env_file_encoding = "utf-8" if needed


# instantiate once, and import `settings` everywhere
settings = Settings()  # type: ignore

# PATHs
templates_path = resource_path("./Pages")
prompts_path   = resource_path("./bucket/prompts")
system_prompt  = resource_path("./bucket/prompts/system.yaml")
product_prompt = resource_path("./bucket/prompts/product.yaml")

# URLs
base_url: str = "https://digilog.pk/products/"
query_url: str = "https://digilog.pk/search?q="
no_image_url: str = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/450px-No_image_available.svg.png"

redis_url   = os.getenv("REDIS_URL", "redis://localhost:6379/0")
mongoDb_uri = os.getenv("MONGO_URL", "mongodb://root:secret@localhost:27017/?authSource=admin")

# Hyper-Parameters
llm_model: str = "gpt-5-mini-2025-08-07"
embedding_model: str = "text-embedding-3-small"
embedding_dimentions: int = 1536  # depending on the model used

vector_db_collection_name: str = "openai_embeddings"

# Index Paths
product_dict_file_location = "./bucket/index_storage/products.pkl"
id_to_product_mapping = "./bucket/index_storage/data.pkl"
vectorDb_index_path = "./bucket/index_storage/faiss"
persistent_path = "./bucket/index_storage/"

order_prefix = '#'