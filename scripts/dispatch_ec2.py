"""Dispatch the fixed SSM deployment document and wait for its actual result."""

import json
import os
import re
import subprocess
import sys
import time


def aws(args):
    result = subprocess.run(
        ["aws", *args, "--output", "json", "--no-cli-pager"],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode:
        # Eventual consistency can briefly hide a newly dispatched invocation.
        if "InvocationDoesNotExist" in result.stderr:
            return None
        raise RuntimeError("AWS_API_REQUEST_FAILED")
    return json.loads(result.stdout)


def main():
    image = os.environ.get("PRISM_IMAGE", "")
    revision = os.environ.get("GITHUB_SHA", "")
    sequence = os.environ.get("GITHUB_RUN_NUMBER", "")
    instance = os.environ.get("PRISM_EC2_INSTANCE_ID", "")
    document = os.environ.get("PRISM_SSM_DOCUMENT", "")
    expected = {
        "image": bool(
            re.fullmatch(
                r"ghcr\.io/oso7865-ship-it/prism-backend-production@sha256:[0-9a-f]{64}", image
            )
        ),
        "revision": bool(re.fullmatch(r"[0-9a-f]{40}", revision)),
        "sequence": bool(re.fullmatch(r"[1-9][0-9]{0,14}", sequence)),
        "instance": bool(re.fullmatch(r"i-[0-9a-f]{17}", instance)),
        "document": document == "PrismDeployBackend",
        "branch": os.environ.get("GITHUB_REF") == "refs/heads/main",
        "event": os.environ.get("GITHUB_EVENT_NAME") in {"push", "workflow_dispatch"},
    }
    if not all(expected.values()):
        print(json.dumps({"status": "FAIL", "checks": expected}))
        return 1
    response = aws(
        [
            "ssm",
            "send-command",
            "--instance-ids",
            instance,
            "--document-name",
            document,
            "--document-version",
            "1",
            "--timeout-seconds",
            "120",
            "--parameters",
            json.dumps({"Image": [image], "Revision": [revision], "Sequence": [sequence]}),
            "--comment",
            f"PRism main {revision}",
        ]
    )
    command_id = response["Command"]["CommandId"]
    print(json.dumps({"command_id": command_id, "status": "DISPATCHED"}), flush=True)
    deadline = time.monotonic() + 1320
    while time.monotonic() < deadline:
        invocation = aws(
            ["ssm", "get-command-invocation", "--command-id", command_id, "--instance-id", instance]
        )
        status = invocation["Status"] if invocation else "Pending"
        if status == "Success":
            print(json.dumps({"command_id": command_id, "status": "SUCCESS"}))
            return 0
        if status not in {"Pending", "InProgress", "Delayed"}:
            print(json.dumps({"command_id": command_id, "status": status}))
            return 1
        time.sleep(5)
    print(json.dumps({"command_id": command_id, "status": "RESULT_TIMEOUT_CHECK_SSM"}))
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired):
        print(json.dumps({"status": "FAIL", "reason": "SSM_DISPATCH_OR_POLL_FAILED"}))
        sys.exit(1)
