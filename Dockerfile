# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Disable Python buffering & pip cache (speeds up containers)
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Put everything under /app
WORKDIR /app

# Install system dependencies (required for building Python wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*


# Install dependencies first for better layer-caching
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of your source code
COPY . .
RUN sed -i 's/\r$//' entrypoint.sh
# make entrypoint.sh executable
RUN chmod +x entrypoint.sh
# Set proper permissions for storage directories
RUN chmod -R 755 /app/bucket

# Expose the FastAPI port
EXPOSE 8000

# Health check
# HEALTHCHECK --interval=20s --timeout=10s --start-period=60s --retries=3 \
#   CMD curl -f http://localhost:8000/health || exit 1

# Run FastApi server / Worker / Scheduler
ENTRYPOINT ["./entrypoint.sh"]

# # Install dependencies
# RUN apt-get update && apt-get install -y wget unzip

# # Install ngrok
# RUN wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip \
#     && unzip ngrok-v3-stable-linux-amd64.zip \
#     && mv ngrok /usr/local/bin/ngrok \
#     && rm ngrok-v3-stable-linux-amd64.zip





# # Start your app (edit the module path if it’s not main.py ⇢ app variable)
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

