from pymongo import AsyncMongoClient
from config import mongoDb_uri, redis_url
import redis.asyncio as redis
from .logger import get_logger
import datetime
import asyncio
import json


class persistant_thread:
  def __init__(self, redis_url) -> None:
    self.redis = redis.from_url(redis_url, decode_responses=True)
    self.session_prefix = "session:"
    self.shadow_prefix  = "session:shadow:"
    self.logger = get_logger("Redis -> MongoDB")
  
  async def listen_for_expiry(self, db_index: int = 0):
    """Listen for key expiry events and recover data from the shadow key."""
    # Ensure notifications are enabled (E = Keyevent, x = expired)
    await self.redis.config_set("notify-keyspace-events", "Ex")

    channel = f"__keyevent@{db_index}__:expired"
    pubsub = self.redis.pubsub()
    await pubsub.subscribe(channel)
    self.logger.info(f"Listening for expired events on {channel} ...")

    async for message in pubsub.listen():
        if message.get("type") != "message":
            continue
        expired_key = message.get("data")
        if not isinstance(expired_key, str):
            continue

        if expired_key.startswith(self.session_prefix):
            session_id = expired_key.split(":", 1)[1]
            shadow_key = f"{self.shadow_prefix}{session_id}"

            # The volatile key is gone; recover from shadow
            shadow_data = await self.redis.get(shadow_key)

            if shadow_data:
                recovered = json.loads(shadow_data)
                # print("💾 Recovered expired session", recovered)
                await self.insert_chatRecord(recovered)
                # TODO: persist `recovered` to MongoDB here
                # Only delete shadow once persistence succeeds
                await self.redis.delete(shadow_key)
            else:
                print(f"⚠️ Shadow not found for {session_id} (possibly already deleted)")

  async def insert_chatRecord(self, data:dict):
    chat_history = {
      "ChatRecord": data.get("data",[]),
      "Metadata": data.get("metadata",{}),
      "date": datetime.datetime.now(tz=datetime.timezone.utc),
    }
    client =  AsyncMongoClient(mongoDb_uri)
    await client.aconnect()
    db = client["Chats"]        # DB
    posts = db.chats            # Collection
    job =  await posts.insert_one(chat_history)
    print(job)
    # print("job.acknowledged", job.acknowledged)
    return job.acknowledged

# data = {
#     "data": "Mike the 4 en",
#     "metadata": {
#         "title": "My First Blog Post",
#         "author": "Mike",
#         "tags": ["mongodb", "python", "pymongo"],
#         "created_at": "2025-09-03T12:00:00Z"
#     }
# }

# print(asyncio.run(insert_chatRecord(data)))

async def store_session_in_db():
    manager = persistant_thread(redis_url=redis_url)
    await manager.listen_for_expiry()
    # Create multiple demo sessions
    # for i in range(1, 5):
    #     await manager.create_session({
    #         "user": f"DENICE {i}",
    #         "chat": ["Hi!", "Hello!", "How are you?"],
    #         "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
    #     })

def run_session_store():
  asyncio.run(store_session_in_db())
  
  
if __name__ == "__main__":
  asyncio.run(store_session_in_db())
