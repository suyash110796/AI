from __future__ import annotations

import argparse
import importlib
import inspect
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

CLI_VERSION = "OMEGA_CLI_CONSOLIDATION_V1"

DEFAULT_OPENAI_PROMPT = (
    "Explain the value of verifiable AI execution in one sentence "
    "for a non-technical executive."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    return str(value)


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))


def _parse_first_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()

    for index, char in enumerate(text):
        if char != "{":
            continue

        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict):
            return value

    return None


def _normalize_payload(value: Any, *, fallback_reason: str) -> dict[str, Any]:
    if isinstance(value, dict):
        payload = dict(value)
    elif hasattr(value, "model_dump"):
        payload = dict(value.model_dump())
    elif hasattr(value, "dict"):
        payload = dict(value.dict())
    else:
        payload = {
            "accepted": False,
            "reason": fallback_reason,
            "raw": str(value),
        }

    payload.setdefault("accepted", bool(payload.get("passed", False)))
    payload.setdefault("reason", fallback_reason)
    payload.setdefault("cli_version", CLI_VERSION)
    return payload


def _run_script(
    script_path: str,
    *,
    script_args: Iterable[str] = (),
    cli_command: str,
    parse_json: bool = True,
) -> dict[str, Any]:
    script = Path(script_path)

    if not script.exists():
        return {
            "accepted": False,
            "cli_version": CLI_VERSION,
            "cli_command": cli_command,
            "reason": f"script not found: {script_path}",
            "script": script_path,
        }

    command = [sys.executable, str(script), *list(script_args)]

    completed = subprocess.run(
        command,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    parsed = _parse_first_json_object(completed.stdout) if parse_json else None

    if parsed is not None:
        payload = _normalize_payload(
            parsed,
            fallback_reason="script produced JSON payload",
        )
    else:
        payload = {
            "accepted": completed.returncode == 0,
            "reason": (
                "script completed"
                if completed.returncode == 0
                else "script failed"
            ),
            "stdout": completed.stdout,
        }

    payload["cli_version"] = CLI_VERSION
    payload["cli_command"] = cli_command
    payload["command"] = command
    payload["returncode"] = completed.returncode
    payload["stderr"] = completed.stderr

    if completed.returncode != 0:
        payload["accepted"] = False

    return payload


def _proof_bundle_payload(_args: argparse.Namespace) -> dict[str, Any]:
    return _run_script(
        "scripts/demo_proof_bundle.py",
        cli_command="proof-bundle",
        parse_json=True,
    )


def _replay_payload(_args: argparse.Namespace) -> dict[str, Any]:
    return _run_script(
        "scripts/demo_replay_verifier.py",
        cli_command="replay",
        parse_json=True,
    )


def _failure_lab_payload(_args: argparse.Namespace) -> dict[str, Any]:
    return _run_script(
        "scripts/demo_failure_lab.py",
        cli_command="failure-lab",
        parse_json=True,
    )


def _evidence_pack_payload(args: argparse.Namespace) -> dict[str, Any]:
    script_args: list[str] = ["--json"]

    output_dir = getattr(args, "output_dir", None)
    if output_dir:
        script_args.extend(["--output-dir", str(output_dir)])

    return _run_script(
        "scripts/demo_evidence_pack.py",
        script_args=script_args,
        cli_command="evidence-pack",
        parse_json=True,
    )


def _release_check_payload(args: argparse.Namespace) -> dict[str, Any]:
    script_args: list[str] = ["--json"]

    out = getattr(args, "out", None)
    if out:
        script_args.extend(["--out", str(out)])

    return _run_script(
        "scripts/release_check.py",
        script_args=script_args,
        cli_command="release-check",
        parse_json=True,
    )


def _build_openai_request(openai_live: Any, args: argparse.Namespace) -> Any:
    request_class = (
        getattr(openai_live, "OpenAILiveRequest", None)
        or getattr(openai_live, "OpenAIRequest", None)
        or getattr(openai_live, "OpenAILiveCallRequest", None)
    )

    live = bool(getattr(args, "live", False))
    if bool(getattr(args, "dry_run", False)):
        live = False

    base_values: dict[str, Any] = {
        "prompt": args.prompt,
        "user_prompt": args.prompt,
        "input_text": args.prompt,
        "live": live,
        "model": args.model,
        "max_output_tokens": args.max_output_tokens,
        "system_prompt": (
            "You are a concise assistant. Answer clearly and directly."
        ),
    }

    if request_class is None:
        return base_values

    signature = inspect.signature(request_class)
    kwargs: dict[str, Any] = {}

    for name, parameter in signature.parameters.items():
        if name in base_values:
            kwargs[name] = base_values[name]
        elif parameter.default is inspect.Parameter.empty:
            if name.endswith("prompt"):
                kwargs[name] = args.prompt
            elif name == "request_id":
                kwargs[name] = f"omega-cli-{_utc_now()}"
            else:
                raise TypeError(
                    f"Cannot build {request_class.__name__}: "
                    f"missing required field {name!r}"
                )

    return request_class(**kwargs)


def _with_cli_metadata(payload: dict[str, Any], command_name: str) -> dict[str, Any]:
    """Attach standard consolidated CLI metadata to a command payload."""
    enriched = dict(payload)
    enriched["cli_command"] = command_name
    enriched["cli_version"] = globals().get("CLI_VERSION", "OMEGA_CLI_CONSOLIDATION_V1")
    return enriched


def _openai_payload(args: argparse.Namespace) -> dict[str, Any]:
    from omega_runtime.openai_live import OpenAILiveRequest, run_openai_live

    request = OpenAILiveRequest(
        prompt=args.prompt,
        model=args.model,
        live=bool(args.live),
        max_output_tokens=args.max_output_tokens,
    )

    payload = _with_cli_metadata(run_openai_live(request), "openai")

    # Every OpenAI CLI run is recorded into the run ledger.
    # This includes both dry-run and live API calls.
    try:
        from omega_runtime.run_ledger import write_run_record

        record_result = write_run_record(payload, source="cli.openai")

        payload["ledger_recorded"] = bool(record_result.get("accepted"))
        payload["ledger_record"] = {
            "accepted": record_result.get("accepted"),
            "reason": record_result.get("reason"),
            "record_id": record_result.get("record_id"),
            "record_path": record_result.get("record_path"),
            "ledger_path": record_result.get("ledger_path"),
            "record_file_sha256": record_result.get("record_file_sha256"),
        }
    except Exception as exc:
        payload["ledger_recorded"] = False
        payload["ledger_record_error_type"] = type(exc).__name__
        payload["ledger_record_error"] = str(exc)

    return payload

def _all_payload(args: argparse.Namespace) -> dict[str, Any]:
    commands: list[tuple[str, Any, argparse.Namespace]] = [
        ("proof-bundle", _proof_bundle_payload, argparse.Namespace()),
        ("replay", _replay_payload, argparse.Namespace()),
        ("failure-lab", _failure_lab_payload, argparse.Namespace()),
        (
            "evidence-pack",
            _evidence_pack_payload,
            argparse.Namespace(output_dir=None),
        ),
        ("release-check", _release_check_payload, argparse.Namespace(out=None)),
        (
            "openai",
            _openai_payload,
            argparse.Namespace(
                live=False,
                dry_run=True,
                prompt=DEFAULT_OPENAI_PROMPT,
                model=getattr(args, "model", "gpt-4.1-mini"),
                max_output_tokens=getattr(args, "max_output_tokens", 300),
            ),
        ),
    ]

    results: dict[str, Any] = {}

    for name, handler, command_args in commands:
        results[name] = handler(command_args)

    accepted = all(bool(value.get("accepted")) for value in results.values())

    return {
        "accepted": accepted,
        "cli_version": CLI_VERSION,
        "cli_command": "all",
        "reason": (
            "all consolidated commands passed"
            if accepted
            else "one or more consolidated commands failed"
        ),
        "generated_at": _utc_now(),
        "results": results,
    }


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Emit machine-readable JSON output. "
            "Kept for compatibility with helper scripts."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omega",
        description="Consolidated CLI for OMEGA Runtime.",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Print OMEGA consolidated CLI version.",
    )

    subparsers = parser.add_subparsers(dest="command")

    proof = subparsers.add_parser(
        "proof-bundle",
        help="Generate and verify the proof bundle demo.",
    )
    _add_json_flag(proof)
    proof.set_defaults(handler=_proof_bundle_payload)

    replay = subparsers.add_parser(
        "replay",
        help="Run replay verifier demo.",
    )
    _add_json_flag(replay)
    replay.set_defaults(handler=_replay_payload)

    failure = subparsers.add_parser(
        "failure-lab",
        help="Run failure lab scenarios.",
    )
    _add_json_flag(failure)
    failure.set_defaults(handler=_failure_lab_payload)

    evidence = subparsers.add_parser(
        "evidence-pack",
        help="Generate the evidence pack archive and report.",
    )
    _add_json_flag(evidence)
    evidence.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory for evidence pack artifacts.",
    )
    evidence.set_defaults(handler=_evidence_pack_payload)

    release = subparsers.add_parser(
        "release-check",
        help="Run release hardening checks.",
    )
    _add_json_flag(release)
    release.add_argument(
        "--out",
        default=None,
        help="Optional output path for release check report.",
    )
    release.set_defaults(handler=_release_check_payload)

    openai_parser = subparsers.add_parser(
        "openai",
        help="Run the OpenAI adapter in dry-run or live mode.",
    )
    _add_json_flag(openai_parser)

    mode = openai_parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--live",
        action="store_true",
        help="Make a real OpenAI API call using OPENAI_API_KEY.",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not make a network call. This is the default.",
    )

    openai_parser.add_argument(
        "--prompt",
        default=DEFAULT_OPENAI_PROMPT,
        help="Prompt to send to the OpenAI adapter.",
    )
    openai_parser.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="OpenAI model name.",
    )
    openai_parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=300,
        help="Maximum output tokens.",
    )
    openai_parser.set_defaults(handler=_openai_payload)

    all_parser = subparsers.add_parser(
        "all",
        help="Run the main internal helper demos/checks behind one command.",
    )
    _add_json_flag(all_parser)
    all_parser.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="OpenAI model used for the dry-run OpenAI adapter check.",
    )
    all_parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=300,
        help="Maximum output tokens for the OpenAI adapter check.",
    )
    all_parser.set_defaults(handler=_all_payload)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        _print_json(
            {
                "accepted": True,
                "cli_version": CLI_VERSION,
                "reason": "version printed",
            }
        )
        return 0

    handler = getattr(args, "handler", None)

    if handler is None:
        parser.print_help()
        return 0

    payload = handler(args)
    _print_json(payload)

    return 0 if bool(payload.get("accepted")) else 1


def verify_proof_main(argv: list[str] | None = None) -> int:
    return main(["proof-bundle", *(argv or [])])


def verify_trace_main(argv: list[str] | None = None) -> int:
    return main(["replay", *(argv or [])])


def system_verify_main(argv: list[str] | None = None) -> int:
    return main(["failure-lab", *(argv or [])])


def verify_episode_main(argv: list[str] | None = None) -> int:
    return main(["evidence-pack", *(argv or [])])


def audit_main(argv: list[str] | None = None) -> int:
    return main(["release-check", *(argv or [])])


__all__ = [
    "CLI_VERSION",
    "build_parser",
    "main",
    "audit_main",
    "system_verify_main",
    "verify_episode_main",
    "verify_proof_main",
    "verify_trace_main",
]


if __name__ == "__main__":
    raise SystemExit(main())
