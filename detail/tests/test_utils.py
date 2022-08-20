"""Tests the detail.utils() module"""
from detail import utils


def test_shell_stdout():
    """Tests utils.shell_stdout()"""
    assert utils.shell_stdout('echo "hello world"') == "hello world"


def test_get_root(mocker):
    """Tests utils.get_root()"""
    mocker.patch(
        "detail.utils.shell_stdout",
        autospec=True,
        # Return value for "git rev-parse --show-toplevel" call
        return_value="/work",
    )

    assert str(utils.get_root()) == "/work"


def test_get_detail_schema_path(mocker):
    """Tests utils.get_detail_schema_path()"""
    mocker.patch(
        "detail.utils.shell_stdout",
        autospec=True,
        # Return value for "git rev-parse --show-toplevel" call
        return_value="/work",
    )

    assert str(utils.get_detail_schema_path()) == "/work/.detail/schema.yaml"


def test_get_detail_note_root(mocker):
    """Tests utils.get_detail_note_root()"""
    mocker.patch(
        "detail.utils.shell_stdout",
        autospec=True,
        # Return value for "git rev-parse --show-toplevel" call
        return_value="/work",
    )

    assert str(utils.get_detail_note_root()) == "/work/.detail/notes"
