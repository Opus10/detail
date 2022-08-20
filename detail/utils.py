"""
Utilities for detail
"""

import pathlib
import subprocess


def shell(cmd, check=True, stdin=None, stdout=None, stderr=None):
    """Runs a subprocess shell with check=True by default"""
    return subprocess.run(cmd, shell=True, check=check, stdin=stdin, stdout=stdout, stderr=stderr)


def shell_stdout(cmd, check=True, stdin=None, stderr=None):
    """Runs a shell command and returns stdout"""
    ret = shell(cmd, stdout=subprocess.PIPE, check=check, stdin=stdin, stderr=stderr)
    return ret.stdout.decode("utf-8").strip() if ret.stdout else ""


def get_root():
    """
    Get the root path in the git project
    """
    top_level = shell_stdout("git rev-parse --show-toplevel")
    return pathlib.Path(top_level)


def get_detail_root():
    """
    Get the detail storage path in the git project
    """
    return get_root() / ".detail"


def get_detail_schema_path():
    """
    Get the default schema path
    """
    return get_detail_root() / "schema.yaml"


def get_detail_note_root():
    """
    The root path where notes are stored
    """
    return get_detail_root() / "notes"
