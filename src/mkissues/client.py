from __future__ import annotations
from collections.abc import Iterator, Sequence
from dataclasses import InitVar, dataclass, field
import logging
import platform
import random
from types import TracebackType
from ghrepo import GHRepo
import requests
from . import __url__, __version__

log = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"

USER_AGENT = "mkissues/{} ({}) requests/{} {}/{}".format(
    __version__,
    __url__,
    requests.__version__,
    platform.python_implementation(),
    platform.python_version(),
)


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


@dataclass
class ICaseSet:
    """A case-insensitive set of strings"""

    data: set[str] = field(init=False, default_factory=set)

    def add(self, s: str) -> None:
        self.data.add(s.lower())

    def __contains__(self, s: str) -> bool:
        return s.lower() in self.data


@dataclass
class Client:
    repo: GHRepo
    token: InitVar[str]
    session: requests.Session = field(init=False)
    milestones: set[str] = field(init=False, default_factory=set)
    labels: ICaseSet = field(init=False, default_factory=ICaseSet)

    def __post_init__(self, token: str) -> None:
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["Authorization"] = f"bearer {token}"
        self.session.headers["User-Agent"] = USER_AGENT
        self.session.headers["X-GitHub-Api-Version"] = "2022-11-28"
        log.debug("Fetching current milestones for %s ...", self.repo)
        for ms in self.paginate(self.milestone_url):
            self.milestones.add(ms["title"])
        log.debug("Fetching current labels for %s ...", self.repo)
        for lbl in self.paginate(self.label_url):
            self.labels.add(lbl["name"])

    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
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
            log.info("Creating milestone %r in %s", title, self.repo)
            r = self.session.post(self.milestone_url, json={"title": title})
            r.raise_for_status()
            self.milestones.add(title)

    def ensure_label(self, name: str) -> None:
        if name not in self.labels:
            log.info("Creating label %r in %s", name, self.repo)
            payload = {"name": name, "color": random.choice(COLORS)}
            r = self.session.post(self.label_url, json=payload)
            r.raise_for_status()
            self.labels.add(name)

    def create_issue(
        self, title: str, body: str, labels: Sequence[str], milestone: str | None
    ) -> None:
        log.info("Creating issue %r in %s", title, self.repo)
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
