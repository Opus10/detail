# Changelog

## 0.2.5 (2024-08-24)

#### Changes

  - Updated docs styling and testing dependencies by [@wesleykendall](https://github.com/wesleykendall) in [#9](https://github.com/Opus10/detail/pull/9).

## 0.2.4 (2024-04-22)

#### Trivial

  - Fixed doc and CI issues. [Wes Kendall, bed7e7c]

## 0.2.3 (2024-04-18)

#### Trivial

  - Fix devops script. [Wes Kendall, d006b54]
  - Upgrade with the latest Python template and migrate to MkDocs. [Wes Kendall, 42440de]

## 0.2.2 (2022-08-20)

#### Trivial

  - Fix release note rendering and code formatting changes [Wes Kendall, 3a94793]

## 0.2.1 (2022-07-31)

#### Trivial

  - Update with the latest Python template, fixing doc builds [Wes Kendall, 17df8b2]

## 0.2.0 (2022-03-22)

#### Feature

  - Change linting behavior, passing if no commits exist [Wes Kendall, 47b4908]

    If no commits exist during ``detail lint``, linting passes
    since there is nothing to check. If commits exist and there are no
    notes, linting fails like before.

## 0.1.1 (2022-03-21)

#### Trivial

  - Added docs and a small tutorial [Wes Kendall, fa2972d]

## 0.1.0 (2022-03-21)

#### Feature

  - V1 of detail [Wes Kendall, 2e077ec]

    V1 of ``detail`` includes the ability to make structured notes in a repository,
    allowing a user several options for automations on those notes.

    This V1 release was inspired by ``git-tidy`` and mimics the interface of it.
    The main difference here is that ``detail`` is storing structured notes in
    files that are part of the project instead of the commit log.

    Along with the core ``detail`` CLI for creating/updating notes, the CLI
    contains a ``lint`` subcommand for linting notes against a git range and
    a ``log`` subcommand for logging notes against a git range.
