"""Which models does my key actually have? Prints the real error if it fails."""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("LLM_API_KEY", "")
base = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")

print(f"key loaded: {bool(key)}  starts with: {key[:4]!r}  length: {len(key)}")

r = httpx.get(
    f"{base}/models",
    headers={"Authorization": f"Bearer {key}"},
    timeout=30,
)
print(f"status: {r.status_code}")

if r.status_code != 200:
    print(r.text[:600])
    raise SystemExit(1)

for m in sorted(d["id"] for d in r.json()["data"]):
    print(" ", m)