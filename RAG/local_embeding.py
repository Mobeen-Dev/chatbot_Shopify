import warnings
from tqdm import tqdm
import numpy as np
from typing import List, Dict, Any, Optional
import uuid

def generate_embeddings_for_pinecone(
    final_chunks, 
    model, 
    batch_size: int = 32,
    show_progress: bool = True,
    include_direct_embedding: bool = True
) -> List[Dict[str, Any]]:
    """
    Generate embeddings from chunks and format for Pinecone insertion.
    Handles deprecation warnings and provides optimized batch processing.
    
    Args:
        final_chunks: List of LangChain Document objects from the chunker
        model: SentenceTransformer model instance
        batch_size: Batch size for embedding generation (default: 32)
        show_progress: Whether to show progress bar (default: True)
        include_direct_embedding: Whether to include direct "embedding" key (default: True)
        
    Returns:
        List of dictionaries formatted for Pinecone upsert operation
    """
    
    # Suppress the specific deprecation warning
    warnings.filterwarnings("ignore", message=".*encoder_attention_mask.*", category=FutureWarning)
    
    vectors_to_upsert = []
    
    # Extract all text content first
    texts = [chunk.page_content for chunk in final_chunks]
    
    # Process in batches for efficiency
    all_embeddings = []
    
    if show_progress:
        print(f"Generating embeddings for {len(texts)} chunks...")
    
    # Generate embeddings in batches
    for i in tqdm(range(0, len(texts), batch_size), disable=not show_progress, desc="Embedding batches"):
        batch_texts = texts[i:i + batch_size]
        
        # Generate embeddings for the batch
        batch_embeddings = model.encode(
            batch_texts,
            show_progress_bar=False,  # Disable inner progress bar
            convert_to_numpy=True,
            normalize_embeddings=False  # Keep original embeddings
        )
        
        all_embeddings.extend(batch_embeddings)
    
    # Format each chunk with its embedding
    for i, (chunk, embedding) in enumerate(zip(final_chunks, all_embeddings)):
        text_content = chunk.page_content
        
        # Convert numpy array to list for JSON serialization
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
        
        # Create unique ID - using UUID for better uniqueness
        chunk_id = f"chunk_{i}_{str(uuid.uuid4())[:8]}"
        
        # Prepare comprehensive metadata
        metadata = {
            "text": text_content,
            "chunk_index": i,
            "text_length": len(text_content),
            "embedding_model": model.get_sentence_embedding_dimension() if hasattr(model, 'get_sentence_embedding_dimension') else None
        }
        
        # Add original metadata if it exists
        if hasattr(chunk, 'metadata') and chunk.metadata:
            # Clean metadata - ensure all values are JSON serializable
            for key, value in chunk.metadata.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    metadata[key] = value
                else:
                    metadata[key] = str(value)
        
        # Create the vector data structure
        vector_data = {
            "id": chunk_id,
            "values": embedding_list,  # Pinecone format
            "metadata": metadata
        }
        
        # Add direct embedding access if requested
        if include_direct_embedding:
            vector_data["embedding"] = embedding_list
        
        vectors_to_upsert.append(vector_data)
    
    if show_progress:
        print(f"Total embedded chunks: {len(vectors_to_upsert)}")
        print(f"Embedding dimension: {len(vectors_to_upsert[0]['values']) if vectors_to_upsert else 'N/A'}")
    
    return vectors_to_upsert


def upsert_to_pinecone_in_batches(
    index, 
    vectors: List[Dict[str, Any]], 
    upsert_batch_size: int = 100,
    show_progress: bool = True
) -> None:
    """
    Upsert vectors to Pinecone in batches to handle large datasets efficiently.
    
    Args:
        index: Pinecone index object
        vectors: List of vector dictionaries from generate_embeddings_for_pinecone
        upsert_batch_size: Batch size for Pinecone upserts (default: 100)
        show_progress: Whether to show progress bar
    """
    
    if show_progress:
        print(f"Upserting {len(vectors)} vectors to Pinecone in batches of {upsert_batch_size}...")
    
    for i in tqdm(range(0, len(vectors), upsert_batch_size), disable=not show_progress, desc="Upserting batches"):
        batch = vectors[i:i + upsert_batch_size]
        
        # Remove the direct "embedding" key before upserting to Pinecone
        pinecone_batch = []
        for vector in batch:
            pinecone_vector = {
                "id": vector["id"],
                "values": vector["values"],
                "metadata": vector["metadata"]
            }
            pinecone_batch.append(pinecone_vector)
        
        try:
            index.upsert(vectors=pinecone_batch)
        except Exception as e:
            print(f"Error upserting batch {i//upsert_batch_size + 1}: {e}")
            continue
    
    if show_progress:
        print("Upsert completed successfully!")


# Usage example:
"""
# Load your data
final_chunks = load_and_split_csv_files()
model = SentenceTransformer("all-MiniLM-L6-v2")

# Generate embeddings
embedded_chunks = generate_embeddings_for_pinecone(
    final_chunks, 
    model, 
    batch_size=32,
    show_progress=True,
    include_direct_embedding=True
)

# Now you can access embeddings directly
print(f"First embedding shape: {len(embedded_chunks[0]['embedding'])}")
print(f"First 5 embedding values: {embedded_chunks[0]['embedding'][:5]}")

# Upsert to Pinecone (assuming you have your index set up)
# upsert_to_pinecone_in_batches(index, embedded_chunks, upsert_batch_size=100)
"""