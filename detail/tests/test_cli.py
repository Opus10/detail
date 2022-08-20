import sys
from unittest import mock

import pytest

from detail import cli


@pytest.fixture
def mock_exit(mocker):
    yield mocker.patch("sys.exit", autospec=True)


@pytest.fixture
def mock_successful_exit(mock_exit):
    yield
    mock_exit.assert_called_once_with(0)


@pytest.mark.usefixtures("mock_successful_exit")
def test_detail_v(mocker, capsys):
    """Test calling detail -v"""
    mocker.patch.object(sys, "argv", ["detail", "-v"])

    cli.main()

    out, _ = capsys.readouterr()
    assert out.startswith("detail ")


@pytest.mark.parametrize(
    "command_args, expected_detail_call",
    [
        ([], mock.call(path=None)),
        (["path"], mock.call(path="path")),
    ],
)
def test_detail(mock_exit, mocker, command_args, expected_detail_call):
    """Test calling detail"""
    mocker.patch.object(sys, "argv", ["detail"] + command_args)
    patched_detail = mocker.patch(
        "detail.core.detail",
        autospec=True,
        return_value=("path", {}),
    )

    cli.main()

    assert patched_detail.call_args_list == [expected_detail_call]


@pytest.mark.parametrize(
    "command_args, lint_is_valid, expected_lint_call, expected_stderr",
    [
        ([], True, mock.call(""), ""),
        (["range"], True, mock.call("range"), ""),
        (
            ["range"],
            False,
            mock.call("range"),
            (
                "2 out of 2 notes have failed linting:\n"
                ".detail/1.yaml: ['error1', 'error2']\n.detail/2.yaml: ['error3', 'error4']\n"
            ),
        ),
    ],
)
def test_lint(
    mock_exit,
    mocker,
    capsys,
    command_args,
    lint_is_valid,
    expected_lint_call,
    expected_stderr,
):
    """Test calling detail lint"""
    mocker.patch.object(sys, "argv", ["detail", "lint"] + command_args)
    notes = mocker.MagicMock(
        __len__=lambda a: 2,
        filter=lambda a, b: [
            mocker.Mock(path=".detail/1.yaml", validation_errors=["error1", "error2"]),
            mocker.Mock(path=".detail/2.yaml", validation_errors=["error3", "error4"]),
        ],
    )
    patched_lint = mocker.patch(
        "detail.core.lint", autospec=True, return_value=(lint_is_valid, notes)
    )

    cli.main()

    _, err = capsys.readouterr()
    assert patched_lint.call_args_list == [expected_lint_call]
    mock_exit.assert_called_once_with(0 if lint_is_valid else 1)
    assert err == expected_stderr


@pytest.mark.parametrize(
    "command_args, expected_log_call",
    [
        (  # Verify default parameters are filled out
            [],
            mock.call(
                "",
                style="default",
                template=None,
                tag_match=None,
                before=None,
                after=None,
                reverse=False,
                output=sys.stdout,
            ),
        ),
        (  # Verify default parameters are filled out
            [
                "range",
                "--style=new",
                "--tag-match=pattern",
                "--before=before",
                "--after=after",
                "--reverse",
                "-o",
                "file",
            ],
            mock.call(
                "range",
                style="new",
                template=None,
                tag_match="pattern",
                before="before",
                after="after",
                reverse=True,
                output="file",
            ),
        ),
    ],
)
@pytest.mark.usefixtures("mock_successful_exit")
def test_log(mocker, command_args, expected_log_call):
    """Test calling detail log"""
    mocker.patch.object(sys, "argv", ["detail", "log"] + command_args)
    patched_commit = mocker.patch("detail.core.log", autospec=True)

    cli.main()

    assert patched_commit.call_args_list == [expected_log_call]
