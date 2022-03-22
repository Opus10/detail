# Changelog
## 0.2.0 (2022-03-22)
### Feature
  - Change linting behavior, passing if no commits exist [Wes Kendall, 47b4908]

    If no commits exist during ``detail lint``, linting passes
    since there is nothing to check. If commits exist and there are no
    notes, linting fails like before.

## 0.1.1 (2022-03-21)
### Trivial
  - Added docs and a small tutorial [Wes Kendall, fa2972d]

## 0.1.0 (2022-03-21)
### Feature
  - V1 of detail [Wes Kendall, 2e077ec]

    V1 of ``detail`` includes the ability to make structured notes in a repository,
    allowing a user several options for automations on those notes.

    This V1 release was inspired by ``git-tidy`` and mimics the interface of it.
    The main difference here is that ``detail`` is storing structured notes in
    files that are part of the project instead of the commit log.

    Along with the core ``detail`` CLI for creating/updating notes, the CLI
    contains a ``lint`` subcommand for linting notes against a git range and
    a ``log`` subcommand for logging notes against a git range.

