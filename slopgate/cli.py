import argparse
import json
import sys

from slopgate.review import review


def main(argv=None):
    parser = argparse.ArgumentParser(prog="slopgate")
    commands = parser.add_subparsers(dest="command", required=True)
    review_args = commands.add_parser("review")
    review_args.add_argument("--repo", default=".")
    review_args.add_argument("--base", required=True)
    review_args.add_argument("--head", required=True)
    review_args.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    result = {"suggestions": [], "followup": [], "rejected": []}
    try:
        result = review(args.repo, args.base, args.head)
    except Exception as error:
        print(f"slopgate: {error!r}", file=sys.stderr)
    print(json.dumps(result, indent=2))
