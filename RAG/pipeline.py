import openai
import os
from typing import List, Dict
from langchain.docstore.document import Document
from config import settings
from .local_data_prepairing import load_and_split_csv_files
# Set your OpenAI API key
openai.api_key = settings.openai_api_key


def embed_documents_openai(
    docs: List[Document],
    model: str = "text-embedding-3-small"
) -> List[Dict]:
    """
    Embeds a list of LangChain Documents using OpenAI and returns
    a list of dicts suitable for vector DB insertion.

    Returns:
        List of dicts with 'id', 'embedding', 'metadata'
    """
    payload = []
    
    for i, doc in enumerate(docs):
        try:
            content = doc.page_content.strip()
            if not content:
                continue
            
            # Call OpenAI embeddings API
            embedding_response = openai.embeddings.create(
                input=[content],
                model=model
            )
            embedding = embedding_response.data[0].embedding

            # Build vector record
            payload.append({
                "id": f"doc-{i}",
                "embedding": embedding,
                "metadata": doc.metadata,
                "text": content,
            })

        except Exception as e:
            print(f"Embedding failed for doc-{i}: {e}")
    
    return payload


if __name__ == "__main__":
    chunks = load_and_split_csv_files()
    print(f"Total chunks created: {len(chunks)}")

    embedded_chunks = embed_documents_openai(chunks[:20])
    print(f"Total embedded chunks: {len(embedded_chunks)}")

    # View an example embedded vector
    print(embedded_chunks[0]["metadata"])
    print(embedded_chunks[0]["embedding"][:5])  # Just first 5 values


# Standard Code

from Shopify import Shopify
from config import settings

async def create_store_index():
  store = Shopify(settings.store, "Pinecone-User")
  products = await store.fetch_all_products()
  await create_index(products)
  
async def create_index(products):
  pass