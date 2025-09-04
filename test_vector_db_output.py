from models import ChatRequest
import json
from typing import List, Dict, Any, Union
from config import settings, embeddind_model
from logger import get_logger
from wrapper_chroma import ChromaRetriever
from Shopify import Shopify

import asyncio

vector_store = ChromaRetriever()


data = asyncio.run(vector_store.query_chroma(query="bluetooth micorcontroller", top_k=2+3))
data = json.dumps(data)
data = "#VectorDB-"+data
# print(data[10:])
if data[:10] == "#VectorDB-":
  objs = json.loads(data[10:])
  print ()
  print([obj["metadata"] for obj in objs])
else:
  print("False")
  print(data[:11])
  