from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from omega_runtime.run_ledger import (
    OpenAICliRunRequest,
    compare_last_two,
    list_run_records,
    run_openai_cli_and_record,
)


DEFAULT_PROMPT = "Explain the value of verifiable AI execution in one sentence for a non-technical executive."


def print_json(value: dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the OMEGA OpenAI adapter and store each run as a unique ledger record."
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Make a real OpenAI API call.")
    mode.add_argument("--dry-run", action="store_true", help="Do not make a network call. This is the default.")

    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt to send to the OpenAI adapter.")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model name.")
    parser.add_argument("--max-output-tokens", type=int, default=300, help="Maximum output tokens.")
    parser.add_argument("--compare-last-two", action="store_true", help="Also compare the last two run records.")
    parser.add_argument("--list", action="store_true", help="List existing run records instead of creating a new one.")
    parser.add_argument("--limit", type=int, default=10, help="Record list limit.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        result = {
            "accepted": True,
            "reason": "run ledger listed",
            "records": list_run_records(limit=args.limit),
        }
        print_json(result)
        return 0

    request = OpenAICliRunRequest(
        live=bool(args.live),
        prompt=args.prompt,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
        root=Path("."),
    )

    result = run_openai_cli_and_record(request)

    if args.compare_last_two:
        result["comparison"] = compare_last_two(root=Path("."))

    print_json(result)

    return 0 if result.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
