from __future__ import annotations
import logging
from pathlib import Path
import shutil
import click
from ghrepo import GHRepo, get_local_repo
from ghtoken import get_ghtoken
from headerparser import HeaderParser
from . import __version__
from .client import Client

log = logging.getLogger(__name__)


class GHRepoParam(click.ParamType):
    name = "ghrepo"

    def convert(
        self,
        value: str | GHRepo,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> GHRepo:
        if isinstance(value, str):
            try:
                return GHRepo.parse(value)
            except KeyError as e:
                self.fail(f"{value!r}: {e}", param, ctx)
        else:
            return value

    def get_metavar(self, _param: click.Parameter) -> str:
        return "OWNER/NAME"


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    __version__,
    "-V",
    "--version",
    message="%(prog)s %(version)s",
)
@click.option("--delete", is_flag=True, help="Delete files after processing")
@click.option(
    "--done-dir",
    type=click.Path(
        exists=False, file_okay=False, dir_okay=True, writable=True, path_type=Path
    ),
    help="Move processed files to the given directory  [default: DONE]",
)
@click.option(
    "-R",
    "--repository",
    type=GHRepoParam(),
    default=get_local_repo,
    help="Create issues in the specified GitHub repository",
    show_default="local repository",
)
@click.argument(
    "files",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    nargs=-1,
)
def main(
    repository: GHRepo, files: tuple[Path, ...], delete: bool, done_dir: Path | None
) -> None:
    """
    Create GitHub issues from text files.

    Visit <https://github.com/jwodder/mkissues> for more information.
    """
    if delete and done_dir is not None:
        raise click.UsageError("--delete and --done-dir are mutually exclusive")
    logging.basicConfig(
        format="[%(levelname)-8s] %(message)s",
        level=logging.INFO,
    )
    hp = HeaderParser()
    hp.add_field("Title", required=True)
    hp.add_field("Milestone", default=None)
    hp.add_field("Labels", type=parse_labels, default=())
    if done_dir is not None:
        done_dir.mkdir(parents=True, exist_ok=True)
    with Client(repo=repository, token=get_ghtoken()) as client:
        for p in files:
            log.info("Processing %s ...", p)
            with p.open(encoding="utf-8") as fp:
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
            if done_dir is not None:
                log.info("Moving %s to %s", p, done_dir)
                shutil.move(p, done_dir)
            else:
                log.info("Deleting %s", p)
                p.unlink()


def parse_labels(s: str) -> list[str]:
    return [ss.strip() for ss in s.split(",")]


if __name__ == "__main__":
    main()
