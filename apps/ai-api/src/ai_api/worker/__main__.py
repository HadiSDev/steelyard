"""`python -m ai_api.worker [--once]`."""
from __future__ import annotations

import argparse
import logging

from .. import config
from .loop import run_worker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute requested pipeline runs one at a time and, when none "
                    "is waiting, read pending documents.",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run a single pass and exit instead of polling forever",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    outcome = run_worker(
        poll_seconds=config.WORKER_POLL_SECONDS,
        document_batch=config.WORKER_DOCUMENT_BATCH,
        once=args.once,
    )
    if args.once:
        print(f"worker pass: {outcome.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
