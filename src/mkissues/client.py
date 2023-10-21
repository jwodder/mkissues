from __future__ import annotations
from collections.abc import Iterator
from dataclasses import InitVar, dataclass, field
import json
import logging
import platform
import random
from types import TracebackType
from typing import Any
from ghrepo import GHRepo
import requests
from . import __url__, __version__

log = logging.getLogger(__name__)

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
    token: InitVar[str]
    session: requests.Session = field(init=False)

    def __post_init__(self, token: str) -> None:
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["Authorization"] = f"bearer {token}"
        self.session.headers["User-Agent"] = USER_AGENT
        self.session.headers["X-GitHub-Api-Version"] = "2022-11-28"

    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        self.session.close()

    def paginate(self, url: str) -> Iterator:
        while True:
            r = self.session.get(url)
            if not r.ok:
                raise PrettyHTTPError(r)
            yield from r.json()
            url2 = r.links.get("next", {}).get("url")
            if url2 is None:
                return
            url = url2

    def post(self, url: str, payload: Any) -> Any:
        r = self.session.post(url, json=payload)
        if not r.ok:
            raise PrettyHTTPError(r)
        return r.json()

    def get_auth_user(self) -> str:
        r = self.session.get("https://api.github.com/user")
        if not r.ok:
            raise PrettyHTTPError(r)
        login = r.json()["login"]
        assert isinstance(login, str)
        return login

    def get_issue_maker(self, repo: GHRepo) -> IssueMaker:
        log.debug("Fetching current milestones for %s ...", repo)
        milestones = set()
        for ms in self.paginate(f"{repo.api_url}/milestones"):
            milestones.add(ms["title"])
        log.debug("Fetching current labels for %s ...", repo)
        labels = ICaseSet()
        for lbl in self.paginate(f"{repo.api_url}/labels"):
            labels.add(lbl["name"])
        return IssueMaker(self, repo, milestones, labels)


@dataclass
class IssueMaker:
    client: Client
    repo: GHRepo
    milestones: set[str]
    labels: ICaseSet

    def ensure_milestone(self, title: str) -> None:
        if title not in self.milestones:
            log.info("Creating milestone %r in %s", title, self.repo)
            self.client.post(f"{self.repo.api_url}/milestones", {"title": title})
            self.milestones.add(title)

    def ensure_label(self, name: str) -> None:
        if name not in self.labels:
            log.info("Creating label %r in %s", name, self.repo)
            payload = {"name": name, "color": random.choice(COLORS)}
            self.client.post(f"{self.repo.api_url}/labels", payload)
            self.labels.add(name)

    def create_issue(
        self, title: str, body: str, labels: list[str], milestone: str | None
    ) -> None:
        log.info("Creating issue %r in %s", title, self.repo)
        payload = {
            "title": title,
            "body": body.rstrip(),
            "labels": labels,
            "milestone": milestone,
        }
        r = self.client.post(f"{self.repo.api_url}/issues", payload)
        log.info("New issue at: %s", r["url"])


@dataclass
class PrettyHTTPError(Exception):
    response: requests.Response

    def __str__(self) -> str:
        if 400 <= self.response.status_code < 500:
            msg = "{0.status_code} Client Error: {0.reason} for URL: {0.url}\n"
        elif 500 <= self.response.status_code < 600:
            msg = "{0.status_code} Server Error: {0.reason} for URL: {0.url}\n"
        else:
            msg = "{0.status_code} Unknown Error: {0.reason} for URL: {0.url}\n"
        msg = msg.format(self.response)
        try:
            resp = self.response.json()
        except ValueError:
            msg += self.response.text
        else:
            msg += json.dumps(resp, indent=4)
        return msg
