# Complete Pinecone Integration for Free/Starter Tier (2025)
# Latest Pinecone Python SDK v7.x with API version 2025-04

import warnings
import os
from tqdm import tqdm
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import uuid
import time

# Suppress the SentenceTransformer deprecation warning
warnings.filterwarnings("ignore", message=".*encoder_attention_mask.*", category=FutureWarning)

# Import Pinecone (latest SDK - install with: pip install pinecone)
from p1inecone import Pinecone, ServerlessSpec, CloudProvider, AwsRegion

def setup_pinecone_client(api_key: str):
    """
    Initialize Pinecone client with your API key.
    Get your API key from: https://app.pinecone.io
    """
    return Pinecone(api_key=api_key)

def create_or_get_index(
    pc: Pinecone, 
    index_name: str, 
    dimension: int = 384,  # all-MiniLM-L6-v2 dimension
    cloud_provider: str = "gcp-starter"  # Free tier only supports gcp-starter
) -> Any:
    """
    Create or connect to a Pinecone index.
    
    For FREE TIER (Starter Plan):
    - Only gcp-starter environment (us-central-1 region)
    - Up to 5 indexes allowed
    - 2GB storage (~300k records)
    - 100 namespaces per index
    """
    
    try:
        # Check if index exists
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        
        if index_name in existing_indexes:
            print(f"Index '{index_name}' already exists. Connecting...")
            return pc.Index(index_name)
            
        else:
            print(f"Creating new index '{index_name}' with dimension {dimension}...")
            
            # Free tier uses gcp-starter environment
            pc.create_index(
                name=index_name,
                dimension=dimension,
                spec=ServerlessSpec(
                    cloud="gcp",
                    region="us-central1"  # Only available region for free tier
                )
            )
            
            # Wait for index to be ready
            print("Waiting for index to be ready...")
            while not pc.describe_index(index_name).status['ready']:
                time.sleep(1)
            
            print(f"Index '{index_name}' created successfully!")
            return pc.Index(index_name)
            
    except Exception as e:
        print(f"Error creating/accessing index: {e}")
        raise

def generate_embeddings_for_pinecone123(
    final_chunks, 
    model, 
    batch_size: int = 32,
    show_progress: bool = True
) -> List[Tuple[str, List[float], Dict[str, Any]]]:
    """
    Generate embeddings and format them for Pinecone upsert.
    Returns list of tuples: (id, embedding_vector, metadata)
    """
    
    # Suppress warnings
    warnings.filterwarnings("ignore", message=".*encoder_attention_mask.*", category=FutureWarning)
    
    vectors_to_upsert = []
    texts = [chunk.page_content for chunk in final_chunks]
    
    if show_progress:
        print(f"Generating embeddings for {len(texts)} chunks...")
    
    # Generate embeddings in batches
    all_embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), disable=not show_progress, desc="Embedding batches"):
        batch_texts = texts[i:i + batch_size]
        batch_embeddings = model.encode(
            batch_texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=False
        )
        all_embeddings.extend(batch_embeddings)
    
    # Format for Pinecone
    for i, (chunk, embedding) in enumerate(zip(final_chunks, all_embeddings)):
        text_content = chunk.page_content
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
        
        # Create unique ID
        chunk_id = f"chunk_{i}_{str(uuid.uuid4())[:8]}"
        
        # Prepare metadata (keep it under 40KB total per vector)
        metadata = {
            "text": text_content[:1000] if len(text_content) > 1000 else text_content,  # Truncate if too long
            "chunk_index": i,
            "text_length": len(text_content)
        }
        
        # Add original metadata if exists (but keep it small)
        if hasattr(chunk, 'metadata') and chunk.metadata:
            for key, value in chunk.metadata.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    # Truncate string values to prevent metadata size issues
                    if isinstance(value, str) and len(value) > 200:
                        metadata[key] = value[:200] + "..."
                    else:
                        metadata[key] = value
        
        # Create tuple format for Pinecone upsert
        vector_tuple = (chunk_id, embedding_list, metadata)
        vectors_to_upsert.append(vector_tuple)
    
    if show_progress:
        print(f"Generated {len(vectors_to_upsert)} embeddings")
        print(f"Embedding dimension: {len(vectors_to_upsert[0][1])}")
    
    return vectors_to_upsert

def upsert_to_pinecone(
    index,
    vectors: List[Tuple[str, List[float], Dict[str, Any]]],
    namespace: str = "",
    batch_size: int = 100,
    show_progress: bool = True
) -> None:
    """
    Upsert vectors to Pinecone index in batches.
    
    FREE TIER LIMITS:
    - 2M Write Units per month
    - Each upsert operation consumes write units
    """
    
    if show_progress:
        print(f"Upserting {len(vectors)} vectors to Pinecone...")
        if namespace:
            print(f"Using namespace: '{namespace}'")
    
    # Upsert in batches to respect rate limits
    for i in tqdm(range(0, len(vectors), batch_size), disable=not show_progress, desc="Upserting"):
        batch = vectors[i:i + batch_size]
        
        try:
            if namespace:
                index.upsert(vectors=batch, namespace=namespace)
            else:
                index.upsert(vectors=batch)
                
            # Small delay to respect rate limits
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error upserting batch {i//batch_size + 1}: {e}")
            # Continue with next batch
            continue
    
    if show_progress:
        print("✅ Upsert completed successfully!")

def query_pinecone_index(
    index,
    query_vector: List[float],
    top_k: int = 5,
    namespace: str = "",
    filter_dict: Optional[Dict] = None
) -> Dict:
    """
    Query the Pinecone index.
    
    FREE TIER LIMITS:
    - 1M Read Units per month
    """
    
    try:
        if namespace:
            results = index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter_dict,
                include_metadata=True
            )
        else:
            results = index.query(
                vector=query_vector,
                top_k=top_k,
                filter=filter_dict,
                include_metadata=True
            )
        
        return results
        
    except Exception as e:
        print(f"Error querying index: {e}")
        return {}

# COMPLETE USAGE EXAMPLE
def main():
    """
    Complete example of using Pinecone with your embeddings
    """
    
    # Step 1: Set up your API key (get from https://app.pinecone.io)
    PINECONE_API_KEY = "your-pinecone-api-key-here"  # Replace with your actual key
    # Or set environment variable: os.environ["PINECONE_API_KEY"] = "your-key"
    
    # Step 2: Initialize Pinecone
    pc = setup_pinecone_client(PINECONE_API_KEY)
    
    # Step 3: Load your data and model (your existing code)
    # final_chunks = load_and_split_csv_files()  # Your chunker function
    # model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Step 4: Create or connect to index
    index_name = "shopify-products"  # Choose your index name
    dimension = 384  # all-MiniLM-L6-v2 embedding dimension
    
    index = create_or_get_index(pc, index_name, dimension)
    
    # Step 5: Generate embeddings
    # vectors_for_pinecone = generate_embeddings_for_pinecone(final_chunks, model)
    
    # Step 6: Upsert to Pinecone
    # upsert_to_pinecone(index, vectors_for_pinecone, namespace="products")
    
    # Step 7: Test query
    # query_text = "resistor electronics"
    # query_embedding = model.encode([query_text])[0].tolist()
    # results = query_pinecone_index(index, query_embedding, top_k=3, namespace="products")
    # print("Query results:", results)

if __name__ == "__main__":
    # Uncomment to run the complete example
    # main()
    pass

# QUICK START GUIDE:
"""
1. Install Pinecone: pip install pinecone
2. Get API key from: https://app.pinecone.io
3. Run your existing code:

# Your existing code
final_chunks = load_and_split_csv_files()
model = SentenceTransformer("all-MiniLM-L6-v2")

# Generate embeddings
vectors_for_pinecone = generate_embeddings_for_pinecone(final_chunks, model)

# Connect to Pinecone
pc = setup_pinecone_client("your-api-key-here")
index = create_or_get_index(pc, "my-shopify-index", 384)

# Upload to Pinecone
upsert_to_pinecone(index, vectors_for_pinecone, namespace="products")

print("✅ All vectors uploaded to Pinecone!")
"""
