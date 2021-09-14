Introduction
============

.. include:: warn.txt

.. currentmodule:: python_gtmetrix2

Account
~~~~~~~~~

Main entry point for this library is :class:`Account` class which is
initialized like this:

.. code-block:: python

    account = python_gtmetrix2.Account(api_key)

where ``api_key`` is your GTmetrix API key.

Object of this class lets you start tests, like this:

.. code-block:: python

    test = account.start_test(url)

where ``url`` is the url you want to test. Optionally, you can pass extra
arguments, like this:

.. code-block:: python

    test = account.start_test(url, report='none', adblock=1)

Full list of available parameters is available in `GTmetrix API documentation
<https://gtmetrix.com/api/docs/2.0/#api-test-start>`__, section "Test
Parameters".  This call returns an object of type :class:`Test`.  Note that
this call does **not** wait for the test to finish.  To know how to wait for
the test to finish, read on.

.. only:: Internal

        You can also query for tests started within last 24 hours:

        .. code-block:: python

            tests = account.list_tests()

        This call returns a :class:`list` of objects of type :class:`Test`.

Test
~~~~

Object of type :class:`Test` has two methods which you will be using:
:meth:`fetch() <Test.fetch>` and :meth:`getreport() <Test.getreport>`. Method
:meth:`fetch() <Test.fetch>` updates test information from GTmetrix API server
and has an optional argument ``wait_for_completion``, which, when set to
``True``, instructs this method to wait until the test finishes.

If the test completes successfully (which happens most of the time), you can
use :meth:`getreport() <Test.getreport>` method to retrieve test results in the
form of :class:`Report` object, like this:

.. code-block:: python

    test.fetch(wait_for_completion=True)
    report = test.getreport()

Note that ``report`` might be ``None`` if test did not finish successfully (for
example, due to connection or certificate error).

Report
~~~~~~

:class:`Report` is a descendant of :class:`dict`, so you can treat it like one:

.. code-block:: python

   print(json.dumps(report, indent=2))

Report also has :meth:`getresource <Report.getresource>` method which lets you
save a report resource (like a PDF representation of the report, screenshot, or
a video of loading website) to file or a variable in your program:

.. code-block:: python

   report.getresource('report.pdf', 'report.pdf')

----

That's all for now. More examples can be found in
`examples <https://github.com/Lex-2008/python-gtmetrix2/tree/main/examples>`__
directory in the repo.
