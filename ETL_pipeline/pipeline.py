import os
import sys
import time
import json
import faiss
import pickle
import openai
import random
import asyncio
import requests
import argparse
import numpy as np
from typing import List
from openai import OpenAI
from Shopify import Shopify
from langchain.schema import Document
from config import settings, db_index_path
from utils.logger import get_logger
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = get_logger("etl-pipeline")

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
    base_doc = Document(page_content=description, metadata={"id": product_id})

    # Split into chunks
    chunks = description_splitter.split_documents([base_doc])

    # Building Product Intro
    variants = ""
    for option in product["options"]:
        variants += f"{option['name']} : {option['values']}"

    category = product["category"]
    if category:
        category = category["fullName"]

    p_info = f" Product : {product['title']} at url /{product['handle']} .With variants {variants} Belongs to {category} \n "

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


def save_chunks_to_faiss(chunks, index_path="faiss_index"):
    texts = [chunk.page_content for chunk in chunks]
    metadata = [chunk.metadata for chunk in chunks]

    # 1. Get embeddings from OpenAI
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)

    embeddings = np.array([e.embedding for e in response.data]).astype("float32")

    # 2. Normalize for cosine similarity
    faiss.normalize_L2(embeddings)

    # 3. Create FAISS index (Inner Product = cosine similarity after normalization)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)  # type: ignore

    # 4. Save FAISS index
    faiss.write_index(index, index_path + ".index")

    # 5. Save metadata separately (aligned by position)
    with open(index_path + "_meta.pkl", "wb") as f:
        pickle.dump(metadata, f)

    logger.info(
        f" Saved {len(chunks)} chunks into FAISS (cosine similarity) at '{index_path}.index'"
    )


def search_faiss(query, index_path="faiss_index", top_k=5):
    # 1. Load FAISS index
    index = faiss.read_index(index_path + ".index")

    # 2. Load metadata
    with open(index_path + "_meta.pkl", "rb") as f:
        metadata = pickle.load(f)

    # 3. Embed and normalize query
    q_emb = (
        client.embeddings.create(model="text-embedding-3-small", input=query)
        .data[0]
        .embedding
    )
    q_emb = np.array([q_emb]).astype("float32")
    faiss.normalize_L2(q_emb)

    # 4. Search
    scores, indices = index.search(q_emb, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        results.append(
            {
                "score": float(score),  # cosine similarity score
                "metadata": metadata[idx],  # remap via saved metadata
            }
        )

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
        },
    }
    return request_object


def create_batch_jsonl(batch_num, data_folder, genres, updated_idx_start):
    """
    Creates a JSONL file containing a batch of genre requests.

    Args:
        batch_num (int): The batch number.
        data_folder (str): The folder to save the JSONL file.
        genres (List): A list of genres to include in the batch.
        updated_idx_start (int): The starting index for request numbering.
    """
    if not genres:
        return

    # Ensure the folder exists
    os.makedirs(data_folder, exist_ok=True)

    file_path = os.path.join(data_folder, f"file_batch_{batch_num}.jsonl")
    with open(file_path, "w", encoding="utf-8") as f:
        for idx, genre in enumerate(genres):
            request_number = updated_idx_start + idx + 1
            genre_request_object = create_request_object(request_number, genre)
            f.write(json.dumps(genre_request_object) + "\n")


def process_and_save_products_into_batches(
    products,
    chunk_per_file=4000,
    index_path="faiss_index",
    data_folder="embed_job_data",
):
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

    logger.info(f"Total products processed: {len(products)}")
    logger.info(f"Total chunks created: {len(chunks)}")

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

    batch_num = min(len(chunks), chunk_per_file)

    for batch_idx, start_idx in enumerate(range(0, len(chunks), batch_num)):
        batch_genres = chunks[start_idx : start_idx + batch_num]
        create_batch_jsonl(
            batch_idx, data_folder, batch_genres, updated_idx_start=start_idx
        )
        logger.extended_logging(f"{start_idx = }\n{batch_num = }")


def upload_batch_files_and_get_ids(
    folder_path, client, max_retries=5, initial_backoff=1
):
    """
    Uploads all files in the specified folder to the API and returns a list of file IDs,
    handling rate limits and network errors with retries.

    Args:
        folder_path (str): Path to the folder containing batch files to upload.
        client: The API client object with a .files.create() method.
        max_retries (int): Maximum number of retries per file.
        initial_backoff (int): Initial backoff delay in seconds.

    Returns:
        List[str]: List of successfully uploaded file IDs.
    """

    uploaded_file_ids = []

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        # Skip empty files
        if os.path.getsize(file_path) == 0:
            logger.extended_logging(f"Skipping empty file: {filename}")
            continue

        # Skip non-files (directories, etc.)
        if not os.path.isfile(file_path):
            continue

        logger.extended_logging(f"Uploading file: {filename}")

        retries = 0
        backoff = initial_backoff

        while retries < max_retries:
            try:
                with open(file_path, "rb") as f:
                    batch_input_file = client.files.create(file=f, purpose="batch")
                    uploaded_file_ids.append(batch_input_file.id)
                    logger.extended_logging(f"Uploaded {filename} -> ID: {batch_input_file.id}")
                    break  # Success, exit retry loop

            except openai.RateLimitError:
                logger.error(
                    f"Rate limit exceeded while uploading {filename}. Retrying in {backoff} seconds..."
                )
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                openai.APIConnectionError,
            ) as e:
                logger.error(
                    f"Network error while uploading {filename}: {e}. Retrying in {backoff} seconds..."
                )
            except Exception as e:
                logger.error(f"Unexpected error while uploading {filename}: {e}")
                break  # Skip file on unhandled error unless you want to retry everything

            # Wait and retry
            time.sleep(backoff)
            retries += 1
            backoff *= 4  # Exponential backoff

        else:
            logger.error(f"Failed to upload {filename} after {max_retries} retries.")

    return uploaded_file_ids


def create_batches_from_file_ids(
    file_ids,
    client,
    endpoint="/v1/embeddings",
    completion_window="24h",
    metadata=None,
    max_retries=2,
    initial_backoff=5,
):
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
        logger.extended_logging(f"Creating batch for file ID: {file_id}")

        retries = 0
        backoff = initial_backoff

        while retries < max_retries:
            try:
                batch_response = client.batches.create(
                    input_file_id=file_id,
                    endpoint=endpoint,
                    completion_window=completion_window,
                    metadata=metadata,
                )
                batch_responses.append(batch_response)
                break  # Success, break out of retry loop

            except openai.RateLimitError:
                logger.info(f"Rate limit exceeded. Retrying in {backoff} seconds...")
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                openai.APIConnectionError,
            ) as e:
                logger.error(f"Network error: {e}. Retrying in {backoff} seconds...")
            except Exception as e:
                logger.error(f"Unhandled error for file ID {file_id}: {e}")
                break  # Optional: break if you don’t want to retry on unexpected errors

            # Wait and retry
            time.sleep(backoff)
            retries += 1
            backoff *= 2  # Exponential backoff

        else:
            logger.error(
                f"Failed to create batch for file ID {file_id} after {max_retries} retries."
            )

    return batch_responses


def batch_to_json(batch_obj):
    """
    Converts a single OpenAI Batch object to a JSON-serializable dictionary.
    Uses model_dump() if available, otherwise falls back to __dict__.

    Args:
        batch_obj: An instance of openai.types.Batch

    Returns:
        dict: A JSON-serializable dictionary representation of the batch
    """
    if hasattr(batch_obj, "model_dump"):
        return batch_obj.model_dump()
    else:
        # Shallow conversion fallback
        return {k: v for k, v in batch_obj.__dict__.items() if not k.startswith("_")}


def save_batches_as_json(batch_list, output_path="batch_responses.json"):
    """
    Converts a list of OpenAI Batch objects to JSON and saves to a file.

    Args:
        batch_list (list): List of openai.types.Batch objects
        output_path (str): Output filename
    """
    os.makedirs(os.path.dirname(db_index_path), exist_ok=True)
    batch_dicts = [batch_to_json(b) for b in batch_list]
    output_path = db_index_path + output_path # Save in persistant Directory
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(batch_dicts, f, indent=2)

    logger.info(f"Saved {len(batch_dicts)} batches to {output_path}")


def return_output_file_ids(batch_file: str = "batch_responses.json") -> List:
    output_file_ids = []
    batch_file_path = db_index_path + batch_file
    with open(batch_file_path, "r") as f:
        data = json.load(f)
        if not data:
            return []
        for obj in data:
            try:
                batch = client.batches.retrieve(obj["id"])
                # logger.info(batch)
                output_file_ids.append(batch.output_file_id)

            except KeyError as e:
                pass

    return output_file_ids


def clean_folder(folder_path):
    if not os.path.exists(folder_path):
        return  # Nothing to clean

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)

        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.remove(item_path)  # Remove file or symbolic link


def save_embeddings_file(output_file_ids: List, folder_path):
    clean_folder(folder_path)
    os.makedirs(folder_path, exist_ok=True)

    for index, output_file_id in enumerate(output_file_ids):
        # output_file = client.files.retrieve(str(output_file_id))
        # logger.info(output_file)
        content = None
        try:
            content = client.files.content(str(output_file_id))
        except Exception as e:
            continue
        binary_data = content.read()

        # Now save it to a local file
        with open(f"{folder_path}/output_{index}.jsonl", "wb") as f:
            f.write(binary_data)


def pipeline(products, client):
    parser = argparse.ArgumentParser(description="Vector Database Pipeline")

    parser.add_argument(
        "--chunk_products",
        action="store_true",
        help="Chunk product list into JSONL files",
    )
    parser.add_argument(
        "--upload_chunks",
        action="store_true",
        help="Upload JSONL chunks to OpenAI server",
    )
    parser.add_argument(
        "--start_embedding_job",
        action="store_true",
        help="Start batch embedding job on uploaded files",
    )
    parser.add_argument(
        "--download_embeddings",
        action="store_true",
        help="Download embedding results from server",
    )

    args = parser.parse_args()

    prepare_data = args.chunk_products
    new_job = args.upload_chunks and args.start_embedding_job
    finish_open_job = args.download_embeddings

    output_folder = "embed_job_output"
    data_folder = "embed_job_data"

    if prepare_data:
        process_and_save_products_into_batches(
            products,
            chunk_per_file=1500,
            index_path="faiss_index",
            data_folder=data_folder,
        )

    if new_job:
        file_ids = upload_batch_files_and_get_ids(data_folder, client)
        batch_responses = create_batches_from_file_ids(file_ids, client)
        logger.extended_logging(f"Batch operations created: {batch_responses}")
        save_batches_as_json(batch_responses)

    if finish_open_job:
        output_file_ids = return_output_file_ids()
        save_embeddings_file(output_file_ids, output_folder)


# Example usage
if __name__ == "__main__":
    store = Shopify(settings.store)
    products = asyncio.run(store.fetch_all_products())

    client = OpenAI(api_key=settings.openai_api_key)

    pipeline(products, client)
