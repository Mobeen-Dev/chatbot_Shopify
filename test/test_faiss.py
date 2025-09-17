import numpy as np
import faiss
import psutil, os

# Parameters
d = 3027  # dimension
n = 1_000_000  # number of vectors

# Generate 1M random vectors (float32)
xb = np.random.rand(n, d).astype("float16")

# Check process memory before FAISS
process = psutil.Process(os.getpid())
print("Memory before FAISS:", process.memory_info().rss / (1024**3), "GB")

# Create a FAISS CPU index (L2 distance)
index = faiss.IndexFlatL2(d)  # CPU-based
print("Is index trained?", index.is_trained)

# Add all vectors to the index
index.add(xb)  # type: ignore
print("Vectors in index:", index.ntotal)

# Check process memory after loading vectors into FAISS
print("Memory after FAISS:", process.memory_info().rss / (1024**3), "GB")

# Example query (retain in memory, just to prove it's alive)
xq = xb[0:5]  # take first 5 vectors as query
D, I = index.search(xq, k=5)  # search top-5 nearest # type: ignore
print("Search result indices:", I)
