# Using a Local Host Directory (custom path)
docker run -d  --name local-mongo  -p 27017:27017  -e MONGO_INITDB_ROOT_USERNAME=root  -e MONGO_INITDB_ROOT_PASSWORD=secret  -v $(pwd)/mongo_data:/data/db  mongo:latest


# Using a Named Docker Volume (recommended)
docker run -d   --name local-mongo   -p 27017:27017   -e MONGO_INITDB_ROOT_USERNAME=root   -e MONGO_INITDB_ROOT_PASSWORD=secret   -v C:/DRIVE_D/PythonProject/chatbot_Shopify/bucket/chatRecord:/data/db  mongo:latest

# Volumne Inspection :
docker volume ls
docker volume inspect mongo_data


docker run -d   --name local-redis  -p 6379:6379  redis:latest  redis-server --appendonly yes --notify-keyspace-events Ex