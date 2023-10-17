from __future__ import annotations
import argparse
import logging
from pathlib import Path
import shutil
from ghrepo import GHRepo
from ghtoken import get_ghtoken
from headerparser import HeaderParser
from .client import Client


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=GHRepo.parse)
    parser.add_argument(
        "files", nargs="+", type=argparse.FileType("r", encoding="utf-8")
    )
    args = parser.parse_args()
    hp = HeaderParser()
    hp.add_field("Title", required=True)
    hp.add_field("Milestone", default=None)
    hp.add_field("Labels", type=parse_labels, default=())
    logging.basicConfig(
        format="[%(levelname)-8s] %(message)s",
        level=logging.INFO,
    )
    done_dir = Path("DONE")
    done_dir.mkdir(parents=True, exist_ok=True)
    with Client(repo=args.repository, token=get_ghtoken()) as client:
        for fp in args.files:
            with fp:
                data = hp.parse(fp)
            if data["Milestone"] is not None:
                client.ensure_milestone(data["Milestone"])
            for lbl in data["Labels"]:
                client.ensure_label(lbl)
            client.create_issue(
                title=data["Title"],
                body=data.body or "",
                labels=data["Labels"],
                milestone=data["Milestone"],
            )
            shutil.move(fp.name, done_dir)


def parse_labels(s: str) -> list[str]:
    return [ss.strip() for ss in s.split(",")]


if __name__ == "__main__":
    main()
