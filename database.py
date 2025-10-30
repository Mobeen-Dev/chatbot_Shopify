import faiss
import pickle
import asyncio
import numpy as np
from openai import AsyncOpenAI
from config import settings, vectorDb_index_path, embedding_model, id_to_product_mapping


class vectorDB:
    def __init__(
        self,
        index_path: str = vectorDb_index_path,
        model: str = embedding_model,
    ):
        self.model = model
        # self.client = AsyncOpenAI(api_key=settings.openai_api_key,)  # async client
        self.db_client = faiss.read_index(index_path + ".index")
        with open(index_path + "_meta.pkl", "rb") as f:
            self.metadata = pickle.load(f)
        with open(id_to_product_mapping, "rb") as f:
            self.data_dict = pickle.load(f)

        # print(len(self.data_dict))
        # print(self.data_dict['8190612144406'])

    # async def aclose(self):
    #     await self.client.close()

    async def query(
        self,
        query: str,
        top_k: int = 5,
    ):
        # 1. Async call to OpenAI for embedding
        try:
            response = None
            async with AsyncOpenAI(
                api_key=settings.openai_api_key,
            ) as client:
                # Perform your asynchronous OpenAI API calls here
                response = await client.embeddings.create(
                    model=self.model, input=[query]
                )
        except Exception as e:
            raise RuntimeError(f"Embedding API failed: {e}")

        if not response or not response.data:
            raise ValueError("Failed to embed query.")

        query_embedding = response.data[0].embedding
        query_embedding = np.array([query_embedding]).astype("float32")
        faiss.normalize_L2(query_embedding)

        # 2. Run Faiss (sync) in a thread so it doesn’t block event loop
        distances, indices = await asyncio.to_thread(
            self.db_client.search,
            query_embedding,  # xq
            top_k,  # k
        )

        # print("Distances:\n", distances)
        # print("Labels (indices of nearest neighbors):\n", indices)

        if (
            distances is None
            or indices is None
            or len(distances) == 0
            or len(indices) == 0
        ):
            return []

        seen_ids = set()
        result = []

        for distance, idx in zip(distances[0], indices[0]):
            print("Index", idx)
            score = 1 / distance
            unique_id = self.metadata[idx - 1]["id"] # MetaData is 0 Based Indexed And Faiss is 1 Based Indexed
            if unique_id not in seen_ids:
                seen_ids.add(unique_id)
                # if self.data_dict[unique_id][]
                result.append(
                    {
                        "score": round(float(score), 3),
                        "content": self.data_dict[unique_id],
                        "metadata": {
                          "Handle": self.data_dict[unique_id]["handle"],
                          "Score": round(float(score), 3),
                          "Query": query,
                        },
                    }
                )

        return result


if __name__ == "__main__":
    store = vectorDB()
    user_query = 'microcontroller development board ESP32 Arduino Raspberry Pi Pico Arduino Nano IoT development board WiFi BLE LoRa STM32 development board'
    wow = "nodemcu esp8266 esp32 development board 1 channel relay module 2 channel 4 channel 5V power supply breadboard jumper wires components for DIY IoT switchboard mobile control"
    matches = asyncio.run(store.query(query=user_query, top_k=20))
    print(matches)
    for i, match in enumerate(matches):
        print("{")
        print(f"\nMatch {i + 1}:")
        print(f"Score: {match['score']:.4f}")
        # print(f"Metadata: {match['metadata']}")
        print(f"Content:\n{match['content']}")
        print("}")
