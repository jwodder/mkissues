from __future__ import annotations

__requires__ = [
    "ghrepo ~= 0.1",
    "ghtoken ~= 0.1",
    "headerparser ~= 0.5.0",
    "requests ~= 2.20",
]

import argparse
from collections.abc import Iterator, Sequence
from dataclasses import InitVar, dataclass, field
import logging
from pathlib import Path
import random
import shutil
from typing import Any
from ghrepo import GHRepo
from ghtoken import get_ghtoken
from headerparser import HeaderParser
import requests

log = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"

# These are the "default colors" listed when creating a label via GitHub's web
# UI as of 2023-09-24:
COLORS = [
    "0052cc",
    "006b75",
    "0e8a16",
    "1d76db",
    "5319e7",
    "b60205",
    "bfd4f2",
    "bfdadc",
    "c2e0c6",
    "c5def5",
    "d4c5f9",
    "d93f0b",
    "e99695",
    "f9d0c4",
    "fbca04",
    "fef2c0",
]


def main():
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


@dataclass
class Client:
    repo: GHRepo
    token: InitVar[str]
    session: requests.Session = field(init=False)
    milestones: set[str] = field(init=False, default_factory=set)
    labels: set[str] = field(init=False, default_factory=set)

    def __post_init__(self, token: str) -> None:
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["Authorization"] = f"bearer {token}"
        self.session.headers["X-GitHub-Api-Version"] = "2022-11-28"
        log.info("Fetching current milestones for %s ...", self.repo)
        for ms in self.paginate(self.milestone_url):
            self.milestones.add(ms["title"])
        log.info("Fetching current labels for %s ...", self.repo)
        for lbl in self.paginate(self.label_url):
            self.labels.add(lbl["name"])

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.session.close()

    @property
    def repo_url(self) -> str:
        return f"{GITHUB_API_URL}/repos/{self.repo.owner}/{self.repo.name}"

    @property
    def milestone_url(self) -> str:
        return f"{self.repo_url}/milestones"

    @property
    def label_url(self) -> str:
        return f"{self.repo_url}/labels"

    def paginate(self, url: str) -> Iterator:
        while True:
            r = self.session.get(url)
            r.raise_for_status()
            yield from r.json()
            url2 = r.links.get("next", {}).get("url")
            if url2 is None:
                return
            url = url2

    def ensure_milestone(self, title: str) -> None:
        if title not in self.milestones:
            log.info("Creating milestone %r", title)
            r = self.session.post(self.milestone_url, json={"title": title})
            r.raise_for_status()
            self.milestones.add(title)

    def ensure_label(self, name: str) -> None:
        if name not in self.labels:
            log.info("Creating label %r", name)
            payload = {"name": name, "color": random.choice(COLORS)}
            r = self.session.post(self.label_url, json=payload)
            r.raise_for_status()
            self.labels.add(name)

    def create_issue(
        self, title: str, body: str, labels: Sequence[str], milestone: str | None
    ) -> None:
        log.info("Creating issue %r", title)
        payload = {
            "title": title,
            "body": body,
            "labels": labels,
            "milestone": milestone,
        }
        r = self.session.post(f"{self.repo_url}/issues", json=payload)
        r.raise_for_status()
        url = r.json()["url"]
        log.info("New issue at: %s", url)


if __name__ == "__main__":
    main()
