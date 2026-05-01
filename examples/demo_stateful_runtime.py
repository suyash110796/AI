
from pathlib import Path

from omega_runtime.core.certificates import issue_certificate_for_action
from omega_runtime.core.stateful_proxy import StatefulOmegaProxy
from omega_runtime.core.types import Action


def main():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello from stateful runtime", encoding="utf-8")

    proxy = StatefulOmegaProxy(run_id="run-stateful-001")

    print("STATEFUL RUNTIME DEMO")
    print("---------------------")

    for label, decision in [
        ("START", proxy.start()),
        ("PLAN", proxy.plan()),
        ("REQUEST_TOOL", proxy.request_tool()),
    ]:
        print(f"{label}: {'PASS' if decision.passed else 'FAIL'} — {decision.reason}")

    action = Action(
        run_id="run-stateful-001",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="run-stateful-001-nonce-1",
    )

    cert = issue_certificate_for_action(action)
    result = proxy.execute_tool(action, cert)

    print(f"EXECUTE_TOOL: {'ACCEPT' if result.accepted else 'REJECT'} — {result.reason}")
    print(f"TOOL EXECUTED: {result.tool_executed}")
    print(f"FINAL STATE: {proxy.context.state.value}")

    print("\nTRANSITION CERTIFICATES:")
    for cert in proxy.context.transition_certificates:
        print(
            f"{cert.step_index}. {cert.from_state} --{cert.phase}--> "
            f"{cert.to_state} [{cert.rule_id}]"
        )


if __name__ == "__main__":
    main()
