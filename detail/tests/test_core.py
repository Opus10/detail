"""Tests the detail.core module

Most of the test coverage of the core module is from the integration
tests in detail/tests/test_integration.py.
"""
from contextlib import ExitStack as does_not_raise
from unittest import mock

import pytest

from detail import core
from detail import exceptions


# A valid user schema
valid_schema = """
- label: type
- label: summary
- label: description
  condition: ['!=', 'type', 'trivial']
  multiline: True
  required: False
 """

# An invalid user schema
invalid_schema = "- invalid: type"


@pytest.mark.parametrize(
    "user_schema, expected_exception, expected_schema_labels",
    [
        (
            valid_schema,
            does_not_raise(),
            [
                "type",
                "summary",
                "description",
            ],
        ),
        (None, pytest.raises(exceptions.SchemaError), None),
        (
            invalid_schema,
            pytest.raises(exceptions.SchemaError),
            None,
        ),
    ],
)
def test_load_note_schema(
    tmp_path,
    mocker,
    user_schema,
    expected_exception,
    expected_schema_labels,
):
    """Tests core._load_note_schema()"""
    user_schema_file = tmp_path / "schema.yaml"
    if user_schema:
        user_schema_file.write_text(user_schema)

    with expected_exception:
        schema = core._load_note_schema(path=user_schema_file)
        assert [s["label"] for s in schema] == expected_schema_labels


@pytest.mark.parametrize(
    "sha, tag_match, git_describe_output, expected_git_call, expected_tag_value",
    [
        ("sha1", None, "0.1~8", "git describe sha1 --contains", "0.1"),
        (
            "sha1",
            "pattern",
            "",
            "git describe sha1 --contains --match=pattern",
            "None",
        ),
    ],
)
def test_tag_from_sha(
    mocker,
    sha,
    tag_match,
    git_describe_output,
    expected_git_call,
    expected_tag_value,
):
    """Tests core.Tag.from_sha()"""
    patched_describe = mocker.patch(
        "detail.utils.shell_stdout",
        autospec=True,
        return_value=git_describe_output,
    )

    assert str(core.Tag.from_sha(sha, tag_match=tag_match)) == expected_tag_value
    assert patched_describe.call_args_list[0][0][0] == expected_git_call


@pytest.mark.parametrize(
    "git_log_output, expected_git_log_call, expected_date",
    [("", mock.call("git log -1 --format=%ad 2.1"), None)],
)
def test_tag_date(mocker, git_log_output, expected_git_log_call, expected_date):
    """Tests core.Tag.date()"""
    patched_shell = mocker.patch(
        "detail.utils.shell_stdout", autospec=True, return_value=git_log_output
    )
    tag = core.Tag("2.1")

    assert tag.date == expected_date
    assert tag.date == expected_date  # Run twice to exercise caching
    assert patched_shell.call_args_list == [expected_git_log_call]


def test_get_pull_request_range(mocker):
    """Tests core._get_pull_request_range"""
    mocker.patch(
        "detail.github.get_pull_request_base",
        autospec=True,
        return_value="develop",
    )
    assert core._get_pull_request_range() == "develop.."
