import redis.asyncio as redis
import uuid
import asyncio
import json
from datetime import timedelta
from models import ChatMessage, ChatCompletionMessageParam, ChatCompletionMessageToolCall
from typing import List, Optional, cast


class SessionManager:
    """An asynchronous session manager using Redis."""

    def __init__(self, redis_client: redis.Redis, session_ttl: int = 3600):
        self.redis_client = redis_client
        self.session_ttl = session_ttl  # Time to live in seconds (default 1 hour)
        self.session_prefix = "session:"

    @staticmethod
    def extract_chat_history(json_string: str) -> List[ChatMessage]:
        """Converts a JSON string back into a list of ChatMessage objects."""
        list_of_dicts = json.loads(json_string)
        return [ChatMessage(**d) for d in list_of_dicts]
    
    @staticmethod
    def serialize_chat_history(chat_history: List[ChatMessage]) -> str:
        """Converts a list of ChatMessage objects to a JSON string."""
        list_of_dicts = [msg.model_dump() for msg in chat_history]
        return json.dumps(list_of_dicts)

    async def create_session(self, user_data: dict) -> str:
        """Creates a new session and returns the session ID."""
        session_id = str(uuid.uuid4())
        session_key = f"{self.session_prefix}{session_id}"
        
        # Store session data as a JSON string
        await self.redis_client.set(session_key, json.dumps(user_data), ex=self.session_ttl)
        return session_id

    async def get_session(self, session_id: str) -> str:
        """Retrieves session data by session ID."""
        session_key = f"{self.session_prefix}{session_id}"
        session_data_json = await self.redis_client.get(session_key)

        if session_data_json:
            # Refresh the session expiration time (sliding expiration)
            await self.redis_client.expire(session_key, self.session_ttl)
            session_data = json.loads(session_data_json)  # dict
            json_str = json.dumps(session_data)  
            return json_str     
        return '{}'
    async def delete_session(self, session_id: str):
        """Deletes a session."""
        session_key = f"{self.session_prefix}{session_id}"
        await self.redis_client.delete(session_key)

    async def update_session(self, session_id: str, new_data: str):
        """Updates session data, overwriting existing keys."""
        session_key = f"{self.session_prefix}{session_id}"
        await self.redis_client.set(session_key, new_data, ex=self.session_ttl)

import asyncio

# --- Example Usage ---
async def wow():
    """An asynchronous function to demonstrate session management."""
    # 1. Connect to Redis and initialize the session manager
    # Use redis.asyncio to create an asynchronous client
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    # Initialize the session manager with a 1-hour session TTL
    session_manager = SessionManager(redis_client, session_ttl=3600)

    # 2. Simulate a user login and create a session
    user_info = {"user_id": 123, "username": "alice", "roles": ["user"]}
    session_id = "f5d22635-66ea-47a8-8e6b-bb16fb65a7cf"
    # await session_manager.create_session(user_info)
    print(f"New session created with ID: {session_id}")

    # 3. Simulate a subsequent request using the session ID
    retrieved_data = await session_manager.get_session(session_id)
    print(f"Retrieved session data: {retrieved_data}")
    return
    # 4. Simulate an update to the session
    new_user_info = {"user_id": 123, "username": "alice", "roles": ["user", "admin"]}
    await session_manager.update_session(session_id, str(new_user_info))
    print("Session updated.")
    
    updated_data = await session_manager.get_session(session_id)
    print(f"Updated session data: {updated_data}")
    
    # # 5. Simulate storing and retrieving a chat history
    # chat_history: List[ChatMessage] = [
    #     ChatMessage(role="user", content="Hello there!"),
    #     ChatMessage(role="assistant", content="Hi, how can I help you?"),
    # ]
    # # Serialize the list of objects and update the session with it
    # chat_json = SessionManager.serialize_chat_history(chat_history)
    # await session_manager.update_session(session_id, {"chat_history": chat_json})
    
    # # Retrieve the updated session
    # session_with_chat = await session_manager.get_session(session_id)
    # retrieved_chat_json = session_with_chat.get("history")
    
    # if retrieved_chat_json:
    #     retrieved_chat_history = SessionManager.extract_chat_history(retrieved_chat_json)
    #     print("\nRetrieved and deserialized chat history:")
    #     for msg in retrieved_chat_history:
    #         print(f"  - {msg.role}: {msg.content}")

    # 6. Simulate a user logout and delete the session
    await session_manager.delete_session(session_id)
    print("\nSession deleted.")

    # 7. Try to retrieve the deleted session (should return None)
    deleted_data = await session_manager.get_session(session_id)
    print(f"Attempt to retrieve deleted session: {deleted_data}")

# Run the asynchronous main function
if __name__ == "__main__":
    asyncio.run(wow())