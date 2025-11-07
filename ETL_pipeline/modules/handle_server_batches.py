import json
import os
from openai import OpenAI
from config import settings
# ✅ Init client
client = OpenAI(api_key=settings.openai_api_key)

# ✅ Path to local batch record
JSON_PATH = "./bucket/index_storage/batch_responses.json"


def load_batches():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_batches(batches):
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(batches, f, indent=2)
    print("✅ Updated batch records saved.")


def get_server_status(batch_id):
    """Retrieve the latest batch details from OpenAI server"""
    try:
        batch = client.batches.retrieve(batch_id)
        return batch
    except Exception as e:
        print(f"⚠️ Could not retrieve batch {batch_id}: {e}")
        return None


def retry_batch(old_batch):
    """Submit a new batch using same input file + settings"""
    print(f"🔁 Retrying batch {old_batch.id}")

    new_batch = client.batches.create(
        input_file_id=old_batch.input_file_id,
        endpoint=old_batch.endpoint,               # e.g. "/v1/embeddings"
        completion_window=old_batch.completion_window,
        metadata=old_batch.metadata
    )

    print(f"✅ New batch created: {new_batch.id}")
    return new_batch


def process_batches():
    stored = load_batches()
    updated = []

    for record in stored:
        batch_id = record["id"]
        print(f"🔎 Checking batch: {batch_id}")

        live = get_server_status(batch_id)
        if not live:
            updated.append(record)
            continue

        status = live.status
        failed_reqs = live.request_counts.failed

        print(f" → Server status: {status}, failed_requests={failed_reqs}")

        needs_retry = False

        # Primary failure condition
        if status == "failed":
            needs_retry = True

        # Handle partial failures
        elif failed_reqs > 0:
            needs_retry = True

        if needs_retry:
            new_batch = retry_batch(live)
            updated.append(new_batch.model_dump())
        else:
            updated.append(live.model_dump())

    save_batches(updated)


if __name__ == "__main__":
    process_batches()
