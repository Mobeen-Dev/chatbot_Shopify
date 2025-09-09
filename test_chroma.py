import chromadb
chroma_client = chromadb.HttpClient(host='localhost', port=8002)
collection = chroma_client.get_collection(name="product_chunks")
chroma_client.heartbeat()
print(collection)