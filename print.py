import openai
import os
from typing import List, Dict
from langchain.docstore.document import Document
from config import settings
from sentence_transformers import SentenceTransformer
from RAG import load_and_split_csv_files, embed_documents_openai
# Set your OpenAI API key
openai.api_key = settings.openai_api_key
from p1inecone import  *


if __name__ == "__main__":
  
  chunks = load_and_split_csv_files(file_range=range(1, 2))
  print(f"Total chunks created: {len(chunks)}")
  
  # Initialize embedding model
  model = SentenceTransformer("all-MiniLM-L6-v2")
  vectors_for_pinecone = generate_embeddings_for_pinecone(chunks[:20], model)
  print(f"Total embedded chunks: {len(vectors_for_pinecone)}")
  
#   print("Example embedded vector metadata:", chunks[:10])
  
   
# #   # View an example embedded vector
# #   print(embedded_chunks[0]["metadata"])
# #   print(embedded_chunks[0]["embedding"][:5])  # Just first 5 values
  
  
#   # Step 1: Set up your API key (get from https://app.pinecone.io)
  PINECONE_API_KEY = settings.pinecone_api_key # Replace with your actual key
#   # Or set environment variable: os.environ["PINECONE_API_KEY"] = "your-key"
  
#   # Step 2: Initialize Pinecone
  pc = setup_pinecone_client(PINECONE_API_KEY)
  
#   # Step 3: Load your data and model (your existing code)
#   # final_chunks = load_and_split_csv_files()  # Your chunker function
#   # model = SentenceTransformer("all-MiniLM-L6-v2")
  
  # Step 4: Create or connect to index
  index_name = "shopify-products"  # Choose your index name
  dimension = 384  # all-MiniLM-L6-v2 embedding dimension
  
  index = create_or_get_index(pc, index_name, dimension)
  
#   # Step 5: Generate embeddings
# #   vectors_for_pinecone = generate_embeddings_for_pinecone(final_chunks, model)
  
#   # Step 6: Upsert to Pinecone
#   upsert_to_pinecone(index, vectors_for_pinecone, namespace="products")
    
  # Step 7: Test query
  query_text = "2 Watt 5% Resistor In Pakistan"
  query_embedding = model.encode([query_text])[0].tolist()
  results = query_pinecone_index(index, query_embedding, top_k=3, namespace="products")
  print("Query results:", results)
