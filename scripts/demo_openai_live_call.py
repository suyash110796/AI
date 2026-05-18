from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    if is_dataclass(value):
        return asdict(value)

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped

    if hasattr(value, "__dict__"):
        return dict(value.__dict__)

    return {
        "accepted": False,
        "reason": f"unsupported report type: {type(value).__name__}",
        "raw": str(value),
    }


def _write_report(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the OMEGA OpenAI live-call adapter in dry-run or live mode."
    )

    parser.add_argument(
        "--prompt",
        default="Explain the value of verifiable AI execution in one sentence for a non-technical executive.",
        help="Prompt to send through the adapter.",
    )

    parser.add_argument(
        "--model",
        default=None,
        help="OpenAI model name. If omitted, the adapter default is used.",
    )

    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=300,
        help="Maximum output tokens for live calls.",
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Make a real OpenAI API call. Without this flag, the script performs a dry run.",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full machine-readable JSON report.",
    )

    parser.add_argument(
        "--out",
        default="artifacts/openai_live/openai_live_report.json",
        help="Where to write the JSON report.",
    )

    return parser


def main() -> int:
    from omega_runtime import openai_live

    parser = _build_parser()
    args = parser.parse_args()

    request_cls = getattr(openai_live, "OpenAILiveRequest", None)
    if request_cls is None:
        raise AttributeError("omega_runtime.openai_live is missing OpenAILiveRequest")

    runner = (
        getattr(openai_live, "run_openai_live_call", None)
        or getattr(openai_live, "run_openai_live", None)
    )
    if runner is None:
        raise AttributeError(
            "omega_runtime.openai_live is missing run_openai_live_call or run_openai_live"
        )

    request_kwargs: dict[str, Any] = {
        "prompt": args.prompt,
        "live": args.live,
        "max_output_tokens": args.max_output_tokens,
        "output_dir": Path(args.out).parent,
    }

    if args.model:
        request_kwargs["model"] = args.model

    request = request_cls(**request_kwargs)
    report = _to_dict(runner(request))

    out_path = Path(args.out)
    _write_report(report, out_path)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        print(f"accepted: {report.get('accepted')}")
        print(f"live: {report.get('live')}")
        print(f"model: {report.get('model')}")
        print(f"reason: {report.get('reason')}")
        print(f"report_path: {out_path}")

        response_text = report.get("response_text") or report.get("output_text")
        if response_text:
            print(f"response_text: {response_text}")

    return 0 if report.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())


