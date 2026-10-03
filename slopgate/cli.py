import argparse
import json
import sys

from slopgate.review import review
from slopgate.sandbox import Contree, Local


def main(argv=None):
    parser = argparse.ArgumentParser(prog="slopgate")
    commands = parser.add_subparsers(dest="command", required=True)
    review_args = commands.add_parser("review")
    review_args.add_argument("--repo", default=".")
    review_args.add_argument("--base", required=True)
    review_args.add_argument("--head", required=True)
    review_args.add_argument("--dry-run", action="store_true")
    review_args.add_argument("--sandbox", choices=["local", "contree"], default="contree")
    args = parser.parse_args(argv)

    result = {"suggestions": [], "followup": [], "rejected": []}
    try:
        result = review(args.repo, args.base, args.head, {"local": Local, "contree": Contree}[args.sandbox]())
    except Exception as error:
        print(f"slopgate: {error!r}", file=sys.stderr)
    print(json.dumps(result, indent=2))
