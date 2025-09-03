from wrapper_chroma import ChromaRetriever
import asyncio
retriver = ChromaRetriever()
results = asyncio.run(retriver.query_chroma(query="wifi capability micro controller", top_k=5+3))
print(results)