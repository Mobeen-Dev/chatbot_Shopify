from Shopify import Shopify
from config import settings
import asyncio
import random
import os
import json
import pickle
import faiss
import numpy as np
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)
store = Shopify(settings.store)

products = asyncio.run(store.fetch_all_products())
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

def create_request_object(request_number, text_chunk):
    """
    Creates a request object for the OpenAI embeddings API.

    Args:
        request_number (int): The sequential request number.
        job_title (str): The job title to be embedded.

    Returns:
        Dict[str, Any]: A dictionary representing the API request object.
    """

    request_object = {
        "custom_id": f"request-{request_number}",
        "method": "POST",
        "url": "/v1/embeddings",
        "body": {
            "model": "text-embedding-3-small",
            "input": text_chunk,
            "encoding_format": "float",
            
            }
        }
    return request_object

def create_batch_jsonl(batch_num, data_folder, genres, updated_idx_start):
    """
    Creates a JSONL file containing a batch of job title requests.

    Args:
        batch_num (int): The batch number.
        job_titles_folder (str): The folder to save the JSONL file.
        job_titles (List): A list of job titles to include in the batch.
        updated_idx_start (int): The starting index for job titles.
    """

    with open(f"{data_folder}/file_batch_{batch_num}.jsonl", "w") as f:
        for idx, genre in enumerate(genres):
            
            request_number = idx+1 + updated_idx_start
            
            genre_request_object = create_request_object(request_number, genre)
            f.write(json.dumps(genre_request_object) + "\n")

# Example usage
if __name__ == "__main__":
    # print(search_faiss("whats ai"))
    chunks = []
    
    
    for product in products:
        
        
        chunks.extend( chunk_product_description(product) ) 
        
        # print(f"Total chunks created: {len(chunks)}\n")
        # save_chunks_to_faiss(chunks)
        # for c in chunks:
        #     print(c.page_content, "\n")
        #     print(c.metadata)
        #     print()

    print(len(products))
    
    chunks = [c.page_content for c in chunks]
    
    data_folder = "embed_job_data"
    if not os.path.exists(data_folder):
        os.mkdir(data_folder)
    
    batch_num = 10000 if len(chunks) > 10000 else int(len(chunks))

    new_beginning = 0
    for batch_idx, num in enumerate(range(0, len(chunks)+1, batch_num )):
        
        batch_genres = chunks[new_beginning: new_beginning + batch_num]
        
        create_batch_jsonl(batch_idx, data_folder, batch_genres, updated_idx_start = num)
        print(f"{new_beginning = }\n {batch_num = }")
        new_beginning += batch_num
        
        
        
    
    
    
    
    

