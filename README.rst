detail
#######

``detail`` allows contributors to create structured and configurable notes in a project,
providing the ability to do automations such as:

1. Ensuring that contributors add information to pull requests that provide
   QA instructions, release notes, and associated tickets. The ``detail lint`` command
   ensures that notes are present in a pull request and adhere to the schema.

2. Rendering dynamic logs from the notes. ``detail log`` provides the ability
   to slice and dice the commit log however you need, pulling in a ``notes``
   variable in a Jinja template with all notes that can be grouped and filtered.

3. Other automations, such as version bumping, Slack posting, ticket comments,
   etc can be instrumented in continuous integration from the structured notes.

When contributing a change, call ``detail`` to be prompted for all information
defined in the project's detail schema. Information can be collected conditionally
based on previous steps all thanks to the `formaldict <https://github.com/Opus10/formaldict>`__ library.

Below is an example of a contributor creating a structured note with the type
of change they are making, a summary, a description, and an associated Jira
ticket:

.. image:: https://raw.githubusercontent.com/opus10/detail/master/docs/_static/detail-intro.gif
    :width: 600

Notes are commited to projects, allowing review of them before they are used to
perform automations in continuous integration.

Documentation
=============

`View the detail docs here
<https://detail.readthedocs.io/>`_.

Installation
============

Install detail with::

    pip3 install detail


Contributing Guide
==================

For information on setting up detail for development and
contributing changes, view `CONTRIBUTING.rst <CONTRIBUTING.rst>`_.

Primary Authors
===============

- @wesleykendall (Wes Kendall)
- @tomage (Tómas Árni Jónasson)
