import os
import csv
import uuid
import time
from typing import Generator, List, Dict, Any, Tuple
from langchain.docstore.document import Document
from langchain_community.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
from config import settings, embeddind_model
from tqdm import tqdm

# Import Pinecone (latest SDK - install with: pip install pinecone)
from pinecone import Pinecone, ServerlessSpec

# Configure your OpenAI key
openai.api_key = settings.openai_api_key

# 1. Generator for chunk streaming (same as your original)
def stream_chunks_from_csv(
    folder_path: str = "Data",
    file_prefix: str = "products_export_",
    file_range: range = range(1, 4),
    record_chunk_size: int = 1000,
    record_chunk_overlap: int = 100,
    description_chunk_size: int = 500,
    description_chunk_overlap: int = 70,
) -> Generator[Document, None, None]:
    csv.field_size_limit(10**7)
    record_splitter = RecursiveCharacterTextSplitter(
        chunk_size=record_chunk_size,
        chunk_overlap=record_chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    description_splitter = RecursiveCharacterTextSplitter(
        chunk_size=description_chunk_size,
        chunk_overlap=description_chunk_overlap,
        separators=["\n", ".", " ", ""],
    )
    for i in file_range:
        csv_path = f"{folder_path}/{file_prefix}{i}.csv"
        loader = CSVLoader(file_path=csv_path, encoding='utf-8', csv_args={'delimiter': ','}, metadata_columns=['Handle'])
        try:
            documents = loader.load()
        except Exception as e:
            print(f"Error loading {csv_path}: {e}")
            continue
        split_records = record_splitter.split_documents(documents)
        for doc in split_records:
            if 'description' in doc.metadata.get('source', '') or 'description' in doc.page_content.lower():
                chunks = description_splitter.split_documents([doc])
            else:
                chunks = [doc]
            for chunk in chunks:
                if chunk.page_content.strip():
                    yield chunk

# 2. Pinecone setup functions
def setup_pinecone_client(api_key: str) -> Pinecone:
    """Initialize Pinecone client with your API key."""
    return Pinecone(api_key=api_key)

def create_or_get_index(
    pc: Pinecone, 
    index_name: str, 
    dimension: int = 3072,  # OpenAI text-embedding-3-large dimension
    cloud_provider: str = "aws"
) -> Any:
    """Create or connect to a Pinecone index."""
    
    try:
        # Check if index exists
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        
        if index_name in existing_indexes:
            print(f"Index '{index_name}' already exists. Connecting...")
            return pc.Index(index_name)
            
        else:
            print(f"Creating new index '{index_name}' with dimension {dimension}...")
            
            pc.create_index(
                name=index_name,
                dimension=dimension,
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"  # Free tier region
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

# 3. OpenAI embedding function
def get_openai_embedding(text: str, model: str = embeddind_model) -> List[float]:
    """Get embedding from OpenAI API."""
    try:
        response = openai.embeddings.create(input=text, model=model)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        raise

def get_openai_embeddings_batch(texts: List[str], model: str = embeddind_model) -> List[List[float]]:
    """Get embeddings for multiple texts in batch."""
    try:
        response = openai.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"Error getting batch embeddings: {e}")
        raise

# 4. Convert chunks to Pinecone format with OpenAI embeddings
def prepare_chunks_for_pinecone(
    chunks: List[Document], 
    start_index: int,
    model: str = embeddind_model
) -> List[Tuple[str, List[float], Dict[str, Any]]]:
    """Convert Document chunks to Pinecone format with OpenAI embeddings."""
    
    texts = [chunk.page_content.strip() for chunk in chunks]
    
    # Get embeddings from OpenAI in batch
    embeddings = get_openai_embeddings_batch(texts, model)
    
    vectors_to_upsert = []
    
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        text_content = chunk.page_content.strip()
        
        # Create unique ID
        chunk_id = f"doc-{start_index + i}-{str(uuid.uuid4())[:8]}"
        
        # Prepare metadata (keep it under 40KB total per vector)
        metadata = {
            "text": text_content[:1000] if len(text_content) > 1000 else text_content,
            "chunk_index": start_index + i,
            "text_length": len(text_content)
        }
        
        # Add original metadata if exists
        if hasattr(chunk, 'metadata') and chunk.metadata:
            for key, value in chunk.metadata.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    # Truncate string values to prevent metadata size issues
                    if isinstance(value, str) and len(value) > 200:
                        metadata[key] = value[:200] + "..."
                    else:
                        metadata[key] = value
        
        # Create tuple format for Pinecone upsert
        vector_tuple = (chunk_id, embedding, metadata)
        vectors_to_upsert.append(vector_tuple)
    
    return vectors_to_upsert

# 5. Save batch to Pinecone
def save_batch_to_pinecone(
    chunks: List[Document], 
    index, 
    start_index: int,
    namespace: str = "",
    model: str = embeddind_model
):
    """Save a batch of chunks to Pinecone."""
    try:
        # Prepare vectors with embeddings
        vectors = prepare_chunks_for_pinecone(chunks, start_index, model)
        
        # Upsert to Pinecone
        if namespace:
            index.upsert(vectors=vectors, namespace=namespace)
        else:
            index.upsert(vectors=vectors)
            
        # Small delay to respect rate limits
        time.sleep(0.1)
        
    except Exception as e:
        print(f"Pinecone save failed for batch starting at {start_index}: {e}")
        raise

# 6. Main embedding and saving function
def embed_and_save_to_pinecone(
    index_name: str = "shopify-products",
    namespace: str = "products",
    batch_size: int = 50,  # Smaller batch for OpenAI API limits
    model: str = embeddind_model,
    pinecone_api_key: str = ''
):
    """Embed chunks and save to Pinecone."""
    
    # Setup Pinecone
    api_key = settings.pinecone_api_key
    pc = setup_pinecone_client(api_key)
    
    # Create or get index (3072  dimensions for text-embedding-3-large)
    index = create_or_get_index(pc, index_name, dimension=3072 )
    
    # Process chunks in batches
    chunk_generator = stream_chunks_from_csv()
    buffer = []
    processed = 0
    
    print(f"Starting to process chunks in batches of {batch_size}...")
    
    for i, chunk in enumerate(chunk_generator):
        buffer.append(chunk)
        
        if len(buffer) >= batch_size:
            print(f"Processing batch {processed // batch_size + 1}...")
            save_batch_to_pinecone(
                buffer, 
                index, 
                start_index=processed,
                namespace=namespace,
                model=model
            )
            processed += len(buffer)
            print(f"Saved batch. Total processed so far: {processed}")
            buffer = []
    
    # Save remaining chunks
    if buffer:
        print(f"Processing final batch...")
        save_batch_to_pinecone(
            buffer, 
            index, 
            start_index=processed,
            namespace=namespace,
            model=model
        )
        print(f"Saved final batch. Total processed: {processed + len(buffer)}")
    
    print("✅ All chunks uploaded to Pinecone!")

# 7. Query Pinecone
# def query_pinecone(
#     query: str,
#     index_name: str = "shopify-products",
#     namespace: str = "products",
#     top_k: int = 5,
#     model: str = embeddind_model,
#     pinecone_api_key: str = ''
# ):
#     """Query Pinecone index."""
    
#     # Setup Pinecone
#     api_key = pinecone_api_key or settings.pinecone_api_key
#     pc = setup_pinecone_client(api_key)
#     index = pc.Index(index_name)
    
#     # Get query embedding
#     query_embedding = get_openai_embedding(query, model)
    
#     # Query Pinecone
#     try:
#         if namespace:
#             results = index.query(
#                 vector=query_embedding,
#                 top_k=top_k,
#                 namespace=namespace,
#                 include_metadata=True
#             )
#         else:
#             results = index.query(
#                 vector=query_embedding,
#                 top_k=top_k,
#                 include_metadata=True
#             )
        
#         # Format results similar to your ChromaDB format
#         matched_chunks = []
#         if results and 'matches' in results:
#             for match in results['matches']:
#                 matched_chunks.append({
#                     "content": match.get('metadata', {}).get('text', ''),
#                     "metadata": match.get('metadata', {}),
#                     "score": match.get('score', 0),  # Pinecone uses similarity score
#                     "id": match.get('id', '')
#                 })
        
#         return matched_chunks
        
#     except Exception as e:
#         print(f"Error querying Pinecone: {e}")
#         return []

# 8. Main execution
if __name__ == "__main__":
    # Uncomment to build the vector store
    embed_and_save_to_pinecone(
        index_name="shopify-products",
        namespace="products",
        batch_size=150,  # Adjust based on your OpenAI rate limits
        model=embeddind_model
    )
    
    # Query example
    # user_query = "Do you have MICRO CONTROLLER like arduino?"
    # matches = query_pinecone(
    #     query=user_query, 
    #     top_k=5,
    #     index_name="shopify-products",
    #     namespace="products"
    # )
    
    # for i, match in enumerate(matches):
    #     print(f"\nMatch {i + 1}:")
    #     print(f"Score: {match['score']:.4f}")  # Similarity score (higher is better)
    #     print(f"ID: {match['id']}")
    #     print(f"Metadata: {match['metadata']}")
    #     print(f"Content:\n{match['content']}")