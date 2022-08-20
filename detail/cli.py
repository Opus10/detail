"""
The detail CLI contains commands for creating notes, linting the
notes, and rendering them.

Commands
~~~~~~~~

* ``detail`` - Creates a note
* ``detail log`` - Renders templated notes
* ``detail lint`` - Validates structure of notes
"""
import sys

import click
from click_default_group import DefaultGroup

import detail as detail_module
from detail import core


@click.group(cls=DefaultGroup, default="detail", default_if_no_args=True)
def main():
    pass


@main.command()
@click.argument("note", required=False)
@click.option("-v", "--version", help="Show the version.", is_flag=True)
def detail(note, version):
    """
    Create a new note or print the version of this library.

    If a note path is provided, it will be updated.
    """
    if version:
        click.echo(f"detail {detail_module.__version__}")
    else:
        note_path, _ = core.detail(path=note)
        if note:
            click.echo(f"Updated note at {note_path}")
        else:
            click.echo(f"Created note at {note_path}")


@main.command()
@click.argument("range", nargs=-1)
@click.pass_context
def lint(ctx, range):
    """
    Run note linting against a range of commits.

    If ``:github/pr`` is provided as the range, the base branch of the pull
    request will be used as the revision range (e.g. ``origin/develop..``).
    """
    range = " ".join(range)
    is_valid, notes = core.lint(range)

    if not is_valid:
        if not notes:
            click.echo('No notes were found. Run "detail" to create one', err=True)
        else:
            failures = notes.filter("is_valid", False)
            err_msg = f"{len(failures)} out of {len(notes)} notes have failed linting:"
            click.echo(click.style(err_msg, fg="red"), err=True)

            for failure in failures:
                click.echo(f"{failure.path}: {failure.validation_errors}", err=True)

        ctx.exit(1)


@main.command()
@click.argument("range", nargs=-1)
@click.option(
    "--style",
    default="default",
    help=(
        "A template file nickname to use. Defaults to .detail/log.tpl."
        " When provided, .detail/log_{style}.tpl is loaded."
    ),
)
@click.option(
    "--template", help='A template string to use. When provided, supercedes the "style" option.'
)
@click.option(
    "--tag-match",
    help=(
        "A glob(7) pattern for matching tags when associating a tag with a"
        " note. Passed to ``git describe --contains --matches``"
        " when associating a tag with committed notes."
    ),
)
@click.option("--before", help="Filter notes before a date.")
@click.option("--after", help="Filter notes after a date.")
@click.option("--reverse", help="Reverse ordering of results.", is_flag=True)
@click.option("-o", "--output", help="Output file name of the log.")
def log(range, style, template, tag_match, before, after, reverse, output):
    """
    Run log output against a range of notes.

    If ``:github/pr`` is provided as the range, the base branch of the pull
    request will be used as the revision range (e.g. ``origin/develop..``).
    If ``:github/pr`` is used as the output target, the log will be written
    as a comment on the current Github pull request.
    """
    range = " ".join(range)
    core.log(
        range,
        style=style,
        template=template,
        tag_match=tag_match,
        before=before,
        after=after,
        reverse=reverse,
        output=output or sys.stdout,
    )
