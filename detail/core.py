"""
The core detail API
"""

import collections.abc
import datetime as dt
import io
import re
import subprocess
import uuid

import dateutil.parser
import formaldict
import jinja2
import yaml

from detail import exceptions
from detail import github
from detail import utils


# The default log Jinja template
DEFAULT_LOG_TEMPLATE = """
{% for tag, notes_by_tag in notes.group('commit_tag').items() %}
## {{ tag|default('Unreleased', True) }} {% if tag.date %}({{ tag.date.date() }}){% endif %}
{% for note in notes_by_tag %}
- {{ note.commit_author_name }} [{{ note.commit_sha[:7] }}]

{% for key, value in note.schema_data.items() %}
  *{{ key }}*: {{ value|indent(4) }}
{% endfor %}

{% endfor %}
{% endfor %}
"""
# The special range value for git ranges against github pull requests
GITHUB_PR = ":github/pr"


def _output(*, value, path):
    """
    Outputs a value to a path.

    Args:
        value (str): The string to output.
        path (str|file): The path to which output is stored. If
            given a string, the value will be stored to the path referenced
            by the string. If ":github/pr" is the path, the value will be
            written as a Github pull request comment. If the path is anything
            but a string, it is treated as a file-like object. If path is
            ``None``, nothing is written.
    """
    if isinstance(path, str) and path != GITHUB_PR:
        with open(path, "w+") as f:
            f.write(value)
    elif isinstance(path, str) and path == GITHUB_PR:
        github.comment(value)
    elif path is not None:
        path.write(value)
        path.flush()


def _load_commit_schema(path=None, full=True):
    """Loads the schema expected for parsed commit messages"""
    schema = [
        {
            "label": "sha",
            "name": "SHA",
            "help": "Full SHA of the commit.",
            "type": "string",
        },
        {
            "label": "author_name",
            "name": "Author Name",
            "help": "The author name of the commit.",
            "type": "string",
        },
        {
            "label": "author_email",
            "name": "Author Email",
            "help": "The author email of the commit.",
            "type": "string",
        },
        {
            "label": "author_date",
            "name": "Author Date",
            "help": "The time at which the commit was authored.",
            "type": "datetime",
        },
        {
            "label": "committer_name",
            "name": "Committer Name",
            "help": "The name of the person who performed the commit.",
            "type": "string",
        },
        {
            "label": "committer_email",
            "name": "Committer Email",
            "help": "The email of the person who performed the commit.",
            "type": "string",
        },
        {
            "label": "committer_date",
            "name": "Committer Date",
            "help": "The time at which the commit was performed.",
            "type": "datetime",
        },
    ]

    return formaldict.Schema(schema)


def _load_note_schema(path=None):
    """Loads the detail schema"""
    path = path or utils.get_detail_schema_path()

    try:
        with open(path, "r") as schema_f:
            schema = yaml.safe_load(schema_f)
    except IOError:
        raise exceptions.SchemaError(
            'Must create a schema.yaml in the ".detail" directory of your project'
        )

    for entry in schema:
        if "label" not in entry:
            raise exceptions.SchemaError(f"Entry in schema does not have label - {entry}")

    return formaldict.Schema(schema)


class Tag(collections.UserString):
    """A git tag."""

    def __init__(self, tag):
        self.data = tag

    @classmethod
    def from_sha(cls, sha, tag_match=None):
        """
        Create a Tag object from a sha or return None if there is no
        associated tag

        Returns:
            Tag: A constructed tag or ``None`` if no tags contain the commit.
        """
        describe_cmd = f"git describe {sha} --contains"
        if tag_match:
            describe_cmd += f" --match={tag_match}"

        rev = (
            utils.shell_stdout(describe_cmd, check=False, stderr=subprocess.PIPE)
            .replace("~", ":")
            .replace("^", ":")
        )
        return cls(rev.split(":")[0]) if rev else None

    @property
    def date(self):
        """
        Parse the date of the tag

        Returns:
            datetime: The tag parsed as a datetime object.
        """
        if not hasattr(self, "_date"):
            try:
                self._date = dateutil.parser.parse(
                    utils.shell_stdout(f"git log -1 --format=%ad {self}")
                )
            except dateutil.parser.ParserError:
                self._date = None

        return self._date


class Commit(collections.UserDict):
    """
    A commit object, parsed from a dictionary of formatted
    commit data. Allows one to easily see the tag.
    """

    def __init__(self, data, tag_match=None):
        self.data = data
        self._tag_match = tag_match

    def __getattribute__(self, attr):
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            if attr in self.data:
                return self.data[attr]
            else:
                raise

    @property
    def tag(self):
        """Returns a `Tag` that contains the commit"""
        if not hasattr(self, "_tag"):
            self._tag = Tag.from_sha(self.sha, tag_match=self._tag_match)

        return self._tag


class Note(collections.UserDict):
    """
    A note object with an optional associated commit
    """

    def __init__(self, data, *, path, schema, commit=None):
        self.data = data
        self.path = path
        self._schema = schema
        self.commit = commit
        self.schema_data = schema.parse(data)

    def __getattribute__(self, attr):
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            if self.schema_data and attr in self.schema_data:
                return self.schema_data[attr]
            elif attr in self._schema:
                return None
            elif self.commit and attr.startswith("commit_") and hasattr(self.commit, attr[7:]):
                return getattr(self.commit, attr[7:])
            else:
                raise

    @property
    def validation_errors(self):
        """
        Returns the schema ``formaldict.Errors`` that occurred during
        validation
        """
        return self.schema_data.errors

    @property
    def is_valid(self):
        """
        ``True`` if the note was successfully validated against
        the schema. If ``False``, some attributes in the schema may
        be missing.
        """
        return self.schema_data.is_valid


def _equals(a, b, match=False):
    """True if a equals b. If match is True, perform a regex match

    If b is a regex ``Pattern``, applies regex matching
    """
    if match:
        return re.match(b, a) is not None if isinstance(a, str) else False
    else:
        return a == b


class Notes(collections.abc.Sequence):
    """A filterable and groupable collection of notes

    When a list of Note objects is organized in this sequence, the
    "group", "filter", and "exclude" chainable methods can be used
    for various access patterns. These access patterns are typically
    used when writing log templates.
    """

    def __init__(self, notes):
        self._notes = notes

    def __getitem__(self, i):
        return self._notes[i]

    def __len__(self):
        return len(self._notes)

    def filter(self, attr, value, match=False):
        """Filter notes by an attribute

        Args:
            attr (str): The name of the attribute on the `Note` object.
            value (str|bool): The value to filter by.
            match (bool, default=False): Treat ``value`` as a regex pattern and
                match against it.

        Returns:
            `Notes`: The filtered notes.
        """
        return Notes([note for note in self if _equals(getattr(note, attr), value, match=match)])

    def exclude(self, attr, value, match=False):
        """Exclude notes by an attribute

        Args:
            attr (str): The name of the attribute on the `Note` object.
            value (str|bool): The value to exclude by.
            match (bool, default=False): Treat ``value`` as a regex pattern and
                match against it.

        Returns:
            `Notes`: The excluded commits.
        """
        return Notes(
            [note for note in self if not _equals(getattr(note, attr), value, match=match)]
        )

    def group(
        self,
        attr,
        ascending_keys=False,
        descending_keys=False,
        none_key_first=False,
        none_key_last=False,
    ):
        """Group notes by an attribute

        Args:
            attr (str): The attribute to group by.
            ascending_keys (bool, default=False): Sort the keys in ascending
                order.
            descending_keys (bool, default=False): Sort the keys in descending
                order.
            none_key_first (bool, default=False): Make the "None" key be first.
            none_key_last (bool, default=False): Make the "None" key be last.

        Returns:
            `collections.OrderedDict`: A dictionary of `Notes` keyed on
            groups.
        """
        if any([ascending_keys, descending_keys]) and not any([none_key_first, none_key_last]):
            # If keys are sorted, default to making the "None" key last
            none_key_last = True

        # Get the natural ordering of the keys
        keys = list(collections.OrderedDict((getattr(note, attr), True) for note in self).keys())

        # Re-sort the keys
        if any([ascending_keys, descending_keys]):
            sorted_keys = sorted((k for k in keys if k is not None), reverse=descending_keys)
            if None in keys:
                sorted_keys.append(None)

            keys = sorted_keys

        # Change the ordering of the "None" key
        if any([none_key_first, none_key_last]) and None in keys:
            keys.remove(None)
            keys.insert(0 if none_key_first else len(keys), None)

        return collections.OrderedDict((key, self.filter(attr, key)) for key in keys)


def _get_pull_request_range():
    base = github.get_pull_request_base()
    return f"{base}.."


def _git_log(git_log_cmd):
    """
    Outputs git log in a format parseable as YAML.

    Args:
        git_log_cmd (str): The primary "git log .." command.
            This function adds the "--format" parameter to
            it and cleans the resulting log.

    Returns:
        List: Commit dictionaries
    """
    delimiter = "\n<-------->"
    git_log_stdout = utils.shell_stdout(
        f"{git_log_cmd} "
        '--format="'
        "sha: %H%n"
        "author_name: %an%n"
        "author_email: %ae%n"
        "author_date: %ad%n"
        "committer_name: %cn%n"
        "committer_email: %ce%n"
        "committer_date: %cd%n"
        f'%n{delimiter}"'
    )

    commit_schema = _load_commit_schema()
    return [
        commit_schema.parse(yaml.safe_load(io.StringIO(msg))).data
        for msg in git_log_stdout.split(delimiter)
        if msg.strip()
    ]


def _note_log(git_log_cmd):
    """
    Return the notes and the associated SHAs of when they were created.

    Args:
        git_log_cmd (str): The primary "git log .." command.
            This function adds additional parsing parameters and cleans
            the log.

    Returns:
        Dict: The file paths for each git sha
    """
    delimiter = "<-------->"
    git_log_stdout = utils.shell_stdout(
        f"{git_log_cmd} "
        f'--format="{delimiter}sha: %H"'
        f" --diff-filter=A --raw -- {utils.get_detail_note_root()}"
    )

    shas_to_files = {}
    msgs = [msg for msg in git_log_stdout.split(delimiter) if msg]
    for msg in msgs:
        split = msg.split("\n")
        sha = split[0][4:].strip()
        files = [line.split("\t")[1].strip() for line in split[1:] if line.strip()]
        shas_to_files[sha] = files

    notes = []
    root = utils.get_root()
    for sha, files in shas_to_files.items():
        for file_path in files:
            try:
                with open(root / file_path) as f:
                    file_contents = f.read()
            except FileNotFoundError:
                continue

            parsed_contents = yaml.safe_load(file_contents)
            notes.append((file_path, parsed_contents, sha))

    return notes


class NoteRange(Notes):
    """
    Represents a range of notes. The range can be filtered and grouped
    using all of the methods in `Notes`.

    When doing ``git log``, the user can provide a range
    (e.g. "origin/develop.."). Any range used in "git log" can be
    used as a range to the NoteRange object.

    If the special ``:github/pr`` value is used as a range, the Github
    API is used to figure out the range based on a pull request opened
    from the current branch (if found).
    """

    def __init__(self, range="", tag_match=None, before=None, after=None, reverse=False):
        self._commit_schema = _load_commit_schema()
        self._tag_match = tag_match
        self._before = before
        self._after = after
        self._reverse = reverse

        # The special ":github/pr" range will do a range against the base
        # pull request branch
        if range == GITHUB_PR:
            range = _get_pull_request_range()

        # Ensure any remotes are fetched
        utils.shell("git --no-pager fetch -q")

        git_log_cmd = f"git --no-pager log {range} --no-merges"
        if before:
            git_log_cmd += f" --before={before}"
        if after:
            git_log_cmd += f" --after={after}"
        if reverse:
            git_log_cmd += " --reverse"

        self.commits = {commit["sha"]: commit for commit in _git_log(git_log_cmd)}
        note_log = _note_log(git_log_cmd)

        self._range = range
        schema = _load_note_schema()

        return super().__init__(
            [
                Note(
                    data,
                    path=path,
                    schema=schema,
                    commit=Commit(self.commits[sha], tag_match=tag_match),
                )
                for path, data, sha in note_log
                if data
            ]
        )


def detail(path=None):
    """
    Creates or updates a note

    Arguments:
        path (str, default=None): A path to an existing note.
            If provided, the note will be updated.

    Returns:
        subprocess.CompletedProcess: The result from running
        git commit. Returns the git pre-commit hook results if
        failing during hook execution.
    """
    defaults = {}
    if path:
        with open(path) as f:
            defaults = yaml.safe_load(f.read())
    else:
        now = dt.datetime.utcnow()
        path = (
            utils.get_detail_note_root()
            / f'{now.strftime("%Y-%m-%d")}-{str(uuid.uuid4())[:6]}.yaml'
        )
        path.parent.mkdir(exist_ok=True, parents=True)

    schema = _load_note_schema()
    entry = schema.prompt(defaults=defaults)
    serialized = yaml.dump(entry.data, default_style="|")

    with open(path, "w") as f:
        f.write(serialized)

    return path, entry


def lint(range=""):
    """
    Lint notes against a range (branch, sha, etc).

    Linting passes when either succeed:

    - No commits are in the range.
    - Commits are found, and all notes pass linting. At least one
      note must be in the commit range.

    Args:
        range (str, default=''): The git revision range against which linting
            happens. The special value of ":github/pr" can be used to lint
            against the remote branch of the pull request that is opened
            from the local branch. No range means linting will happen against
            all commits.

    Raises:
        `NoGithubPullRequestFoundError`: When using ``:github/pr`` as
            the range and no pull requests are found.
        `MultipleGithubPullRequestsFoundError`: When using ``:github/pr`` as
            the range and multiple pull requests are found.

    Returns:
        tuple(bool, NoteRange): A tuple of the lint result (True/False)
        and the associated `NoteRange`
    """
    notes = NoteRange(range=range)
    if not notes.commits:
        return True, notes
    elif not notes:
        return False, notes
    else:
        return not notes.filter("is_valid", False), notes


def log(
    range="",
    style="default",
    template=None,
    tag_match=None,
    before=None,
    after=None,
    reverse=False,
    output=None,
):
    """
    Renders notes.

    Args:
        range (str, default=''): The git revision range over which logs are
            output. Using ":github/pr" as the range will use the base branch
            of an open github pull request as the range. No range will result
            in all commits being logged.
        style (str, default="default"): The template file nickname to use when rendering.
            Defaults to "default", which means ``.detail/log.tpl`` will
            be used to render. When used, the ``.detail/log_{{style}}.tpl``
            file will be rendered.
        template (str, default=None): A template string to use when rendering.
            Supercedes any style provided.
        tag_match (str, default=None): A glob(7) pattern for matching tags
            when associating a tag with a commit in the log. Passed through
            to ``git describe --contains --matches`` when finding a tag.
        before (str, default=None): Only return commits before a specific
            date. Passed directly to ``git log --before``.
        after (str, default=None): Only return commits after a specific
            date. Passed directly to ``git log --after``.
        reverse (bool, default=False): Reverse ordering of results. Passed
            directly to ``git log --reverse``.
        output (str|file): Path or file-like object to which the template is
            written. Using the special ":github/pr" output path will post the
            log as a comment on the pull request.

    Raises:
        `NoGithubPullRequestFoundError`: When using ``:github/pr`` as
            the range and no pull requests are found.
        `MultipleGithubPullRequestsFoundError`: When using ``:github/pr`` as
            the range and multiple pull requests are found.

    Returns:
        str: The rendered log.
    """
    notes = NoteRange(
        range=range,
        tag_match=tag_match,
        before=before,
        after=after,
        reverse=reverse,
    )

    if not template:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(utils.get_detail_root()),
            trim_blocks=True,
        )
        template_file = "log.tpl" if style == "default" else f"log_{style}.tpl"

        try:
            template = env.get_template(template_file)
        except jinja2.exceptions.TemplateNotFound:
            if style == "default":
                # Use the default template if the user didn't provide one
                template = jinja2.Template(DEFAULT_LOG_TEMPLATE, trim_blocks=True)
            else:
                raise
    else:
        template = jinja2.Template(template, trim_blocks=True)

    rendered = template.render(notes=notes, output=output, range=range)

    _output(path=output, value=rendered)

    return rendered
