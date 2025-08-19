import faiss
import numpy as np

# Parameters
d = 3072          # dimension
nb = 100_000      # database size
nlist = 2048      # number of IVF clusters (tunable)
m = 64            # number of PQ subquantizers (must divide d)
nbits = 8         # bits per code (256 centroids per subquantizer)

# Generate synthetic data (replace with your actual vectors)
np.random.seed(123)
x = np.random.random((nb, d)).astype('float32')

# Step 1. Coarse quantizer for IVF
quantizer = faiss.IndexFlatL2(d)  # used for clustering

# Step 2. IVF + PQ index
ivfpq_index = faiss.IndexIVFPQ(quantizer, d, nlist, m, nbits)

# Step 3. Wrap with refine flat BEFORE training/adding
index = faiss.IndexRefineFlat(ivfpq_index)

# Step 4. Train (on a random subset of x)
train_samples = x[np.random.choice(nb, size=79872, replace=False)]
print("Training...")
index.train(train_samples)    # type: ignore
print("Done training.")

# Step 5. Add database vectors (goes into both indices)
print("Adding vectors...")
index.add(x) # type: ignore
print("Index size:", index.ntotal)

# Step 6. Search
topk = 10  # number of nearest neighbors to retrieve
query = np.random.random((5, d)).astype('float32')  # 5 random queries

# nprobe controls how many IVF clusters to search
ivfpq_index.nprobe = 16

print("Searching...")
D, I = index.search(query, topk)   # type: ignore
print("Refined Distances:\n", D)
print("Refined Indices:\n", I)
