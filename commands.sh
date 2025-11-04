

# Using a Local Host Directory (custom path)
docker run -d  --name local-mongo  -p 27017:27017  -e MONGO_INITDB_ROOT_USERNAME=root  -e MONGO_INITDB_ROOT_PASSWORD=secret  -v $(pwd)/mongo_data:/data/db  mongo:latest

# Using a Named Docker Volume (recommended)
docker run -d   --name local-mongo   -p 27017:27017   -e MONGO_INITDB_ROOT_USERNAME=root   -e MONGO_INITDB_ROOT_PASSWORD=secret   -v C:/DRIVE_D/PythonProject/chatbot_Shopify/bucket/chatRecord:/data/db  mongo:latest

# Volumne Inspection :
docker volume ls
docker volume inspect mongo_data

docker run -d   --name local-redis  -p 6379:6379  redis:latest  redis-server --appendonly yes --notify-keyspace-events Ex


docker run -d --rm --name chromadb -p 9001:9001  -v /C:/DRIVE_D/PythonProject/chatbot_Shopify/chroma_store:/data/chroma_store  chromadb/chroma:latest   run --host 0.0.0.0 --port 9001 --path /data/chroma_store

# for realtime access of folder content:
sudo chmod -R 755 /path/to/prompt_folder

import chromadb
from chromadb.config import Settings

client = chromadb.HttpClient(host="localhost", port=9001, settings=Settings())

# ETL Job Execution
# start new job
python -m ETL_pipeline.pipeline --chunk_products --upload_chunks --start_embedding_job