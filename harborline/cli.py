"""Command-line entry: ingest, ask, eval."""

from __future__ import annotations

import argparse
import json
import sys

from harborline.answer import ask
from harborline.config import get_settings
from harborline.evaluate import run_eval
from harborline.ingest import write_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harborline policy Q&A")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Build the deterministic chunk index")

    ask_p = sub.add_parser("ask", help="Retrieve (and optionally generate) an answer")
    ask_p.add_argument("query", help="Employee question")
    ask_p.add_argument("--employee-id", dest="employee_id", default=None)
    ask_p.add_argument("--json", action="store_true")

    eval_p = sub.add_parser("eval", help="Run seeded retrieval evaluation")
    eval_p.add_argument("--limit", type=int, default=None, help="Sample N gold items")
    eval_p.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    settings = get_settings()
    settings.apply_seeds()

    if args.command == "ingest":
        path = write_index(settings)
        print(f"Wrote {path} (seed={settings.seed}, size={settings.chunk_size})")
        return 0

    if args.command == "ask":
        result = ask(args.query, employee_id=args.employee_id, settings=settings)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result["answer"])
            print("\nSources:")
            for src in result["sources"]:
                print(f"  - {src['source_path']} ({src['kind']}, {src['score']})")
        return 0

    report = run_eval(settings=settings, limit=args.limit)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"seed={report['seed']}  n={report['n']}  "
            f"passed={report['passed']}  recall@{report['top_k']}={report['recall_at_k']}"
        )
        for row in report["results"]:
            mark = "PASS" if row["pass"] else "FAIL"
            print(f"  [{mark}] {row['id']}: {row['question']}")
    return 0 if report["passed"] == report["n"] else 1


if __name__ == "__main__":
    sys.exit(main())
