import os
import sys
import json
import numpy as np
import faiss
import pickle
from openai import OpenAI
from config import settings


client = OpenAI(api_key=settings.openai_api_key)

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
        print({
                "score": float(score),  # cosine similarity score
                "metadata": metadata[idx],  # remap via saved metadata
                "position": idx
            })
        results.append(
            {
                "score": float(score),  # cosine similarity score
                "metadata": metadata[idx],  # remap via saved metadata
            }
        )

    return results

print(search_faiss("Rd-03E is a radar dectector module equipped with ICLEGEND\u2019s S3KM111L chip developed by Shenzhen Ai-Thinker Technology Co., Ltd. It operates in the 24GHz K-band, with a modulation bandwidth of up to 1GHz per single frequency scan. This module uses the FMCW waveform and the advanced signal processing technology proprietary to the S3 series chip to achieve accurate human sensing range measurement, distance information display and gesture recognition", "openai_embeddings", 50))
sys.exit()
# CONFIG
FOLDER_PATH = 'embed_job_output'  # <- change this
EMBEDDING_DIM = 1536  # depending on the model used

all_embeddings = []

# Step 1: Process each .jsonl file
for filename in os.listdir(FOLDER_PATH):
    if filename.endswith('.jsonl'):
        file_path = os.path.join(FOLDER_PATH, filename)
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line)
                    entries = data['response']['body']['data']
                    for entry in entries:
                        embedding = entry['embedding']
                        all_embeddings.append(embedding)
                except (KeyError, json.JSONDecodeError) as e:
                    print(f"Skipping line {line_num} in {filename}: {e}")

# Step 2: Convert to NumPy array
embedding_matrix = np.array(all_embeddings).astype('float32')

# Normalize embeddings for cosine similarity (if using IndexFlatIP)
faiss.normalize_L2(embedding_matrix)

# Step 3: Create FAISS index
index = faiss.IndexFlatIP(EMBEDDING_DIM)
index.add(embedding_matrix) # type: ignore

print(f"✅ Loaded {index.ntotal} embeddings into FAISS index.")

# Optional: Save FAISS index to disk
faiss.write_index(index, "openai_embeddings.index")
