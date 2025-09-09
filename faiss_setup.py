import os
import csv
from typing import Generator, List
from langchain.docstore.document import Document
from langchain_community.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
from config import settings, embeddind_model, vector_db_collection_name
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import asyncio
from openai import AsyncOpenAI
import asyncio


# Configure your OpenAI key
openai.api_key = settings.openai_api_key

# 1. Generator for chunk streaming
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

# 2. Embed and save to Chroma
def embed_and_save_to_faiss(
    persist_directory: str = "faiss_store",
    collection_name: str = "product_chunks",
    batch_size: int = 100,
    model: str = embeddind_model,
):
    if not os.path.exists(persist_directory):
        os.makedirs(persist_directory)
    # Chroma client
    
    def get_embedding(text, model="text-embedding-ada-002"):
        response = openai.embeddings.create(input=text, model=model)
        return response.data[0].embedding

    
    chunk_generator = stream_chunks_from_csv()
    buffer = []
    processed = 0

    for i, chunk in enumerate(chunk_generator):
        buffer.append(chunk)

        if len(buffer) >= batch_size:
            _save_batch_to_chroma(buffer, collection, embedding_fn, start_index=i - len(buffer) + 1)
            processed += len(buffer)
            print(f"Saved batch. Total processed so far: {processed}")
            buffer = []

    if buffer:
        _save_batch_to_chroma(buffer, collection, embedding_fn, start_index=processed)
        print(f"Saved final batch. Total processed: {processed + len(buffer)}")

    # Persist automatically handled by chromadb (as of newer versions)


def _save_batch_to_chroma(chunks: List[Document], collection, embedding_fn, start_index: int):
    texts = [doc.page_content.strip() for doc in chunks]
    metadatas = [doc.metadata for doc in chunks]
    ids = [f"doc-{start_index + i}" for i in range(len(chunks))]

    try:
        embeddings = embedding_fn(texts)  # Call OpenAI here manually

        collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
    except Exception as e:
        print(f"Chroma save failed for batch starting at {start_index}: {e}")

# Code to Build the vector store
# Uncomment the following lines to run the embedding and saving process
if __name__ == "__main__":
    embed_and_save_to_chroma(
        persist_directory="faiss_store",
        collection_name="product_chunks",
        batch_size=100
    )
    
    