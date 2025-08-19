from openai import OpenAI
from config import settings
client = OpenAI(api_key=settings.openai_api_key,)

res = client.embeddings.create(
    model="text-embedding-3-large",
    input="hello world"
)

vec = res.data[0].embedding
print(type(vec), len(vec), vec[:5], type(vec[0]))
