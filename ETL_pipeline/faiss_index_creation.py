import os
import sys
import json
import faiss
import numpy as np
from openai import OpenAI
from config import settings, vectorDb_index_path, embedding_dimentions
from utils.logger import get_logger

logger = get_logger("faiss-index-creation")
client = OpenAI(api_key=settings.openai_api_key)

# CONFIG
FOLDER_PATH = "embed_job_output"  # <- change this

def return_index(value: str) -> int:
    return int(value.split("-")[1])


all_embeddings = []
all_indexes = []

# Step 1: Process each .jsonl file
for filename in sorted(os.listdir(FOLDER_PATH)):
    if filename.endswith(".jsonl"):
        file_path = os.path.join(FOLDER_PATH, filename)
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line)
                    entries = data["response"]["body"]["data"]
                    for entry in entries:
                        embedding = entry["embedding"]
                        all_embeddings.append(embedding)

                        index = return_index(data["custom_id"])
                        all_indexes.append(index)

                except (KeyError, json.JSONDecodeError) as e:
                    print(f"Skipping line {line_num} in {filename}: {e}")

# Step 2: Convert to NumPy array
embedding_matrix = np.array(all_embeddings).astype("float32")

# Normalize embeddings for cosine similarity (if using IndexFlatIP)
faiss.normalize_L2(embedding_matrix)

# Your custom IDs (must be int64s)
all_indexes = np.array(all_indexes, dtype="int64")

print(all_indexes[:10])
print(all_indexes[-10:])
print(max(all_indexes))
print(len(all_indexes))
sys.exit()
# Step 3: Create FAISS index
base_index = faiss.IndexFlatIP(embedding_dimentions)
index = faiss.IndexIDMap(base_index)  # Wrap with IDMap
# index.add(embedding_matrix) # type: ignore
index.add_with_ids(embedding_matrix, all_indexes)  # type: ignore

logger.info(f"Created FAISS index with {index.ntotal} embeddings")
 
# Optional: Save FAISS index to disk
path = f"{vectorDb_index_path}.index"
faiss.write_index(index, path)
