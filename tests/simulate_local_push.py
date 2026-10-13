"""Simulates a Google Cloud Storage -> Pub/Sub push event against a running local or remote endpoint."""

import argparse
import base64
import json
import sys
import urllib.request
import urllib.error


def send_simulated_event(url: str, bucket: str, object_name: str, event_type: str = "OBJECT_FINALIZE"):
    gcs_payload = {
        "kind": "storage#object",
        "name": object_name,
        "bucket": bucket,
        "size": "2048",
        "contentType": "application/octet-stream",
    }
    encoded_data = base64.b64encode(json.dumps(gcs_payload).encode("utf-8")).decode("utf-8")

    pubsub_body = {
        "message": {
            "data": encoded_data,
            "attributes": {
                "eventType": event_type,
                "bucketId": bucket,
                "objectId": object_name,
            },
            "messageId": "simulated-test-message-1",
            "publishTime": "2026-10-13T20:00:00Z",
        },
        "subscription": "projects/simulation/subscriptions/local-push",
    }

    req_data = json.dumps(pubsub_body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"[*] Sending simulated Pub/Sub event for gs://{bucket}/{object_name} to {url}...")
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            print(f"[+] HTTP {status_code} Response:")
            try:
                parsed = json.loads(body)
                print(json.dumps(parsed, indent=2))
            except json.JSONDecodeError:
                print(body)
    except urllib.error.HTTPError as e:
        print(f"[-] HTTP Error {e.code}: {e.read().decode('utf-8')}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[-] Connection Error: {e.reason}")
        print("    Ensure the FastAPI service is running (e.g., uvicorn app.main:app --port 8080).")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Pub/Sub GCS push notification to Cloud Run service.")
    parser.add_argument("--url", default="http://localhost:8080/", help="Target endpoint URL (default: http://localhost:8080/)")
    parser.add_argument("--bucket", default="sample-doc-bucket", help="GCS bucket name")
    parser.add_argument("--object", default="invoices/october_invoice.pdf", help="Object path/filename")
    parser.add_argument("--event", default="OBJECT_FINALIZE", help="GCS event type (default: OBJECT_FINALIZE)")

    args = parser.parse_args()
    send_simulated_event(args.url, args.bucket, args.object, args.event)
