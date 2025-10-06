import os
import sys
import json
import numpy as np
import faiss
import pickle
from openai import OpenAI
from config import settings
from typing import Generator, List
from langchain.docstore.document import Document
from langchain_community.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
from config import settings, embeddind_model, vector_db_collection_name
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import asyncio
from openai import AsyncOpenAI
import asyncio

# Configure your OpenAI key
openai.api_key = settings.openai_api_key


class vectorDB:
    def __init__(
        self,
        index_path: str = "openai_embeddings",
        model: str = embeddind_model,
    ):
        self.model = model
        # self.client = AsyncOpenAI(api_key=settings.openai_api_key,)  # async client
        self.db_client = faiss.read_index(index_path + ".index")
        with open(index_path + "_meta.pkl", "rb") as f:
            self.metadata = pickle.load(f)
        with open("data.pkl", "rb") as f:
            self.data_dict = pickle.load(f)

    # async def aclose(self):
    #     await self.client.close()

    async def query(
        self,
        query: str,
        top_k: int = 5,
    ):
        # 1. Async call to OpenAI for embedding
        try:
            response = None
            async with AsyncOpenAI(
                api_key=settings.openai_api_key,
            ) as client:
                # Perform your asynchronous OpenAI API calls here
                response = await client.embeddings.create(
                    model=self.model, input=[query]
                )
        except Exception as e:
            raise RuntimeError(f"Embedding API failed: {e}")

        if not response or not response.data:
            raise ValueError("Failed to embed query.")

        query_embedding = response.data[0].embedding
        query_embedding = np.array([query_embedding]).astype("float32")
        faiss.normalize_L2(query_embedding)

        # 2. Run Faiss (sync) in a thread so it doesn’t block event loop
        scores, indices = await asyncio.to_thread(
            self.db_client.search,
            query_embedding,  # xq
            top_k,  # k
        )

        if scores is None or indices is None or len(scores) == 0 or len(indices) == 0:
            return []

        seen_ids = set()
        result = []

        for score, idx in zip(scores[0], indices[0]):
            unique_id = self.metadata[idx]["id"]
            if unique_id not in seen_ids:
                seen_ids.add(unique_id)
                result.append(
                    {
                        "score": float(score),
                        "content": self.data_dict[unique_id],
                        "metadata": {
                            "Handle": self.data_dict[unique_id]["handle"],
                            "Score": round(float(score), 3),
                            "Query": query,
                        },
                    }
                )

        return result


if __name__ == "__main__":
    store = vectorDB()
    user_query = "Do you have MICRO CONTROLLER like arduino?"
    matches = asyncio.run(store.query(query=user_query, top_k=5))
    print(matches)
    # for i, match in enumerate(matches):
    #     print("{")
    #     print(f"\nMatch {i + 1}:")
    #     print(f"Score: {match['score']:.4f}")
    #     # print(f"Metadata: {match['metadata']}")
    #     print(f"Content:\n{match['content']}")
    #     print("}")
