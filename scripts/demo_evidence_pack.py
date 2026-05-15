from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


EVIDENCE_PACK_VERSION = "OMEGA_EVIDENCE_PACK_V1"
OUTPUT_DIR = Path("artifacts/evidence_pack")
REPORT_PATH = OUTPUT_DIR / "evidence_pack_report.json"
ZIP_PATH = OUTPUT_DIR / "omega_evidence_pack.zip"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return sha256(path.read_bytes()).hexdigest()


def run_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    return {
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def artifact_record(path: str, artifact_type: str) -> dict[str, Any]:
    p = Path(path)

    return {
        "artifact_type": artifact_type,
        "path": str(p),
        "exists": p.exists(),
        "sha256": file_hash(p),
        "size_bytes": p.stat().st_size if p.exists() and p.is_file() else None,
    }


def create_zip(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)

    added: list[str] = []

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in artifacts:
            path = Path(item["path"])
            if path.exists() and path.is_file():
                archive.write(path, arcname=str(path))
                added.append(str(path))

    return {
        "zip_path": str(ZIP_PATH),
        "zip_exists": ZIP_PATH.exists(),
        "zip_hash": file_hash(ZIP_PATH),
        "files_added": added,
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    setup_runs = []

    proof_script = Path("scripts/demo_proof_bundle.py")
    replay_script = Path("scripts/demo_replay_verifier.py")
    failure_lab_script = Path("scripts/demo_failure_lab.py")

    if proof_script.exists():
        setup_runs.append(run_command([sys.executable, str(proof_script)]))

    if replay_script.exists():
        setup_runs.append(run_command([sys.executable, str(replay_script)]))

    if failure_lab_script.exists():
        setup_runs.append(run_command([sys.executable, str(failure_lab_script)]))

    artifacts = [
        artifact_record("artifacts/proof_bundle_demo.json", "proof_bundle"),
        artifact_record("traces/replay-verifier-demo.jsonl", "replay_trace"),
        artifact_record("artifacts/failure_lab/failure_lab_report.json", "failure_lab_report"),
    ]

    zip_info = create_zip(artifacts)

    existing_count = sum(1 for item in artifacts if item["exists"])

    report = {
        "accepted": existing_count > 0 and zip_info["zip_exists"],
        "reason": "evidence pack generated" if existing_count > 0 else "no evidence artifacts found",
        "evidence_pack_version": EVIDENCE_PACK_VERSION,
        "generated_at": utc_now(),
        "output_dir": str(OUTPUT_DIR),
        "report_path": str(REPORT_PATH),
        "artifact_count": len(artifacts),
        "artifacts_found": existing_count,
        "artifacts": artifacts,
        "archive": zip_info,
        "setup_runs": setup_runs,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))

    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
