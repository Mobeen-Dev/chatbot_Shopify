import os
import json
import faiss
import pickle
import random
import asyncio
import numpy as np
from openai import OpenAI
from Shopify import Shopify
from config import settings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


client = OpenAI(api_key=settings.openai_api_key)
store = Shopify(settings.store)

products = asyncio.run(store.fetch_all_products())
# print(products)


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
    
    p_info = f" Product : {product["title"]} at url /{product["handle"]} .With variants {variants} Belongs to {category} \n "
    
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

def process_products_to_batches(products, 
                                chunk_per_file=4000, 
                                index_path="faiss_index",
                                data_folder="embed_job_data"):
    """
    Processes a list of products by chunking their descriptions, saving metadata,
    and batching chunks into jsonl files.

    Args:
        products (list): List of product objects.
        chunk_per_file (int): Number of chunks per batch file.
        index_path (str): Path prefix for saving metadata pickle.
        data_folder (str): Folder to save batch jsonl files.
    """

    chunks = []
    for product in products:
        chunks.extend(chunk_product_description(product))
        
    print(f"Total products processed: {len(products)}")
    print(f"Total chunks created: {len(chunks)}")

    # Extract metadata and page contents separately
    meta_chunks = [c.metadata for c in chunks]
    chunks = [c.page_content for c in chunks]

    # Save metadata as pickle file
    with open(index_path + "_meta.pkl", "wb") as f:
        pickle.dump(meta_chunks, f)

    # Clear existing files in data_folder
    if os.path.exists(data_folder):
        for filename in os.listdir(data_folder):
            file_path = os.path.join(data_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    else:
        os.mkdir(data_folder)

    batch_num = chunk_per_file if len(chunks) > chunk_per_file else len(chunks)

    new_beginning = 0
    for batch_idx, num in enumerate(range(0, len(chunks)+1, batch_num)):
        batch_genres = chunks[new_beginning:new_beginning + batch_num]
        create_batch_jsonl(batch_idx, data_folder, batch_genres, updated_idx_start=num)
        print(f"{new_beginning = }\n{batch_num = }")
        new_beginning += batch_num

def upload_batch_files_and_get_ids(folder_path, client):
    """
    Uploads all files in the specified folder to the API and returns a list of file IDs.

    Args:
        folder_path (str): Path to the folder containing batch files to upload.
        client: The API client object with a .files.create() method.

    Returns:
        List[str]: List of uploaded file IDs.
    """

    uploaded_file_ids = []

    # List all files in the folder
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        # Make sure it is a file (skip directories)
        if os.path.isfile(file_path):
            print(f"Uploading file: {filename}")
            with open(file_path, "rb") as f:
                batch_input_file = client.files.create(
                    file=f,
                    purpose="batch"
                )
                uploaded_file_ids.append(batch_input_file.id)

    return uploaded_file_ids

def create_batches_from_file_ids(file_ids, client, endpoint="/v1/chat/completions", completion_window="24h", metadata=None):
    """
    Creates batch operations for each uploaded file ID.

    Args:
        file_ids (list): List of file IDs to create batches for.
        client: API client object with .batches.create() method.
        endpoint (str): API endpoint for the batch completion.
        completion_window (str): Duration for the batch completion window.
        metadata (dict): Optional metadata for the batch.

    Returns:
        list: List of batch operation responses.
    """
    if metadata is None:
        metadata = {"description": "batch job"}

    batch_responses = []

    for file_id in file_ids:
        print(f"Creating batch for file ID: {file_id}")
        batch_response = client.batches.create(
            input_file_id=file_id,
            endpoint=endpoint,
            completion_window=completion_window,
            metadata=metadata
        )
        batch_responses.append(batch_response)

    return batch_responses

# Example usage
if __name__ == "__main__":
    data_folder="embed_job_data"
    process_products_to_batches(products, chunk_per_file=4000, index_path="faiss_index", data_folder=data_folder)
    
    file_ids = upload_batch_files_and_get_ids(data_folder, client)
    
    batch_responses = create_batches_from_file_ids(file_ids, client)
    print("Batch operations created:", batch_responses)
    with open("batch_job_responses.json", 'w') as f:
        json.dump(batch_responses, f, indent=2)
    
    

