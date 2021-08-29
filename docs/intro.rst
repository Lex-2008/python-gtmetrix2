Introdunction
=============

Interface
~~~~~~~~~

Main entry point for this library is :class:`Interface` class which is
initialized like this:

.. code-block:: python

    interface = python_gtmetrix2.Interface(api_key)

where ``api_key`` is your GTmetrix API key.

Interface lets you start tests, like this:

.. code-block:: python

    test = interface.start_test(url)

where ``url`` is the url you want to test. Optionally, you can pass extra
arguments, like this:

.. code-block:: python

    test = interface.start_test(url, report='none', adblock=1)

Full list of available parameters is available in `GTmetrix API documentation
<https://gtmetrix.com/api/docs/2.0/#api-test-start>`__, section "Test
Parameters".  This call returns an object of type :class:`Test`.  Note that
this call does **not** wait for the test to finish.  To know how to wait for
the test to finish, read on.

.. only:: Internal

        You can also query for tests started within last 24 hours:

        .. code-block:: python

            tests = interface.list_tests()

        This call returns a :class:`list` of objects of type :class:`Test`.

Test
~~~~

Object of type :class:`Test` has two useful methods: :meth:`Test.fetch` and :meth:`Test.getreport`.
:meth:`Test.fetch` updates test information from GTmetrix API server and has an optional
argument ``wait_for_completion``, which, when set to ``True``, instructs this
method to wait until the test finishes.  Like this:

.. code-block:: python

    test.fetch(wait_for_completion=True)

If the test completes successfully (which happens most of the time), you can
use ``getreport`` method to retrieve test results in the form of ``Report``
object.

Like this:

.. code-block:: python

    report = test.getreport()

Note that ``report`` might be ``None`` if test did not finish successfully (for
example, due to connection or certificate error).

Report
~~~~~~

For now, report doesn't provide any special functionality, but you can access
all its data.  It's basically a ``dict`` containing all data returned by
GTmetrix API.  You can consult all possible values in the `docs
<https://gtmetrix.com/api/docs/2.0/#api-report-by-id>`__.

More examples
~~~~~~~~~~~~~

are in
`examples <https://github.com/Lex-2008/python-gtmetrix2/tree/main/examples>`__
directory.
