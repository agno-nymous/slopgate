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
    review_args.add_argument("--base")
    review_args.add_argument("--head")
    review_args.add_argument("--pr", type=int)
    review_args.add_argument("--dry-run", action="store_true")
    review_args.add_argument("--sandbox", choices=["local", "contree"], default="contree")
    index_args = commands.add_parser("index")
    index_args.add_argument("--repo", default=".")
    index_args.add_argument("--ref", required=True)
    commands.add_parser("hook")
    args = parser.parse_args(argv)
    if args.command == "review" and not args.pr and not (args.base and args.head):
        review_args.error("give --pr, or both --base and --head")

    if args.command == "hook":
        try:
            from slopgate import live, trace

            trace.start("slopgate-hook")
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

    from slopgate import diff, github, trace
    from slopgate.review import review
    from slopgate.sandbox import Contree, Local

    trace.start("slopgate-gate")
    result = {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    started = time.monotonic()
    try:
        if args.pr:
            event = github.pull_request(args.repo, args.pr)
            base, head = event["pull_request"]["base"]["sha"], event["pull_request"]["head"]["sha"]
        else:
            event, base, head = None, args.base, args.head
            if not args.dry_run:
                with open(os.environ["GITHUB_EVENT_PATH"]) as file:
                    event = json.load(file)
        pr = event and f"{event['repository']['full_name']}#{event['pull_request']['number']}"
        session = pr or f"{os.path.basename(os.path.realpath(args.repo))}@{diff.git(args.repo, 'rev-parse', head).strip()[:12]}"
        with trace.span("gate.review", session=session, input=f"{pr or args.repo} {base}..{head}", repo=args.repo, base=base, head=head, pr=pr, sandbox=args.sandbox):
            result = review(args.repo, base, head, {"local": Local, "contree": Contree}[args.sandbox]())
            if not args.dry_run:
                github.publish(args.repo, result, event, time.monotonic() - started)
            trace.output(result)
    except Exception as error:
        print(f"slopgate: {error!r}", file=sys.stderr)
    print(json.dumps(result, indent=2))
