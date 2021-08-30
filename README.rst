python-gtmetrix2
================

**python-gtmetrix2** is a Python client library for
`GTmetrix <https://gtmetrix.com/>`__ REST API
`v2.0 <https://gtmetrix.com/api/docs/2.0/>`__ (hence 2 in the name).

|Build Status| |codecov| |Code style: black| |Documentation Status|
|License: MIT|

|PyPI - Latest Version| |PyPI - Python Version|
|PyPI - Downloads Monthly| |PyPI - Downloads Daily|


.. |Build Status| image:: https://app.travis-ci.com/Lex-2008/python-gtmetrix2.svg?branch=main
   :target: https://app.travis-ci.com/Lex-2008/python-gtmetrix2
.. |codecov| image:: https://codecov.io/gh/Lex-2008/python-gtmetrix2/branch/main/graph/badge.svg?token=N8P5Z08497
   :target: https://codecov.io/gh/Lex-2008/python-gtmetrix2
.. |Code style: black| image:: https://img.shields.io/badge/code_style-black_--l_118-4c1.svg
   :target: https://github.com/psf/black
.. |Documentation Status| image:: https://readthedocs.org/projects/python-gtmetrix2/badge/?version=latest
   :target: https://python-gtmetrix2.readthedocs.io/en/latest/?badge=latest
.. |License: MIT| image:: https://img.shields.io/github/license/Lex-2008/python-gtmetrix2
   :target: https://github.com/Lex-2008/python-gtmetrix2/blob/main/LICENSE

.. |PyPI - Latest Version| image:: https://img.shields.io/pypi/v/python-gtmetrix2
   :target: https://pypi.org/project/python-gtmetrix2/
.. |PyPI - Python Version| image:: https://img.shields.io/pypi/pyversions/python-gtmetrix2
   :target: https://pypi.org/project/python-gtmetrix2/
.. |PyPI - Downloads Monthly| image:: https://img.shields.io/pypi/dm/python-gtmetrix2
   :target: https://pypi.org/project/python-gtmetrix2/
.. |PyPI - Downloads Daily| image:: https://img.shields.io/pypi/dd/python-gtmetrix2
   :target: https://pypi.org/project/python-gtmetrix2/
.. |PyPi - License| image:: https://img.shields.io/pypi/l/python-gtmetrix2
   :target: https://pypi.org/project/python-gtmetrix2/


Inspired by the `library with a similar
name <https://github.com/aisayko/python-gtmetrix>`__.

Installation:
-------------

via pip
~~~~~~~

.. code-block:: shell

    pip install python-gtmetrix2

file copy
~~~~~~~~~

This library has zero dependencies and is contained within a single file, so you can just save
`this <https://github.com/Lex-2008/python-gtmetrix2/blob/main/src/python_gtmetrix2/__init__.py>`__
file as ``python_gtmetrix2.py`` in your project directory and ``import`` it

Usage:
------

Simplest example:

.. code-block:: python

    import json
    import python_gtmetrix2
    api_key = "e8ddc55d93eb0e8281b255ea236dcc4f"    # your API key
    account = python_gtmetrix2.Account(api_key)     # init
    test = account.start_test(url)                  # start test
    test.fetch(wait_for_completion=True)            # wait for it to finish
    report = test.getreport()                       # get test result
    print(json.dumps(report, indent=2))             # do something useful with it

For an explanation of the above lines, `dive into the docs <https://python-gtmetrix2.readthedocs.io/>`__

Testing:
~~~~~~~~

Autotests are automated by
`Travis <https://app.travis-ci.com/github/Lex-2008/python-gtmetrix2>`__
in clouds, so to run them you can just create a PR.

To run tests locally, you need to install
`pytest <https://pypi.org/project/pytest/>`__ with
`httpserver <https://pypi.org/project/pytest-httpserver/>`__
and execute ``pytest`` in the root of this repository like this:

.. code-block:: shell

    ~/git/python-gtmetrix2$ pytest tests
    ======================== test session starts =========================
    platform linux -- Python 3.9.6, pytest-6.2.4, py-1.10.0, pluggy-0.13.1
    rootdir: /home/lex/git/python-gtmetrix2
    plugins: requests-mock-1.9.3, cov-2.12.1, httpserver-1.0.0
    collected 15 items                                                   

    tests/auto_test.py ...............                             [100%]

    ========================= 15 passed in 0.80s =========================

To measure coverage, install
`coverage <https://pypi.org/project/coverage/>`__ and run it like this:

.. code-block:: shell

    ~/git/python-gtmetrix2$ coverage run -m pytest tests

Its output is same as above. To show actual coverage values, run:

.. code-block:: shell

    ~/git/python-gtmetrix2$ coverage report --skip-empty
    Name                               Stmts   Miss  Cover
    ------------------------------------------------------
    src/python_gtmetrix2/__init__.py     155      0   100%
    tests/auto_test.py                   227      0   100%
    ------------------------------------------------------
    TOTAL                                382      0   100%

To generate a coverage report in html format, run:

.. code-block:: shell

    ~/git/python-gtmetrix2$ coverage html --skip-empty

It will output nothing, but create nice HTML report in the ``htmlcov``
directory.

Tis project aims for 100% code coverage by tests, so just mark untested lines
with ``pragma: no cover`` and be done with it, lol.

