"""Verify an OpenAI-compatible chat endpoint (e.g. RunPod vLLM, Ollama).

Usage:
    python scripts/verify_llm.py --base-url http://localhost:11434/v1 --llm-model llama3.1:8b
    python scripts/verify_llm.py --base-url https://api.runpod.ai/v2/ID/openai/v1 --llm-model NousResearch/Meta-Llama-3.1-8B-Instruct
"""
import argparse

from openai import OpenAI


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--llm-model", required=True)
    parser.add_argument("--api-key", default="dummy")
    args = parser.parse_args()

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    resp = client.chat.completions.create(
        model=args.llm_model,
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        max_tokens=10,
    )
    print("chat OK:", repr(resp.choices[0].message.content))


if __name__ == "__main__":
    main()
