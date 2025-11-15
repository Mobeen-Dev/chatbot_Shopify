import os
import json
import numpy as np
import matplotlib.pyplot as plt
import tiktoken

data_folder = "embed_job_data"  # folder where your jsonl files are

# Load GPT tokenizer
encoding = tiktoken.get_encoding("cl100k_base")

# Collect all text inputs
texts = []

for file in sorted(os.listdir(data_folder)):
    if file.endswith(".jsonl"):
        path = os.path.join(data_folder, file)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    text = obj.get("body", {}).get("input", "")
                    if text:
                        texts.append(text)
                except json.JSONDecodeError:
                    continue

print(f"Total chunks loaded: {len(texts)}")

# Compute token lengths
token_lengths = [len(encoding.encode(t)) for t in texts]

# Stats
print(f"Mean tokens: {np.mean(token_lengths):.2f}")
print(f"Median tokens: {np.median(token_lengths):.2f}")
print(f"95th percentile: {np.percentile(token_lengths, 95):.2f}")
print(f"Max tokens: {np.max(token_lengths):.2f}")

# Visualization

plt.figure(figsize=(12,6))
plt.hist(token_lengths, bins=80, alpha=0.7)
plt.title("Token Length Distribution for Product Chunks")
plt.xlabel("Token Length")
plt.ylabel("Number of Chunks")
plt.grid(True)
plt.show()

plt.figure(figsize=(8,3))
plt.boxplot(token_lengths, vert=False)
plt.title("Token Length Boxplot")
plt.xlabel("Token Count")
plt.grid(True)
plt.show()
