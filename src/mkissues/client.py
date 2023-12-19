from __future__ import annotations
from dataclasses import dataclass, field
import logging
import random
from ghrepo import GHRepo
import ghreq
from . import __url__, __version__

log = logging.getLogger(__name__)

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


class Client(ghreq.Client):
    def __init__(self, token: str) -> None:
        super().__init__(
            token=token,
            user_agent=ghreq.make_user_agent("mkissues", __version__, url=__url__),
        )

    def get_auth_user(self) -> str:
        login = self.get("/user")["login"]
        assert isinstance(login, str)
        return login

    def get_issue_maker(self, repo: GHRepo) -> IssueMaker:
        log.debug("Fetching current milestones for %s ...", repo)
        milestones = {}
        for ms in self.paginate(f"{repo.api_url}/milestones"):
            milestones[ms["title"]] = ms["number"]
        log.debug("Fetching current labels for %s ...", repo)
        labels = ICaseSet()
        for lbl in self.paginate(f"{repo.api_url}/labels"):
            labels.add(lbl["name"])
        return IssueMaker(self, repo, milestones, labels)


@dataclass
class IssueMaker:
    client: Client
    repo: GHRepo
    milestones: dict[str, int]
    labels: ICaseSet

    def ensure_milestone(self, title: str) -> int:
        if title not in self.milestones:
            log.info("Creating milestone %r in %s", title, self.repo)
            data = self.client.post(f"{self.repo.api_url}/milestones", {"title": title})
            self.milestones[title] = data["number"]
        return self.milestones[title]

    def ensure_label(self, name: str) -> None:
        if name not in self.labels:
            log.info("Creating label %r in %s", name, self.repo)
            payload = {"name": name, "color": random.choice(COLORS)}
            self.client.post(f"{self.repo.api_url}/labels", payload)
            self.labels.add(name)

    def create_issue(
        self, title: str, body: str, labels: list[str], milestone: int | None
    ) -> None:
        log.info("Creating issue %r in %s", title, self.repo)
        payload = {
            "title": title,
            "body": body.rstrip(),
            "labels": labels,
            "milestone": milestone,
        }
        r = self.client.post(f"{self.repo.api_url}/issues", payload)
        log.info("New issue at: %s", r["html_url"])
