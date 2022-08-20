"""Integration tests for detail"""
from contextlib import ExitStack as does_not_raise
import io
import os
import pathlib
import shutil

import formaldict
import jinja2.exceptions
import pytest
import yaml

from detail import core
from detail import utils


@pytest.fixture()
def detail_config(tmp_path, mocker):
    """Creates an example detail config for integration tests"""
    detail_root = tmp_path / ".detail"
    detail_root.mkdir()

    detail_commit_config = detail_root / "schema.yaml"
    detail_commit_config.write_text(
        "- label: type\n"
        "  name: Type\n"
        "  help: The type of change.\n"
        "  type: string\n"
        "  choices:\n"
        "      - api-break\n"
        "      - bug\n"
        "      - feature\n"
        "      - trivial\n"
        "\n"
        "- label: summary\n"
        "  name: Summary\n"
        "  help: A high-level summary of the changes.\n"
        "  type: string\n"
        "\n"
        "- label: description\n"
        "  name: Description\n"
        "  help: An in-depth description of the changes.\n"
        "  type: string\n"
        '  condition: ["!=", "type", "trivial"]\n'
        "  multiline: True\n"
        "  required: False\n"
        "\n"
        "- label: jira\n"
        "  name: Jira\n"
        "  help: Jira Ticket ID.\n"
        "  type: string\n"
        "  required: false\n"
        '  condition: ["!=", "type", "trivial"]\n'
        "  matches: WEB-[\\d]+\n"
        "\n"
        "- label: component\n"
        "  type: string\n"
        "  required: false\n"
        '  condition: ["!=", "type", "trivial"]\n'
    )

    detail_commit_template = detail_root / "log.tpl"
    detail_commit_template.write_text(
        '{% for tag, notes_by_tag in notes.group("commit_tag").items() %}\n'
        '# {{ tag|default("Unreleased", True) }} '
        "{% if tag.date %}({{ tag.date.date() }}){% endif %}\n"
        "\n"
        "{% for type, notes_by_type in "
        'notes_by_tag.group("type", '
        "ascending_keys=True, none_key_last=True).items() %}\n"
        '## {{ type|default("Other", True)|title }}\n'
        "{% for note in notes_by_type %}\n"
        "- {{ note.summary }} [{{ note.commit_author_name }}, {{ note.commit_sha }}]\n"
        "{% if note.description %}\n"
        "\n"
        "  {{ note.description }}\n"
        "{% endif %}\n"
        "{% endfor %}\n"
        "{% endfor %}\n"
        "\n"
        "{% endfor %}\n"
    )

    mocker.patch(
        "detail.utils.get_detail_root",
        return_value=pathlib.Path(detail_root),
        autospec=True,
    )

    utils.get_detail_note_root().mkdir()

    yield tmp_path


@pytest.fixture()
def detail_repo(detail_config):
    """Create a git repo with for integration tests"""
    cwd = os.getcwd()
    os.chdir(detail_config)

    utils.shell("git init .")
    utils.shell('git config user.email "you@example.com"')
    utils.shell('git config user.name "Your Name"')

    with open(utils.get_detail_note_root() / "note1.yaml", "w") as f:
        f.write(
            "summary: Summary1 [skip ci]\ndescription: Description1\n"
            "type: api-break\njira: WEB-1111\n"
        )

    utils.shell("git add .")
    utils.shell('git commit -m "commit"')

    with open(utils.get_detail_note_root() / "note2.yaml", "w") as f:
        f.write("summary: Summary2\ndescription: Description2\ntype: bug\njira: WEB-1112\n")

    utils.shell("git add .")
    utils.shell('git commit -m "commit"')
    utils.shell("git tag v1.1")

    with open(utils.get_detail_note_root() / "note3.yaml", "w") as f:
        f.write("summary: Summary3\ntype: trivial\n")

    utils.shell("git add .")
    utils.shell('git commit -m "commit"')
    utils.shell("git tag dev1.2")
    utils.shell("git tag v1.2")

    with open(utils.get_detail_note_root() / "note4.yaml", "w") as f:
        f.write("summary: Summary4\ndescription: Description4\ntype: feature\njira: WEB-1113\n")

    utils.shell("git add .")
    utils.shell('git commit -m "commit"')

    with open(utils.get_detail_note_root() / "note5.yaml", "w") as f:
        f.write("summary: Invalid5\ndescription: Hi\ntype: feature\njira: INVALID\n")

    utils.shell("git add .")
    utils.shell('git commit -m "commit"')

    utils.shell('git commit --allow-empty -m $"Invalid5\n\n' 'Type: feature\nJira: INVALID"')
    # Create a commit that uses the same delimiter structure as detail
    # to create a scenario of an unparseable commit.
    # utils.shell('git commit --allow-empty -m $"Invalid6\n\nUnparseable: *{*"')

    yield detail_config

    os.chdir(cwd)


@pytest.mark.usefixtures("detail_repo")
def test_detail_log():
    """
    Integration test for detail-log
    """
    full_log = utils.shell_stdout("detail log")
    assert full_log.startswith("# Unreleased")
    assert "# v1.2" not in full_log  # dev1.2 takes precedence in this case
    assert "# dev1.2" in full_log
    assert "# v1.1" in full_log


@pytest.mark.usefixtures("detail_repo")
def test_detail_log_custom_template():
    """
    Integration test for detail-log with a custom template
    """
    full_log = utils.shell_stdout(
        'detail log --template="{% for note in notes %}{{note.commit_tag}}\n{% endfor %}"'
    )
    assert full_log == "None\nNone\ndev1.2\nv1.1\nv1.1"


@pytest.mark.usefixtures("detail_repo")
def test_commit_properties_and_range_filtering(mocker):
    """
    Integration test for core.NoteRange filtering, grouping, and excluding
    and core Commit properties
    """
    nr = core.NoteRange()

    # Check various commit properties
    invalid_note = list(nr.filter("is_valid", False))[0]
    assert (
        str(invalid_note.validation_errors)
        == 'jira: Value "INVALID" does not match pattern "WEB-[\\d]+".'
    )
    assert invalid_note.type == "feature"
    assert not invalid_note.is_valid
    with pytest.raises(AttributeError):
        invalid_note.invalid_attribute
    assert invalid_note.jira is None
    assert invalid_note.commit_tag is None

    api_break_note = list(nr.filter("type", "api-break"))[0]
    assert str(api_break_note.commit.tag) == "v1.1"

    # Check various filterings on the range
    assert len(nr.filter("is_valid", True)) == 4
    assert len(nr.filter("is_valid", False)) == 1
    assert len(nr.exclude("is_valid", False)) == 4
    assert len(nr.filter("type", "feature").filter("is_valid", True)) == 1
    assert len(nr.filter("summary", r".*\[skip ci\].*", match=True)) == 1
    assert len(nr.exclude("summary", r".*\[skip ci\].*", match=True)) == 4

    # Check groupings
    tag_groups = nr.group("commit_tag")
    assert len(tag_groups) == 3
    assert len(tag_groups[None]) == 2
    assert len(tag_groups["v1.1"]) == 2
    assert len(tag_groups["dev1.2"]) == 1
    assert len(tag_groups[None].group("type")) == 1
    assert list(tag_groups["v1.1"].group("type", ascending_keys=True)) == [
        "api-break",
        "bug",
    ]

    type_groups = nr.group("type")
    assert len(type_groups) == 4
    assert len(type_groups["api-break"]) == 1
    assert len(type_groups["bug"]) == 1
    assert len(type_groups["feature"]) == 2
    assert len(type_groups["trivial"]) == 1

    # Check group sorting
    assert list(nr.group("commit_tag", ascending_keys=True)) == [
        "dev1.2",
        "v1.1",
        None,
    ]
    assert list(nr.group("commit_tag", descending_keys=True)) == [
        "v1.1",
        "dev1.2",
        None,
    ]
    assert list(nr.group("commit_tag", ascending_keys=True, none_key_first=True)) == [
        None,
        "dev1.2",
        "v1.1",
    ]
    assert list(nr.group("commit_tag", descending_keys=True, none_key_first=True)) == [
        None,
        "v1.1",
        "dev1.2",
    ]

    # Try matching on the v* tags (no dev tags)
    nr = core.NoteRange(tag_match="v*")
    assert set(nr.group("commit_tag")) == {None, "v1.1", "v1.2"}

    # Try before/after filtering
    assert not list(core.NoteRange(before="2019-01-01"))
    assert len(core.NoteRange(after="2019-01-01")) == 5
    assert not list(core.NoteRange(after="2019-01-01", before="2019-01-01"))

    # Try reversing commits
    assert list(core.NoteRange(tag_match="v*", reverse=True))[0].type == "api-break"

    # Get a commit range over a github PR
    mocker.patch("detail.core._get_pull_request_range", autospec=True, return_value="")

    nr = core.NoteRange(":github/pr")
    assert len(nr) == 5


@pytest.mark.parametrize(
    "input_data",
    [
        {
            "type": "bug",
            "summary": "summary!",
            "description": "description!",
            "jira": "WEB-9999",
        },
        # Tests a scenario where a key is empty.
        {
            "type": "feature",
            "summary": "summary",
            "description": "description",
            "jira": "",
        },
        # Tests a scenario where twos keys are empty.
        {
            "type": "feature",
            "summary": "summary",
            "description": "description",
            "jira": "",
            "component": "",
        },
        # Tests committing key with double quotes
        {
            "type": "feature",
            "summary": "summary",
            "description": '"description"',
            "jira": "",
            "component": '"""',
        },
    ],
)
@pytest.mark.usefixtures("detail_repo")
def test_detail(mocker, input_data):
    """Tests core.detail and verifies the resulting note."""
    mocker.patch.object(
        formaldict.Schema, "prompt", autospec=True, return_value=mocker.Mock(data=input_data)
    )

    path, entry = core.detail()

    assert entry.data == input_data
    with open(path) as f:
        assert yaml.safe_load(f.read()) == input_data


@pytest.mark.usefixtures("detail_repo")
def test_detail_update(mocker):
    """Tests core.detail while updating a note."""
    input_data = {
        "type": "bug",
        "summary": "summary!",
        "description": "description!",
        "jira": "WEB-9999",
    }
    patch = mocker.patch.object(
        formaldict.Schema, "prompt", autospec=True, return_value=mocker.Mock(data=input_data)
    )
    path, entry = core.detail()

    update_data = {
        "type": "bug",
        "summary": "summary!",
        "description": "description!",
        "jira": "WEB-1000",
    }
    patch.return_value = mocker.Mock(data=update_data)
    new_path, entry = core.detail(path)

    assert new_path == path

    assert entry.data == update_data
    with open(path) as f:
        assert yaml.safe_load(f.read()) == update_data


@pytest.mark.usefixtures("detail_repo")
def test_lint():
    """Tests core.lint()"""
    passed, notes = core.lint()
    assert not passed
    assert len(notes) == 5
    assert len(notes.commits) == 6

    passed, notes = core.lint(range="HEAD..")
    assert passed
    assert len(notes) == 0
    assert len(notes.commits) == 0

    passed, notes = core.lint(range="HEAD~1..")
    assert not passed
    assert len(notes) == 0
    assert len(notes.commits) == 1


@pytest.mark.parametrize("output", [None, "output_file", io.StringIO(), ":github/pr"])
@pytest.mark.usefixtures("detail_repo")
def test_log(output, mocker):
    """Tests core.log() with various output targets"""
    patched_github = mocker.patch("detail.github.comment", autospec=True)
    rendered = core.log(output=output)

    if isinstance(output, str) and output != ":github/pr":
        with open(output) as f:
            rendered = f.read()
    elif output == ":github/pr":
        assert patched_github.called
    elif output is not None:
        rendered = output.getvalue()

    assert rendered.startswith("# Unreleased")
    assert "# dev1.2 (" in rendered
    assert "## Api-Break" in rendered


@pytest.mark.parametrize(
    "style, expected_exception",
    [
        ("default", does_not_raise()),
        (
            "custom",
            pytest.raises(jinja2.exceptions.TemplateNotFound, match="log_custom.tpl"),
        ),
    ],
)
@pytest.mark.usefixtures("detail_repo")
def test_log_no_template(style, expected_exception):
    """
    Tests core.log() when no template is present. The default detail template
    should be used when the default style is provided
    """
    os.remove(".detail/log.tpl")
    with expected_exception:
        rendered = core.log(style=style)

        assert "# v1.2" not in rendered  # dev1.2 takes precedence in this case
        assert "# dev1.2" in rendered
        assert "# v1.1" in rendered
        assert "Unreleased" in rendered
        assert "Description1" in rendered
        assert "Summary1" in rendered


@pytest.mark.usefixtures("detail_repo")
def test_log_deleted_files():
    """
    Tests core.log() when no template is present. The default detail template
    should be used when the default style is provided
    """
    shutil.rmtree(".detail/notes")
    rendered = core.log()
    assert not rendered.strip()
