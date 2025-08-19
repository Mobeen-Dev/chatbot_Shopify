import os
import csv
from typing import Generator, List
from langchain.docstore.document import Document
from langchain_community.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
from config import settings
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

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
def embed_and_save_to_chroma(
    persist_directory: str = "chroma_store",
    collection_name: str = "product_chunks",
    batch_size: int = 100,
    model: str = "text-embedding-3-small",
):
    if not os.path.exists(persist_directory):
        os.makedirs(persist_directory)
    # Chroma client
    client = chromadb.PersistentClient(path=persist_directory)

    # Use OpenAI embedding function wrapper
    embedding_fn = OpenAIEmbeddingFunction(
        api_key=openai.api_key,
        model_name=model
    )
    def get_embedding(text, model="text-embedding-ada-002"):
        response = openai.embeddings.create(input=text, model=model)
        return response.data[0].embedding

    # Create or load collection (with embedding_fn provided at add-time, not creation-time)
    if collection_name not in [c.name for c in client.list_collections()]:
        collection = client.create_collection(name=collection_name)
    else:
        collection = client.get_collection(name=collection_name)

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

class ChromaRetriever:
    def __init__(self, persist_directory: str = "chroma_store", collection_name: str = "product_chunks", model: str = "text-embedding-3-small"):
        
        self.model = model
        
        # Connect to Chroma
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_collection(name=collection_name)
        
    def query_chroma(
        self,
        query: str,       
        top_k: int = 5,
    ):

        # Embed user query
        try:
            response = openai.embeddings.create(input=[query], model=self.model)
        except Exception as e:
            raise RuntimeError(f"Embedding API failed: {e}")

        if not response or not response.data:
            raise ValueError("Failed to embed query.")

        query_embedding = response.data[0].embedding

        # Query vector DB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        docs, metas, dists = results.get("documents"), results.get("metadatas"), results.get("distances")

        if not docs or not metas or not dists or not docs[0]:
            return []

        return [
            {"content": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(docs[0], metas[0], dists[0])
        ]

# Code to Build the vector store
# Uncomment the following lines to run the embedding and saving process
# if __name__ == "__main__":
#     embed_and_save_to_chroma(
#         persist_directory="chroma_store",
#         collection_name="product_chunks",
#         batch_size=100
#     )
    
if __name__ == "__main__":
    store = ChromaRetriever()
    user_query = "Do you have MICRO CONTROLLER like arduino?"
    matches = store.query_chroma(query=user_query, top_k=5)

    for i, match in enumerate(matches):
        print(f"\nMatch {i + 1}:")
        print(f"Distance: {match['distance']:.4f}")
        print(f"Metadata: {match['metadata']}")
        print(f"Content:\n{match['content']}")
        print("-" * 80)