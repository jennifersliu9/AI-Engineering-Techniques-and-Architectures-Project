"""Command-line entry: ingest, ask, eval."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from harborline.answer import ask
from harborline.config import get_settings
from harborline.evaluate import run_eval
from harborline.ingest import load_chunks, write_index
from harborline.store import persist_chunks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harborline policy Q&A")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "ingest",
        help="Parse corpus, chunk, embed with local MiniLM, and store in FAISS",
    )

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
        chunks = load_chunks(settings)
        json_path = write_index(settings)
        stored = persist_chunks(chunks, settings)
        formats = Counter(c.source_format for c in chunks)
        print(f"Parsed and chunked {len(chunks)} records")
        print("  formats:", dict(formats))
        print(f"  json index: {json_path}")
        print(f"  vector index: {settings.vector_dir} ({stored} embedded chunks)")
        print(f"  embedding: local FastEmbed {settings.embedding_model} (no API key)")
        return 0

    if args.command == "ask":
        result = ask(args.query, employee_id=args.employee_id, settings=settings)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result["answer"])
            print("\nCitations:")
            for src in result["sources"]:
                print(
                    f"  - {src['title']} | {src['section']}\n"
                    f"    {src['source_path']} ({src['kind']}, score={src['score']})\n"
                    f"    {src['snippet']}"
                )
        return 0

    report = run_eval(settings=settings, limit=args.limit)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"backend={settings.retrieve_backend}  seed={report['seed']}  n={report['n']}  "
            f"passed={report['passed']}  recall@{report['top_k']}={report['recall_at_k']}"
        )
        for row in report["results"]:
            mark = "PASS" if row["pass"] else "FAIL"
            print(f"  [{mark}] {row['id']}: {row['question']}")
    return 0 if report["passed"] == report["n"] else 1


if __name__ == "__main__":
    sys.exit(main())
