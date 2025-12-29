from pymongo import AsyncMongoClient
from config import mongoDb_uri, redis_url
import redis.asyncio as redis
from .logger import get_logger
import datetime
import asyncio
import json
from typing import Optional


class SessionPersistenceWorker:
    """
    Background worker that listens for Redis key expiry events
    and persists session data to MongoDB.
    """

    def __init__(self, redis_url: str, mongo_uri: str) -> None:
        self.redis_url = redis_url
        self.mongo_uri = mongo_uri

        # Will be initialized in start()
        self.redis: Optional[redis.Redis] = None
        self.mongo_client: Optional[AsyncMongoClient] = None
        self.collection = None

        self.session_prefix = "session:"
        self.shadow_prefix = "session:shadow:"
        self.logger = get_logger("Redis->MongoDB")

        self._running = False
        self._reconnect_delay = 5  # seconds
        self._max_reconnect_delay = 60

    async def start(self):
        """Initialize connections"""
        try:
            # Create Redis connection
            self.redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )

            # Create MongoDB connection with connection pool
            self.mongo_client = AsyncMongoClient(
                self.mongo_uri,
                maxPoolSize=10,
                minPoolSize=1,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
            )

            # Test MongoDB connection
            await self.mongo_client.admin.command("ping")

            # Get database and collection
            db = self.mongo_client["Chats"]
            self.collection = db["chats"]

            self.logger.info("✅ Connections established (Redis + MongoDB)")

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize connections: {e}")
            raise

    async def stop(self):
        """Cleanup connections"""
        self._running = False

        if self.redis:
            await self.redis.aclose()
            self.logger.info("Closed Redis connection")

        if self.mongo_client:
            await self.mongo_client.close()
            self.logger.info("Closed MongoDB connection")

    async def listen_for_expiry(self, db_index: int = 0):
        """
        Main loop: Listen for Redis key expiry events and persist to MongoDB.
        Handles reconnections automatically.
        """
        self._running = True
        reconnect_delay = self._reconnect_delay

        while self._running:
            if self.redis:
                try:
                    # Ensure notifications are enabled
                    await self.redis.config_set("notify-keyspace-events", "Ex")

                    channel = f"__keyevent@{db_index}__:expired"
                    pubsub = self.redis.pubsub()

                    try:
                        await pubsub.subscribe(channel)
                        self.logger.info(f"🎧 Listening on {channel}")

                        # Reset reconnect delay on successful connection
                        reconnect_delay = self._reconnect_delay

                        async for message in pubsub.listen():
                            if not self._running:
                                break

                            await self._process_message(message)

                    finally:
                        await pubsub.unsubscribe(channel)
                        await pubsub.close()

                except redis.ConnectionError as e:
                    if self._running:
                        self.logger.error(f"⚠️ Redis connection lost: {e}")
                        self.logger.info(f"Reconnecting in {reconnect_delay}s...")
                        await asyncio.sleep(reconnect_delay)

                        # Exponential backoff
                        reconnect_delay = min(
                            reconnect_delay * 2, self._max_reconnect_delay
                        )
                    else:
                        break

                except Exception as e:
                    if self._running:
                        self.logger.error(
                            f"❌ Unexpected error in listener: {e}", exc_info=True
                        )
                        await asyncio.sleep(reconnect_delay)
                    else:
                        break

        self.logger.info("👋 Stopped listening for expiry events")

    async def _process_message(self, message: dict):
        """Process a single Redis pubsub message"""
        if message.get("type") != "message":
            return

        expired_key = message.get("data")
        if not isinstance(expired_key, str):
            return

        # Only process session keys
        if not expired_key.startswith(self.session_prefix):
            return

        session_id = expired_key.removeprefix(self.session_prefix)
        shadow_key = f"{self.shadow_prefix}{session_id}"
        if self.redis:
            try:
                # Retrieve shadow data
                shadow_data = await self.redis.get(shadow_key)
                print("\n\nREDIS DATA RETRIEVAL\nn")
                print(shadow_data)
                print("\n\nREDIS DATA RETRIEVAL\n\n")

                if not shadow_data:
                    self.logger.warning(f"⚠️ No shadow found for session: {session_id}")
                    return

                # Parse and persist
                recovered = json.loads(shadow_data)
                self.logger.info(f"💾 Recovering session: {session_id}")

                success = await self._insert_chat_record(recovered, session_id)

                if success:
                    # Only delete shadow after successful persistence
                    await self.redis.delete(shadow_key)
                    self.logger.info(f"✅ Persisted & cleaned session: {session_id}")
                else:
                    self.logger.error(f"❌ Failed to persist session: {session_id}")

            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in shadow key {shadow_key}: {e}")
                # Optionally delete corrupted shadow data
                await self.redis.delete(shadow_key)

            except Exception as e:
                self.logger.error(
                    f"Error processing session {session_id}: {e}", exc_info=True
                )

    async def _insert_chat_record(self, data: dict, id: str) -> bool:
        """Insert chat record into MongoDB"""
        try:
            # Handle case where data might still be a string
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    self.logger.error(
                        f"Data is string but not valid JSON: {data[:100]}"
                    )
                    return False

            # Ensure data is a dictionary
            if not isinstance(data, dict):
                self.logger.error(f"Data is not a dict after parsing: {type(data)}")
                return False

            raw_chat = data.get("data", [])
            filtered_chat = [
                msg
                for msg in raw_chat
                if msg.get("role") in ["user", "assistant"]
                and msg.get("content", "").strip()
            ]

            # FINAL VALIDATION
            if id == "":
                return True  # Bypass Empty Entries
            if not filtered_chat:
                return True  # Bypass Empty Entries

            chat_history = {
                "ChatId": id,
                "ChatRecord": filtered_chat,
                "Metadata": data.get("metadata", {}),
                "date": datetime.datetime.now(tz=datetime.timezone.utc),
            }

            result = await self.collection.insert_one(chat_history)  # type: ignore
            return result.acknowledged

        except Exception as e:
            self.logger.error(f"MongoDB insert failed: {e}", exc_info=True)
            return False


# Global worker instance
_worker: Optional[SessionPersistenceWorker] = None
_worker_task: Optional[asyncio.Task] = None


async def start_session_worker():
    """Start the background worker - call this in FastAPI lifespan startup"""
    global _worker, _worker_task

    if _worker is not None:
        raise RuntimeError("Worker already running")

    _worker = SessionPersistenceWorker(redis_url=redis_url, mongo_uri=mongoDb_uri)

    try:
        await _worker.start()
        _worker_task = asyncio.create_task(_worker.listen_for_expiry())

    except Exception as e:
        _worker.logger.error(f"Failed to start worker: {e}")
        await _worker.stop()
        _worker = None
        raise


async def stop_session_worker():
    """Stop the background worker - call this in FastAPI lifespan shutdown"""
    global _worker, _worker_task

    if _worker is None:
        return

    _worker.logger.info("Shutting down worker...")

    # Signal worker to stop
    await _worker.stop()

    # Cancel the task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass

    _worker = None
    _worker_task = None


async def store_session_in_db():
    worker = SessionPersistenceWorker(redis_url=redis_url, mongo_uri=mongoDb_uri)

    try:
        await worker.start()
        await worker.listen_for_expiry()
    finally:
        await worker.stop()


# For standalone testing
if __name__ == "__main__":
    asyncio.run(store_session_in_db())
