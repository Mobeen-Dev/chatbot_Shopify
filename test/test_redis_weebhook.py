import asyncio
import json
import datetime
import uuid
import redis.asyncio as redis

class SessionManager:
    def __init__(self, redis_url="redis://localhost:6379/0", ttl_seconds: int = 10):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.session_prefix = "session:"
        self.shadow_prefix = "session:shadow:"
        self.session_ttl = ttl_seconds  # short TTL for demo

    async def create_session(self, user_data: dict) -> str:
        """Create a session with TTL and write a shadow copy without TTL."""
        session_id = str(uuid.uuid4())
        key = f"{self.session_prefix}{session_id}"
        shadow_key = f"{self.shadow_prefix}{session_id}"

        payload = json.dumps(user_data)
        # Volatile key (expires)
        await self.redis.set(key, payload, ex=self.session_ttl)
        # Shadow key (no TTL)
        await self.redis.set(shadow_key, payload)

        print(f"✅ Created session {session_id} (TTL={self.session_ttl}s)")
        return session_id

    async def update_session(self, session_id: str, user_data: dict):
        """Update both the volatile and shadow copies (sliding expiry)."""
        key = f"{self.session_prefix}{session_id}"
        shadow_key = f"{self.shadow_prefix}{session_id}"
        payload = json.dumps(user_data)

        # Refresh volatile value + TTL
        await self.redis.set(key, payload, ex=self.session_ttl)
        # Update shadow copy
        await self.redis.set(shadow_key, payload)

        print(f"🔄 Updated session {session_id} (TTL reset to {self.session_ttl}s)")

    async def listen_for_expiry(self, db_index: int = 0):
        """Listen for key expiry events and recover data from the shadow key."""
        # Ensure notifications are enabled (E = Keyevent, x = expired)
        await self.redis.config_set("notify-keyspace-events", "Ex")

        channel = f"__keyevent@{db_index}__:expired"
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        print(f"👂 Listening for expired events on {channel} ...")

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
                recovered = (
                    json.loads(shadow_data) if shadow_data else {"info": "No shadow found"}
                )
                print(
                    "💾 Recovered expired session\n"
                    f"  session_id: {session_id}\n"
                    f"  expired_at: {datetime.datetime.now(datetime.UTC).isoformat()}\n"
                    f"  data: {recovered}\n"
                )

                # TODO: persist `recovered` to MongoDB here, then clean shadow:
                # await mongo_collection.insert_one({...})
                await self.redis.delete(shadow_key)


    async def close(self):
        await self.redis.close()


async def demo():
    manager = SessionManager(ttl_seconds=5)  # very short for demo
    # Create multiple demo sessions
    for i in range(1, 15):
      await manager.create_session({
          "data": {
              "user": f"{i}{i}{i}",
              "chat": ["Hi!", "Hello!", "How are you?"],
              "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
          },
          "metadata": {
              "source": "chatbot",
              "session_type": "demo",
              "created_at": datetime.datetime.now(datetime.UTC).isoformat()
          }
      })
      await asyncio.sleep(2)

    # Run the expiry listener (will print recovered data)
    await manager.listen_for_expiry(db_index=0)

if __name__ == "__main__":
    asyncio.run(demo())
