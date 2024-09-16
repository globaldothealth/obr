import sys
import argparse
import webbrowser
from pathlib import Path

import requests

from .report import make_report
from .lint import lint
from .outbreaks import OUTBREAKS
from .util import msg_ok, msg_fail

USAGE = """olm: Office for Linelist Management

olm is a tool to operate on linelists provided from Global.health (G.h).
Linelists are epidemiological datasets with information about a disease
outbreak organised into one row per case. Currently it supports
generating briefing reports, fetching linelists and checking linelists
against a provided schema.

olm is organised into subcommands:

list        lists G.h outbreaks that olm supports
get         saves linelist data to disk
report      generates briefing report for an outbreak
lint        lints (checks) an outbreak linelist for errors
"""


def abort(msg):
    msg_fail("cli", msg)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Global.health outbreak report creator"
    )

    subparsers = parser.add_subparsers(dest="command")

    lint_parser = subparsers.add_parser(
        "lint", help="Lint outbreak data according to schema"
    )
    lint_parser.add_argument("outbreak", help="Outbreak name")
    lint_parser.add_argument("--data", help="Data URL")
    lint_parser.add_argument("--schema", help="Data schema path or URL")
    lint_parser.add_argument("--ignore", help="Ignore fields, comma-separated")

    get_parser = subparsers.add_parser("get", help="Get data for outbreak")
    get_parser.add_argument("outbreak", help="Outbreak name")

    _ = subparsers.add_parser("list", help="List outbreaks managed by olm")

    report_parser = subparsers.add_parser("report", help="Generate briefing report")
    report_parser.add_argument("outbreak", help="Outbreak name")
    report_parser.add_argument("--data", help="Data URL")
    report_parser.add_argument(
        "-b", "--bucket", help="S3 bucket to write outbreak report to"
    )
    report_parser.add_argument(
        "--cloudfront", help="Cloudfront distribution which should be invalidated"
    )
    report_parser.add_argument(
        "-o", "--open", action="store_true", help="Open local file in web browser"
    )

    args = parser.parse_args()
    if args.command and args.command != "list" and args.outbreak not in OUTBREAKS:
        abort(
            "outbreak not known, choose from: \033[1m"
            + ", ".join(OUTBREAKS)
            + "\033[0m"
        )
    bold_outbreak = f"\033[1m{args.outbreak}\033[0m"

    match args.command:
        case "list":
            for outbreak in OUTBREAKS:
                print(
                    f"\033[1m{outbreak:12s} \033[0m{OUTBREAKS[outbreak]['description']} [{OUTBREAKS[outbreak]['id']}]"
                )
        case "get":
            if "url" not in OUTBREAKS[args.outbreak]:
                abort(f"no data URL found for {bold_outbreak}")
            output_file = f"{args.outbreak}.csv"
            if (
                res := requests.get(OUTBREAKS[args.outbreak]["url"])
            ).status_code == 200:
                Path(output_file).write_text(res.text)
                msg_ok("get", "wrote " + output_file)
        case "lint":
            ignore_keys = args.ignore.split(",") if args.ignore is not None else []
            if (
                lint_result := lint(args.outbreak, args.data, args.schema, ignore_keys)
            ).ok:
                msg_ok("lint", "succeeded for " + bold_outbreak)
            else:
                msg_fail("lint", "failed for " + bold_outbreak)
                print(lint_result)
                sys.exit(2)
        case "report":
            make_report(
                args.outbreak,
                args.data or OUTBREAKS[args.outbreak]["url"],
                OUTBREAKS[args.outbreak],
                output_bucket=args.bucket,
                cloudfront_distribution=args.cloudfront,
            )
            if args.open and (Path(args.outbreak + ".html")).exists():
                webbrowser.open("file://" + str(Path.cwd() / (args.outbreak + ".html")))
        case None:
            print(USAGE)


if __name__ == "__main__":
    main()
