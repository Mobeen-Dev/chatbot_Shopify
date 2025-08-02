# shopify_bridge/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
import os

import sys


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class Settings(BaseSettings):
    # === OpenAi credentials ===
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    
    # === Shopify Master Store credentials ===
    shopify_api_key: str = Field(alias="SHOPIFY_API_KEY")
    shopify_api_secret: str = Field(alias="SHOPIFY_API_SECRET")
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
            "store_name": self.shopify_store_name,
            "api_version": self.shopify_api_version,
        }
    

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

base_url = "https://digilog.pk/products/"
NO_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/450px-No_image_available.svg.png"





