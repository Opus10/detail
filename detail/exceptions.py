class Error(Exception):
    """The base error for all detail errors"""


class SchemaError(Error):
    """When an issue is found in the user-supplied schema"""


class CommitParseError(Error):
    """For representing errors when parsing commits"""


class GithubConfigurationError(Error):
    """When not correctly set up for Github access"""


class GithubPullRequestAPIError(Error):
    """When an unexpected error happens with the Github pull request API"""


class NoGithubPullRequestFoundError(Error):
    """When no Github pull requests have been opened"""


class MultipleGithubPullRequestsFoundError(Error):
    """When multiple Github pull requests have been opened"""
