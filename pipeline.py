from Shopify import Shopify
from config import settings
import asyncio
import random

import pickle
import faiss
import numpy as np
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)
store = Shopify(settings.store)

products = asyncio.run(store.fetch_all_products(True))
# print(products)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

def chunk_product_description(product, chunk_size: int = 500, chunk_overlap: int = 70):
    """
    Splits a product's description into chunks with metadata including product.id.
    
    Args:
        product: An object or dict with 'id' and 'description' attributes/keys.
        chunk_size: Max size of each chunk.
        chunk_overlap: Overlap between chunks.
        
    Returns:
        List of Document objects containing chunked description and metadata.
    """
    
    # Ensure we can handle both dict and object input
    product_id = getattr(product, "id", None) or product.get("id")
    description = getattr(product, "description", None) or product.get("description")
    
    if not description:
        return []

    # Initialize text splitter
    description_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n", ".", " ", ""],
    )

    # Create initial document
    base_doc = Document(
        page_content=description,
        metadata={"id": product_id}
    )

    # Split into chunks
    chunks = description_splitter.split_documents([base_doc])
    
    # Building Product Intro
    variants = ''
    for option in product["options"]:
      variants += f"{option["name"]} : {option["values"]}"
    
    category = product["category"]
    if category:
      category = category["fullName"]
    
    p_info = f" Product : {product["title"]} at url /{product["handle"]} .With variants {variants} Belongs to {category}"
    
    # Make sure metadata carries the product id
    added = False
    for chunk in chunks:
        chunk.metadata["id"] = product_id
        if random.random() < 0.05:  # ~5% chance per chunk
            added = True
            chunk.page_content = p_info + chunk.page_content

    # Guarantee: at least one chunk gets p_info
    if not added and chunks:
        chosen = random.choice(chunks)
        chosen.page_content = p_info + chosen.page_content


    return chunks

def normalize(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

def save_chunks_to_faiss(chunks, index_path="faiss_index"):
    texts = [chunk.page_content for chunk in chunks]
    metadata = [chunk.metadata for chunk in chunks]

    # 1. Get embeddings from OpenAI
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )

    embeddings = np.array([e.embedding for e in response.data]).astype("float32")

    # 2. Normalize for cosine similarity
    embeddings = normalize(embeddings)

    # 3. Create FAISS index (Inner Product = cosine similarity after normalization)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings) # type: ignore

    # 4. Save FAISS index
    faiss.write_index(index, index_path + ".index")

    # 5. Save metadata separately (aligned by position)
    with open(index_path + "_meta.pkl", "wb") as f:
        pickle.dump(metadata, f)

    print(f"✅ Saved {len(chunks)} chunks into FAISS (cosine similarity) at '{index_path}.index'")

def search_faiss(query, index_path="faiss_index", top_k=5):
    # 1. Load FAISS index
    index = faiss.read_index(index_path + ".index")

    # 2. Load metadata
    with open(index_path + "_meta.pkl", "rb") as f:
        metadata = pickle.load(f)

    # 3. Embed and normalize query
    q_emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding
    q_emb = np.array([q_emb]).astype("float32")
    q_emb = normalize(q_emb)

    # 4. Search
    scores, indices = index.search(q_emb, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        results.append({
            "score": float(score),       # cosine similarity score
            "metadata": metadata[idx],   # remap via saved metadata
        })

    return results
    
# Example usage
if __name__ == "__main__":
  print(search_faiss("whats ai"))
  
  
  
  for product in products:
    break
    
    chunks = chunk_product_description(product)
    
    print(f"Total chunks created: {len(chunks)}\n")
    save_chunks_to_faiss(chunks)
    for c in chunks:
        print(c.page_content, "\n")
        print(c.metadata)
        print()

  print(len(products))
