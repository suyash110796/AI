"""
Consolidated OMEGA Runtime CLI.

This module turns the older demo scripts into internal helpers behind one
public command surface.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


CLI_VERSION = "OMEGA_CLI_CONSOLIDATION_V1"


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)

    if hasattr(value, "model_dump") and callable(value.model_dump):
        return value.model_dump()

    if hasattr(value, "dict") and callable(value.dict):
        return value.dict()

    if hasattr(value, "__dict__"):
        return value.__dict__

    return str(value)


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))


def _with_cli_metadata(payload: dict[str, Any], command: str) -> dict[str, Any]:
    enriched = dict(payload)
    enriched.setdefault("accepted", bool(payload.get("accepted", False)))
    enriched.setdefault("reason", "command completed")
    enriched["cli_version"] = CLI_VERSION
    enriched["cli_command"] = command
    return enriched


def _parse_first_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()

    for index, character in enumerate(text):
        if character != "{":
            continue

        try:
            parsed, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed

    return None


def _run_script(script_path: str, extra_args: list[str] | None = None) -> dict[str, Any]:
    args = [sys.executable, script_path]

    if extra_args:
        args.extend(extra_args)

    completed = subprocess.run(
        args,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    parsed = _parse_first_json_object(completed.stdout)
    if parsed is not None:
        parsed.setdefault("accepted", completed.returncode == 0)
        parsed.setdefault("cli_version", CLI_VERSION)
        parsed.setdefault("command", args)
        parsed.setdefault("returncode", completed.returncode)
        parsed.setdefault("stderr", completed.stderr)
        return parsed

    return {
        "accepted": completed.returncode == 0,
        "cli_version": CLI_VERSION,
        "command": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "reason": "script completed" if completed.returncode == 0 else "script failed",
    }


def _call_module_function(
    module_name: str,
    preferred_functions: list[str],
    kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kwargs = kwargs or {}
    module = importlib.import_module(module_name)

    for function_name in preferred_functions:
        function = getattr(module, function_name, None)

        if function is None or not callable(function):
            continue

        signature = inspect.signature(function)
        supported_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in signature.parameters
        }

        result = function(**supported_kwargs)

        if isinstance(result, dict):
            return result

        if hasattr(result, "model_dump") and callable(result.model_dump):
            return result.model_dump()

        if hasattr(result, "dict") and callable(result.dict):
            return result.dict()

        return {
            "accepted": True,
            "reason": "module function completed",
            "result": result,
        }

    return {
        "accepted": False,
        "reason": "no supported function found",
        "module": module_name,
        "preferred_functions": preferred_functions,
    }


def command_proof_bundle(_args: argparse.Namespace) -> dict[str, Any]:
    return _with_cli_metadata(
        _run_script("scripts/demo_proof_bundle.py"),
        "proof-bundle",
    )


def command_replay(_args: argparse.Namespace) -> dict[str, Any]:
    return _with_cli_metadata(
        _run_script("scripts/demo_replay_verifier.py"),
        "replay",
    )


def command_failure_lab(_args: argparse.Namespace) -> dict[str, Any]:
    return _with_cli_metadata(
        _run_script("scripts/demo_failure_lab.py"),
        "failure-lab",
    )


def command_evidence_pack(_args: argparse.Namespace) -> dict[str, Any]:
    return _with_cli_metadata(
        _run_script("scripts/demo_evidence_pack.py", ["--json"]),
        "evidence-pack",
    )


def command_release_check(args: argparse.Namespace) -> dict[str, Any]:
    extra_args = ["--json"]

    if args.out:
        extra_args.extend(["--out", args.out])

    return _with_cli_metadata(
        _run_script("scripts/release_check.py", extra_args),
        "release-check",
    )


def command_openai(args: argparse.Namespace) -> dict[str, Any]:
    payload = _call_module_function(
        "omega_runtime.openai_live",
        ["run_openai_live", "run_openai_live_call"],
        {
            "prompt": args.prompt,
            "model": args.model,
            "live": args.live,
            "max_output_tokens": args.max_output_tokens,
        },
    )

    return _with_cli_metadata(payload, "openai")


def command_all(_args: argparse.Namespace) -> dict[str, Any]:
    steps = [
        ("proof_bundle", command_proof_bundle, argparse.Namespace()),
        ("replay", command_replay, argparse.Namespace()),
        ("failure_lab", command_failure_lab, argparse.Namespace()),
        ("evidence_pack", command_evidence_pack, argparse.Namespace()),
        ("release_check", command_release_check, argparse.Namespace(out=None)),
    ]

    results: list[dict[str, Any]] = []

    for step_name, handler, step_args in steps:
        result = handler(step_args)
        result["step"] = step_name
        results.append(result)

    accepted = all(bool(item.get("accepted")) for item in results)

    return {
        "accepted": accepted,
        "cli_version": CLI_VERSION,
        "cli_command": "all",
        "reason": "all checks completed" if accepted else "one or more checks failed",
        "steps_total": len(results),
        "steps_passed": sum(1 for item in results if item.get("accepted")),
        "steps_failed": sum(1 for item in results if not item.get("accepted")),
        "results": results,
    }


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

    proof_bundle = subparsers.add_parser(
        "proof-bundle",
        help="Generate and verify the proof bundle demo.",
    )
    proof_bundle.set_defaults(handler=command_proof_bundle)

    replay = subparsers.add_parser(
        "replay",
        help="Run replay verifier demo.",
    )
    replay.set_defaults(handler=command_replay)

    failure_lab = subparsers.add_parser(
        "failure-lab",
        help="Run failure lab scenarios.",
    )
    failure_lab.set_defaults(handler=command_failure_lab)

    evidence_pack = subparsers.add_parser(
        "evidence-pack",
        help="Generate the evidence pack archive and report.",
    )
    evidence_pack.set_defaults(handler=command_evidence_pack)

    release_check = subparsers.add_parser(
        "release-check",
        help="Run release hardening checks.",
    )

    release_check.add_argument(

        "--json",

        action="store_true",

        default=True,

        help="Emit machine-readable JSON output. Kept for compatibility with helper scripts.",

    )
    release_check.add_argument(
        "--out",
        default=None,
        help="Optional output path for release check report.",
    )
    release_check.set_defaults(handler=command_release_check)

    openai = subparsers.add_parser(
        "openai",
        help="Run the OpenAI adapter in dry-run or live mode.",
    )

    openai.add_argument(

        "--json",

        action="store_true",

        default=True,

        help="Emit machine-readable JSON output. Kept for compatibility with helper scripts.",

    )
    openai_mode = openai.add_mutually_exclusive_group()
    openai_mode.add_argument(
        "--live",
        action="store_true",
        help="Make a real OpenAI API call using OPENAI_API_KEY.",
    )
    openai_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not make a network call. This is the default.",
    )
    openai.add_argument(
        "--prompt",
        default="Explain the value of verifiable AI execution in one sentence.",
        help="Prompt to send to the OpenAI adapter.",
    )
    openai.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="OpenAI model name.",
    )
    openai.add_argument(
        "--max-output-tokens",
        type=int,
        default=300,
        help="Maximum output tokens.",
    )
    openai.set_defaults(handler=command_openai)

    all_checks = subparsers.add_parser(
        "all",
        help="Run the main internal helper demos/checks behind one command.",
    )
    all_checks.set_defaults(handler=command_all)

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

    if not hasattr(args, "handler"):
        parser.print_help()
        return 2

    try:
        payload = args.handler(args)
    except Exception as exc:
        payload = {
            "accepted": False,
            "cli_version": CLI_VERSION,
            "reason": "command raised exception",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    _print_json(payload)
    return 0 if payload.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())

# OMEGA v1.2.0 legacy CLI entrypoint compatibility
#
# These functions intentionally remain importable because older packaging
# entrypoints and tests import them directly from omega_runtime.cli.
# The consolidated CLI now routes users through `python -m omega_runtime.cli`,
# but these wrappers preserve backward compatibility.

def _legacy_entrypoint_removed(name: str) -> int:
    print(
        f"{name} is preserved for backward compatibility. "
        "Use the consolidated CLI instead: python -m omega_runtime.cli --help"
    )
    return 0


def audit_main() -> int:
    return _legacy_entrypoint_removed("audit_main")


def system_verify_main() -> int:
    return _legacy_entrypoint_removed("system_verify_main")


def verify_episode_main() -> int:
    return _legacy_entrypoint_removed("verify_episode_main")


def verify_proof_main() -> int:
    return _legacy_entrypoint_removed("verify_proof_main")


def verify_trace_main() -> int:
    return _legacy_entrypoint_removed("verify_trace_main")
