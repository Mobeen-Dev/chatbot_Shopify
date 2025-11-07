from openai import OpenAI
from config import settings
# ✅ Init client
client = OpenAI(api_key=settings.openai_api_key)

def queued_tokens():
    batches = client.batches.list(limit=100)
    total = 0
    for b in batches.data:
        if b.status in ("validating", "in_progress", "finalizing"):
            total += b.usage.total_tokens
    return total

print("Queued tokens:", queued_tokens())
