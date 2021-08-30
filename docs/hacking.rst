Contributing
============

Any feedback or PRs are welcome

Testing
-------

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

Examples serve as kind of "manual" tests.

Coverage
--------

Code coverage by autotests is measured by
`Codecov <https://app.codecov.io/gh/Lex-2008/python-gtmetrix2>`__
in clouds, so you can see results in PRs.

To measure coverage manually, install
`coverage <https://pypi.org/project/coverage/>`__ and run it like this:

.. code-block:: shell

    ~/git/python-gtmetrix2$ coverage run -m pytest tests

Its output is same as when running tests. To show actual coverage values, run:

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

