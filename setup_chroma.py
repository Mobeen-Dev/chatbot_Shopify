import openai
import chromadb
from chromadb.config import Settings
from config import settings
import os
# Set up OpenAI API key
openai.api_key = settings.openai_api_key  # Replace with your API key

persist_dir = "./chroma_data"
if not os.path.exists(persist_dir):
    os.makedirs(persist_dir)


# Initialize ChromaDB with persistence
client = chromadb.PersistentClient(path=persist_dir)
# Create a collection in ChromaDB
collection = client.get_or_create_collection("openai_embeddings")

# Define your data
documents = ["OpenAI is revolutionizing AI.", "ChromaDB makes embedding storage easy."]
metadata = [{"id": 1}, {"id": 2}]

# Generate embeddings using OpenAI
def get_embedding(text, model="text-embedding-ada-002"):
    response = openai.embeddings.create(input=text, model=model)
    return response.data[0].embedding

# Add documents and embeddings to ChromaDB
for doc, meta in zip(documents, metadata):
    embedding = get_embedding(doc)
    collection.add(
        documents=[doc],
        embeddings=[embedding],
        metadatas=[meta],
        ids=[str(meta["id"])]
    )

# Query ChromaDB
query_text = "AI revolution"
query_embedding = get_embedding(query_text)

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=2
)

print("Query Results:", results)