import os
from sys import stderr, stdout
import json
import urllib.request
from urllib.error import URLError


def main() -> int:
    vllm_base_url = (os.environ.get("VLLM_BASE_URL") or "").strip()
    local_model = (os.environ.get("LOCAL_MODEL") or "").strip()
    if not vllm_base_url or not local_model:
        stderr.write("Health check failed: Missing or empty environment variables.\n")
        return 2
    try:
        with urllib.request.urlopen(f"{vllm_base_url}/models", timeout=2) as response:
            payload = json.load(response)
            if not isinstance(payload, dict) or "data" not in payload:
                stderr.write("Health check failed: Invalid response format.\n")
                return 1
            model_found = any(
                model.get("id") == local_model for model in payload["data"]
            )
            if model_found:
                stdout.write("Health check passed: Model found.\n")
                return 0
            else:
                stderr.write("Health check failed: Model not found.\n")
                return 1

    except (URLError, TimeoutError) as e:
        stderr.write(f"Health check failed: {e}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
