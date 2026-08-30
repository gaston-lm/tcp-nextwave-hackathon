#!/usr/bin/env python3
"""Reject commit messages that do not follow Conventional Commits."""

from __future__ import annotations

import re
import sys
from pathlib import Path

COMMIT_MESSAGE = re.compile(
    r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)"
    r"(?:\([a-z0-9][a-z0-9._/-]*\))?"
    r"!?\: .+$"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("Expected the path to Git's commit-message file.", file=sys.stderr)
        return 2

    subject = next(
        (
            line.strip()
            for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ),
        "",
    )
    if COMMIT_MESSAGE.fullmatch(subject):
        return 0

    print(
        "Commit message must follow Conventional Commits, for example: "
        "feat(agent): add anomaly clustering or fix: handle empty baseline.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
