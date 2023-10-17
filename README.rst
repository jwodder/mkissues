.. image:: https://www.repostatus.org/badges/latest/concept.svg
    :target: https://www.repostatus.org/#concept
    :alt: Project Status: Concept – Minimal or no implementation has been done
          yet, or the repository is only intended to be a limited example,
          demo, or proof-of-concept.

.. image:: https://github.com/jwodder/mkissues/actions/workflows/test.yml/badge.svg
    :target: https://github.com/jwodder/mkissues/actions/workflows/test.yml
    :alt: CI Status

.. image:: https://img.shields.io/github/license/jwodder/mkissues.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/mkissues>`_
| `Issues <https://github.com/jwodder/mkissues/issues>`_

``mkissues`` is a command for creating GitHub issues from local Markdown files
formatted with special headers.


Installation
============
``mkissues`` requires Python 3.10 or higher.  Just use `pip
<https://pip.pypa.io>`_ for Python 3 (You have pip, right?) to install it::

    python3 -m pip install git+https://github.com/jwodder/mkissues.git


Usage
=====

::

    mkissues [<options>] [<files>]

``mkissues`` creates a GitHub issue from each file specified on the command
line; see "`File Format`_" below.  Issues can be created with specific labels
and/or milestones; if a file specifies a label or milestone that does not yet
exist in the repository, the label or milestone is created.  After an issue is
created, its file is either moved to a separate directory or deleted, depending
on the options passed to the ``mkissues`` command.

By default, ``mkissues`` creates issues in the GitHub repository listed as the
``origin`` remote for the Git repository in the current directory; a different
GitHub repository can be specified via the ``-R``/``--repository`` option.


File Format
-----------

Each input file must be a UTF-8 text file that starts with one or more "Name:
Value" header lines.  The header may optionally be followed by a blank line,
everything after which becomes the body of the new issue.

The following headers (case insensitive) are recognized.  Unknown headers are
an error.

``Title``
    *(required)* The title for the new issue

``Labels``
    A list of comma-separated labels to apply to the new issue

``Milestone``
    The name of a milestone to set for the new issue


Options
-------

--delete                        Delete each input file after processing.

                                This option is mutually exclusive with
                                ``--done-dir``.

--done-dir DIR                  Move each input file to the given directory
                                after processing.  This is the default
                                behavior.  [default directory: ``DONE/``]

                                This option is mutually exclusive with
                                ``--delete``.

-R SPEC, --repository SPEC      Operate on the specified GitHub repository.  A
                                repository can be specified in the form
                                ``OWNER/NAME`` or as a GitHub repository URL.

Authentication
--------------

``mkissues`` requires a GitHub access token with appropriate permissions in
order to run.  Specify the token via the ``GH_TOKEN`` or ``GITHUB_TOKEN``
environment variable (possibly in an ``.env`` file), by storing a token with
the ``gh`` or ``hub`` command, or by setting the ``hub.oauthtoken`` Git config
option in your ``~/.gitconfig`` file.
