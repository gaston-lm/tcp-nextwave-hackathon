#!/usr/bin/env python3
"""Trigger one investigation for the latest completed simulated time window."""

from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urlopen(request, timeout=180) as response:  # noqa: S310 - localhost URLs are arguments.
        return json.loads(response.read())


def run_once(args: argparse.Namespace) -> int:
    args.lock_file.parent.mkdir(parents=True, exist_ok=True)
    with args.lock_file.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Skipped: the previous investigation is still running.")
            return 0

        try:
            stream = request_json(f"{args.generator_url.rstrip('/')}/api/live/status")
            if not stream.get("running"):
                print("Skipped: live ingestion is not running.")
                return 0
            simulated_timestamp = stream.get("simulated_timestamp")
            if not simulated_timestamp:
                print("Skipped: Generator has not produced a simulated timestamp.")
                return 0

            result = request_json(
                f"{args.agent_url.rstrip('/')}/investigations",
                {"as_of": simulated_timestamp},
            )
        except HTTPError as error:
            print(f"Investigation failed: agent returned HTTP {error.code}.")
            return 1
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            print(f"Investigation failed: {error}.")
            return 1

    persistence = result.get("persistence", {})
    print(
        "Investigation completed for "
        f"{simulated_timestamp}: created={persistence.get('created_incident_ids', [])}, "
        f"updated={persistence.get('updated_incident_ids', [])}."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an agent investigation for the Generator's current simulated time."
    )
    parser.add_argument("--agent-url", default="http://127.0.0.1:8001")
    parser.add_argument("--generator-url", default="http://127.0.0.1:8002")
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=Path("/tmp/control-tower-agent-scheduler.lock"),
    )
    args = parser.parse_args()
    return run_once(args)


if __name__ == "__main__":
    raise SystemExit(main())
