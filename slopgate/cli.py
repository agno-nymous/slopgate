import argparse
import json
import os
import sys
import time


def main(argv=None):
    parser = argparse.ArgumentParser(prog="slopgate")
    commands = parser.add_subparsers(dest="command", required=True)
    review_args = commands.add_parser("review")
    review_args.add_argument("--repo", default=".")
    review_args.add_argument("--base", required=True)
    review_args.add_argument("--head", required=True)
    review_args.add_argument("--dry-run", action="store_true")
    review_args.add_argument("--sandbox", choices=["local", "contree"], default="contree")
    index_args = commands.add_parser("index")
    index_args.add_argument("--repo", default=".")
    index_args.add_argument("--ref", required=True)
    commands.add_parser("hook")
    args = parser.parse_args(argv)

    if args.command == "hook":
        try:
            from slopgate import live

            if out := live.hook(sys.stdin.read()):
                print(out)
        except Exception as error:
            print(f"slopgate: {error!r}", file=sys.stderr)
        return

    if args.command == "index":
        from slopgate import embed, index, live

        ready = embed.compile_model()
        path = index.location(args.repo, args.ref)
        records = index.build(args.repo, args.ref)
        if ready:
            live.seed(args.repo, records)
        print(json.dumps({"ref": path.stem, "functions": len(records), "path": str(path)}))
        return

    from slopgate import github
    from slopgate.review import review
    from slopgate.sandbox import Contree, Local

    result = {"suggestions": [], "followup": [], "rejected": []}
    started = time.monotonic()
    try:
        result = review(args.repo, args.base, args.head, {"local": Local, "contree": Contree}[args.sandbox]())
        if not args.dry_run:
            with open(os.environ["GITHUB_EVENT_PATH"]) as event:
                github.publish(args.repo, result, json.load(event), time.monotonic() - started)
    except Exception as error:
        print(f"slopgate: {error!r}", file=sys.stderr)
    print(json.dumps(result, indent=2))
