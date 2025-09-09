import os
import openai
import faiss
import numpy as np
from config import settings
import asyncio
from openai import AsyncOpenAI
from config import settings, embeddind_model, vector_db_collection_name

import asyncio
# Set your OpenAI API key (ensure it's set in your environment)
openai.api_key = settings.openai_api_key

# Your list of documents
documents = [
    "How to learn Python for data science.",
    "A beginner's guide to machine learning.",
    "Best ways to cook Italian pasta.",
    "How to troubleshoot Windows 11 issues.",
    "The future of artificial intelligence.",
]
class ChromaRetriever:
    def __init__(
        self,
        persist_directory: str = "chroma_store",
        collection_name: str = vector_db_collection_name,
        model: str = embeddind_model,
    ):
        self.model = model
        # self.client = AsyncOpenAI(api_key=settings.openai_api_key,)  # async client
        # Chroma is sync, so we keep it as-is
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        
        self.collection = self.chroma_client.get_collection(name=collection_name)

# Function to get embedding using OpenAI API
    async def get_embedding(self,text, model="text-embedding-ada-002"):
        try:
          response = None
          async with AsyncOpenAI(api_key=settings.openai_api_key,) as client:
              # Perform your asynchronous OpenAI API calls here
              response = await client.embeddings.create(
                  model=self.model,
                  input=[query]
              )
        except Exception as e:
            raise RuntimeError(f"Embedding API failed: {e}")

        if not response or not response.data:
            raise ValueError("Failed to embed query.")

        query_embedding = response.data[0].embedding
        return query_embedding


# Generate embeddings for all documents
doc_embeddings = [get_embedding(doc) for doc in documents]

# Convert embeddings to numpy array of float32 (required by FAISS)
embedding_matrix = np.array(doc_embeddings).astype("float32")

# Create a FAISS index
dimension = embedding_matrix.shape[1]  # Number of dimensions in the embeddings
index = faiss.IndexFlatL2(dimension)   # L2 (Euclidean) distance
index.add(embedding_matrix)           # Add document embeddings to the index

# Query to search for
query = "Beginner tips for AI and machine learning"
query_vec = get_embedding(query)
query_vec = np.array([query_vec]).astype("float32")

# Search for top 3 most similar documents
k = 3
D, I = index.search(query_vec, k)

# Print the top results
print("Top results:")
for idx in I[0]:
    print(f"- {documents[idx]}")
