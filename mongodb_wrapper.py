from pymongo import AsyncMongoClient
import asyncio
import datetime
from config import mongoDb_uri
from bson import ObjectId

async def insert_chatRecord(data, post_id):
  post = {
    "ChatRecord": data.get("data",[]),
    "Metadata": data.get("metadata",{}),
    "date": datetime.datetime.now(tz=datetime.timezone.utc),
  }
  client =  AsyncMongoClient(mongoDb_uri)
  await client.aconnect()
  db = client["Chats"]        # DB
  posts = db.chats            # Collection
  # return (await posts.insert_one(post)).acknowledged
  # post_id = (await posts.insert_one(post))
  # post_id
  
  # print(post_id)
  return await posts.find_one({"_id": ObjectId(post_id)})
  # return await posts.find_one({"author": "Mike the Mobeen"})
  # return post_id



# print(client)
while(1):
  post = {
    "ChatRecord": "Mike the 4 en",
    "Metadata": "My first blog post!",
    "date": datetime.datetime.now(tz=datetime.timezone.utc),
  }
  print(asyncio.run(insert_chatRecord(post, "68b84f59d07d3f16d7b93d4a")))
  

