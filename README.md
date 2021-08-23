python-gtmetrix2
================

**python-gtmetrix2** is a Python client library for [GTmetrix][gtmetrix] REST API [v2.0][v2] (hence 2 in the name).

[![Build Status](https://app.travis-ci.com/Lex-2008/python-gtmetrix2.svg?branch=main)](https://app.travis-ci.com/Lex-2008/python-gtmetrix2)
[![codecov](https://codecov.io/gh/Lex-2008/python-gtmetrix2/branch/main/graph/badge.svg?token=N8P5Z08497)](https://codecov.io/gh/Lex-2008/python-gtmetrix2)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-gtmetrix2)
![PyPI - License](https://img.shields.io/pypi/l/python-gtmetrix2)
![PyPI - Status](https://img.shields.io/pypi/status/python-gtmetrix2)
![PyPI - Downloads](https://img.shields.io/pypi/dm/python-gtmetrix2)


[gtmetrix]: https://gtmetrix.com/
[v2]: https://gtmetrix.com/api/docs/2.0/

Inspired by the [other library][other].

[other]: https://github.com/aisayko/python-gtmetrix

Goals:
-----

- [x] [CI][]
- [x] [100% code coverage][cov]
- [x] [pip package][pip]
- [ ] drop-in compatibility with previous library
- [ ] 100% coverage of [API][v2]
- [ ] fancy docs

[CI]: https://app.travis-ci.com/github/Lex-2008/python-gtmetrix2
[cov]: https://app.codecov.io/gh/Lex-2008/python-gtmetrix2/
[pip]: https://test.pypi.org/project/python-gtmetrix2/

Installation:
------------

### via pip

	pip install python-gtmetrix2

### file copy

Just download [this][py] file, save it as `python_gtmetrix2.py` in your project directory and

	import python_gtmetrix2

[py]: python_gtmetrix2/__init__.py

### Your favorite package manager

I wish...

Usage:
-----

Simplest example:

	def test_url(url, api_key):
		""" returns GTmetrix grade (one letter from A to F) for a given URL """
		interface = python_gtmetrix2.Interface(api_key) # init
		test = interface.start_test(url)                # start test
		test.fetch(True)                                # wait for it to finish
		report = test.getreport()                       # get test results
		return report['attributes']['gtmetrix_grade']   # return one-letter result

These five lines are explained below.


### Interface

Main entry point for this library is `Interface` class which is initialized like this:

	interface = python_gtmetrix2.Interface(api_key)

where `api_key` is your GTmetrix API key.

Interface lets you start tests, like this:

	test = interface.start_test(url)

where `url` is the url you want to test. Optionally, you can pass extra arguments, like this:

	test = interface.start_test(url, report='none', adblock=1)

Full list of available parameters is available in [GTmetrix API documentation][start], section "Test Parameters".
This call returns an object of type `Test`.
Note that this call does **not** wait for the test to finish.
To know how to wait for the test to finish, read on.

[start]: https://gtmetrix.com/api/docs/2.0/#api-test-start


You can also query for tests started within last 24 hours:

	tests = interface.list_tests()

This call returns a `list` of objects of type `Test`.

### Test

Object of type `Test` has two useful methods: `fetch` and `getreport`.
`fetch` updates test information from GTmetrix API server and has an optional argument `wait_for_completion`,
which, when set to `True`, instructs this method to wait until the test finishes.
Like this:

	test.fetch(True)

If the test completes successfully (which happens most of the time),
you can use `getreport` method to retrieve test results in the form of `Report` object.

Like this:

	report = test.getreport()

Note that `report` might be `None` if test did not finish successfully
(for example, due to connection or certificate error).

### Report

For now, report doesn't have anything useful,
but you can access all its data.
It's basically a `dict` containing all data returned by GTmetrix API.
You can consult all possible values in the [docs][repo]

[repo]: https://gtmetrix.com/api/docs/2.0/#api-report-by-id


Testing:
-------

Autotests are automated by [Travis][CI] in clouds, so to run them you can just create a PR.

To run tests locally, you need to install [pytest][] with [httpserver][].

[httpserver]: https://pypi.org/project/pytest-httpserver/
[pytest]: https://pypi.org/project/pytest/

To run tests, execute pytest like this:

	$ pytest
	======================== test session starts =========================
	platform linux -- Python 3.9.6, pytest-6.2.4, py-1.10.0, pluggy-0.13.1
	rootdir: /home/lex/git/python-gtmetrix2
	plugins: requests-mock-1.9.3, cov-2.12.1, httpserver-1.0.0
	collected 15 items                                                   

	tests.py ...............                                       [100%]

	========================= 15 passed in 0.80s =========================


To measure coverage, install [coverage][] and run it like this:

[coverage]: https://pypi.org/project/coverage/

	$ coverage run -m pytest

Its output is same as above. To show actual coverage values, run:

	$ coverage report
	Name                  Stmts   Miss  Cover
	-----------------------------------------
	python_gtmetrix2.py     155      0   100%
	tests.py                227      0   100%
	-----------------------------------------
	TOTAL                   382      0   100%

To generate a coverage report in html format, run:

	$ coverage html

It will output nothing, but create nice HTML report in the htmlcov directory.

Tis project aims for 100% code coverage by tests, so just mark untested lines
with `pragma: no cover` and be done with it, lol.
