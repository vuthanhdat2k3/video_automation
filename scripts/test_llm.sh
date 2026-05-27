#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Load .env
export $(grep -v '^#' .env | xargs 2>/dev/null) || true

echo "=== LLM Connection Test ==="
echo "URL:   $LLM_BASE_URL"
echo "Model: $LLM_MODEL"
echo ""

HOST=$(echo "$LLM_BASE_URL" | sed -E 's|https?://([^:/]+).*|\1|')
PORT=$(echo "$LLM_BASE_URL" | sed -E 's|https?://[^:/]+:?([0-9]*).*|\1|')
PORT=${PORT:-80}

# 1. Ping
echo "--- Ping $HOST ---"
if ping -c 1 -W 3 "$HOST" &>/dev/null; then
    echo "OK  ($(ping -c 1 -W 3 "$HOST" | tail -1 | awk '{print $4}'))"
else
    echo "FAIL"
fi
echo ""

# 2. TCP port
echo "--- TCP $HOST:$PORT ---"
if timeout 5 bash -c "echo > /dev/tcp/$HOST/$PORT" 2>/dev/null; then
    echo "OK  (port open)"
else
    echo "FAIL"
fi
echo ""

# 3. Chat completion via OpenAI Python client
echo "--- Chat Completion ---"
source .venv/bin/activate 2>/dev/null || true
python3 << 'EOF' 2>&1
import os, time
from openai import OpenAI

base_url = os.getenv("LLM_BASE_URL", "http://100.92.219.30:3505/openai/v1")
api_key = os.getenv("LLM_API_KEY", "sk-bf-6122bdad-df9a-4c9c-957e-47124ac97574")
model = os.getenv("LLM_MODEL", "sunllm_v2/Qwen3.6-35B-A3B-Q8_0")

# Ensure trailing slash for base_url
if not base_url.endswith("/"):
    base_url += "/"

client = OpenAI(base_url=base_url, api_key=api_key)

# Test text
print(f"  Text: ", end="", flush=True)
start = time.time()
resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Say hello in 3 words"}],
    max_tokens=20, temperature=0.1,
)
text = resp.choices[0].message.content
print(f"[{time.time()-start:.1f}s] {text}")

# Test streaming
print(f"  Stream: ", end="", flush=True)
start = time.time()
stream = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Count 1 to 3"}],
    max_tokens=50, temperature=0.1, stream=True,
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print(f"  [{time.time()-start:.1f}s]")

print("\n✅ LLM OK")
EOF
