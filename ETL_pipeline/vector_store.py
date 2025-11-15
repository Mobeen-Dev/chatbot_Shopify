import os
import json
import shutil
import tempfile
from typing import List
from openai import OpenAI
from config import settings

client = OpenAI(api_key=settings.openai_api_key)
data_folder = "embed_job_data"


def upload_chunks_in_batches(
    chunks: List[str],
    store_name: str,
    batch_size: int = 4000,
    folder_path: str = "vector_batches",
):
    """
    Uploads large numbers of chunks into an OpenAI vector store by splitting
    them across multiple JSONL files. Suitable for server use.

    Args:
        chunks: List of text chunks.
        store_name: Name of the vector store.
        batch_size: Number of chunks per JSONL file (tune per memory limits).
    """

    # Create vector store
    vector_store = client.vector_stores.create(name=store_name)
    vs_id = vector_store.id

    # Clean old folder if exists
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)

    # Create a new clean folder
    os.makedirs(folder_path, exist_ok=True)

    print(f"Created vector store: {vs_id}")

    total_chunks = len(chunks)
    batch_index = 0

    for i in range(0, total_chunks, batch_size):
        batch_index += 1
        batch = chunks[i : i + batch_size]

        # Create JSONL batch file
        batch_file = os.path.join(folder_path, f"batch_{batch_index}.json")

        # Write chunk batch as JSON (supported format)
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump(
                [{"text": c} for c in batch],
                f,
                ensure_ascii=False,
            )

        print(
            f"[Batch {batch_index}] → Created file {batch_file} ({len(batch)} chunks)"
        )

        # Upload the file
        with open(batch_file, "rb") as f:
            client.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vs_id, files=[f]
            )

        print(f"[Batch {batch_index}] → Uploaded")

    # After all uploads → delete entire folder
    shutil.rmtree(folder_path)
    print(f"All batches uploaded. Removed folder: {folder_path}")
    return vs_id


chunks = []

for file in sorted(os.listdir(data_folder)):
    if file.endswith(".jsonl"):
        path = os.path.join(data_folder, file)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    text = obj.get("body", {}).get("input", "")
                    if text:
                        chunks.append(text)
                except json.JSONDecodeError:
                    continue


vs_id = upload_chunks_in_batches(
    chunks,
    store_name="product-vector-store",
    batch_size=3650,  # adjust depending on server memory
)

print("Vector store ready:", vs_id)
