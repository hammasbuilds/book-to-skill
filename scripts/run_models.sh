#!/usr/bin/env bash
# Run the model arm end to end: the model-written skill for both books, then
# closed-book / RAG / skill / skill+RAG answering, judged by the same model.
#
#   scripts/run_models.sh --dry-run   print the job list and call count, call nothing
#   scripts/run_models.sh             check resources, then run (resumable: every
#                                     generation is cached in data/cache/llm)
#
# Environment overrides: OLLAMA_URL (default http://127.0.0.1:11434),
# MODEL (default qwen2.5:14b-instruct), MIN_FREE_RAM_GB (8), MIN_FREE_VRAM_GB (10),
# SECONDS_PER_CALL (6, only used for the time estimate).
set -euo pipefail

cd "$(dirname "$0")/.."
unset VIRTUAL_ENV
OLLAMA_URL=${OLLAMA_URL:-http://127.0.0.1:11434}
MODEL=${MODEL:-qwen2.5:14b-instruct}
MIN_FREE_RAM_GB=${MIN_FREE_RAM_GB:-8}
MIN_FREE_VRAM_GB=${MIN_FREE_VRAM_GB:-10}
SECONDS_PER_CALL=${SECONDS_PER_CALL:-6}

if [[ ! -f data/raw/thinkpython2.pdf ]]; then
  echo "data/raw is empty: run scripts/fetch_data.sh first" >&2
  exit 1
fi

plan=$(uv run book-to-skill model-arm --dry-run --model "$MODEL" --judge-model "$MODEL")
echo "$plan"
calls=$(echo "$plan" | sed -n 's/.*"total_calls": \([0-9]*\).*/\1/p')
echo "estimated time at ${SECONDS_PER_CALL}s/call: $((calls * SECONDS_PER_CALL / 3600))h $((calls * SECONDS_PER_CALL % 3600 / 60))m (cached calls are free)"

if [[ ${1:-} == "--dry-run" ]]; then
  exit 0
fi

# ---- resource checks: refuse to start on a busy machine ----------------------
free_ram_gb() {
  if command -v powershell >/dev/null 2>&1; then
    powershell -NoProfile -Command "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)"
  else
    awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo
  fi
}
ram=$(free_ram_gb | tr -d '\r')
echo "free RAM: ${ram} GB (need ${MIN_FREE_RAM_GB})"
if (( ram < MIN_FREE_RAM_GB )); then
  echo "not enough free RAM; try again when other jobs have finished" >&2
  exit 1
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  vram_mb=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1 | tr -d '\r ')
  echo "free VRAM: $((vram_mb / 1024)) GB (need ${MIN_FREE_VRAM_GB})"
  nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader || true
  if (( vram_mb / 1024 < MIN_FREE_VRAM_GB )); then
    echo "the GPU is busy (listed above); not starting" >&2
    exit 1
  fi
else
  echo "nvidia-smi not found: a 14B model on CPU will be very slow" >&2
fi

if ! curl -sf -m 5 "$OLLAMA_URL/api/tags" >/dev/null; then
  echo "ollama is not answering at $OLLAMA_URL" >&2
  exit 1
fi

uv run book-to-skill model-arm \
  --url "$OLLAMA_URL" --model "$MODEL" --judge-model "$MODEL" \
  --data data --results results --out out/skills --cache data/cache/llm
echo "wrote results/model_arm.json and results/model_outcomes.jsonl"
