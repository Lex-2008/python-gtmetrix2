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

manual
~~~~~~

* Clone or download and extract the repository

* Copy the ``src/python-gtmetrix2`` directory to your project directory

Usage:
------

Simplest example:

.. code-block:: python

    import json
    import python_gtmetrix2

    api_key = "e8ddc55d93eb0e8281b255ea236dcc4f"    # your API key
    url = "http://example.com"                      # URL to test

    account = python_gtmetrix2.Account(api_key)     # init
    test = account.start_test(url)                  # start test
    test.fetch(wait_for_completion=True)            # wait for it to finish
    report = test.getreport()                       # get test result

    print(json.dumps(report, indent=2))             # do something useful with it

For a wordy introduction into this library,
or a more technical explanation,
`dive into the docs <https://python-gtmetrix2.readthedocs.io/>`__

Versioning:
-----------

This project follows `semver <https://semver.org/spec/v2.0.0.html>`__
versioning scheme. Note that according to the semver, as long as the version
number starts with 0, no guarantees regarding compatibility are given.  Hence,
when anyone starts using this library, please let the author know about it, so
we can bump version number to one and "freeze" API compatibility.
