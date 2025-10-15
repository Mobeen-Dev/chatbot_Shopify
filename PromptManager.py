import yaml
import aiofiles
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional


# ---------------------------------------------------------
# Async YAML Reader
# ---------------------------------------------------------
async def read_yaml_async(file_path: str) -> Dict[str, Any]:
    """Efficiently read and parse a YAML file in an async app."""
    async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
        content = await f.read()
    # YAML parsing is CPU-bound → move to a background thread
    return await asyncio.to_thread(yaml.safe_load, content)


# ---------------------------------------------------------
# PromptManager Class
# ---------------------------------------------------------
class PromptManager:
    """Manages multiple YAML prompt files asynchronously and safely."""

    _instance = None
    _lock = asyncio.Lock()  # async-safe lock for concurrent refresh

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    async def init(
        self,
        system_prompts_path: str = "system.yaml",
        product_prompts_path: str = "product.yaml",
    ):
        """Initialize the manager asynchronously (only once)."""
        if self._initialized:
            return self

        self.system_prompts_path = Path(system_prompts_path)
        self.user_prompts_path = Path(product_prompts_path)
        self.system_prompts: Dict[str, Any] = {}
        self.user_prompts: Dict[str, Any] = {}

        await self.reload()
        self._initialized = True
        return self

    async def reload(self):
        """Reload both YAML files concurrently (async + thread-safe)."""
        async with self._lock:
            try:
                results = await asyncio.gather(
                    read_yaml_async(str(self.system_prompts_path)),
                    read_yaml_async(str(self.user_prompts_path)),
                )
                self.system_prompts, self.user_prompts = results
                print(
                    f"✅ Reloaded {len(self.system_prompts)} system prompts and {len(self.user_prompts)} user prompts"
                )
            except Exception as e:
                print(f"❌ Failed to reload prompts: {e}")

    # -----------------------------------------------------
    # Accessor methods
    # -----------------------------------------------------
    def get_system_prompt(self, key: str, default: str = ""):
        return self.system_prompts.get(key, default)

    def get_recommend_product_prompt(self, key: str,  default: str = ""):
        return self.user_prompts.get(key, default)
