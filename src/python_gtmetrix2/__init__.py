# python-gtmetrix2
#
# a Python client library for GTmetrix REST API v2.0 (hence 2 in the name).
#
# Library overview
# ================
"""
Overview
--------

User of this library is expected to interact primarily with the following three
classes:

* :class:`Account`, which is instantiated with your API key and is used for
  all API calls which don't operate on a particular test or report. For
  example, API calls to start a *new* test (:meth:`Account.start_test`), or
  to get account information (:meth:`Account.status`).

* :class:`Test`, which corresponds to a requested test (which might be still
  running or already finished).

* :class:`Report`, which describes results of a *successfully finished* test.

Note that usually objects of :class:`Test` and :class:`Report` classes should
not be instantiated directly - users of this library are expected to use
methods of :class:`Account` class instead: for example,
:meth:`Account.start_test` to start a test, or :meth:`Account.list_tests`
to get a list of recent tests. And then :meth:`Test.getreport` to get a report
for a finished test.

Also note that :class:`Test` and :class:`Report` classes are descendants of the
dict, so you can operate on as such: :func:`json.dumps` them to inspect
their internals, and access their attributes same way as for a :class:`dict`.

Public API classes
------------------
"""
import json
import shutil
import time


from .exceptions import *
from ._internals import *


class Account:
    """Main entry point into this library

    :param api_key: your GTmetrix API key.

    :param str, optional base_url:
        base URL for all API requests - useful for testing or if
        someone implements a GTmetrix competitor with a compatible API,
        defaults to "https://gtmetrix.com/api/2.0/"

    :param method, optional sleep_function:
        the function to execute when waiting between retries (after receiving a
        "429" response) - useful for testing, or if someone wants to add some
        logging or notification of a delayed request, defaults to
        :func:`time.sleep`
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://gtmetrix.com/api/2.0/",
        sleep_function=time.sleep,
    ):
        self._requestor = Requestor(api_key, base_url, sleep_function)
        self._sleep = sleep_function

    def start_test(self, url: str, **attributes) -> "Test":
        """Start a Test

        :param str url: the URL to test.

        You can pass additional parameters for the tests (like browser,
        location, desired report depth, etc) as extra keyword arguments, like
        this:

        >>> account.start_test('http://example.com', report='none')

        Or, if you prefer having a dict, you can use the ``**kwargs``-style
        Python expansion, like this:

        >>> parameters={'location': '1', 'browser': '3', 'adblock': '1'}
        >>> account.start_test('http://example.com', **parameters)

        Note that this method does not wait for the test to finish.  For that,
        call :meth:`test.fetch(wait_for_completion=True) <Test.fetch>` after
        calling this method.

        :returns: a new instance of :class:`Test` corresponding to a new running test.

        :rtype: Test
        """
        attributes["url"] = url
        data = {"type": "test", "attributes": attributes}
        (response, response_data) = self._requestor.request(
            "tests",
            data={"data": data},
            method="POST",
            headers={"Content-Type": "application/vnd.api+json"},
        )
        if __debug__:
            if not dict_is_test(response_data["data"]):
                raise APIFailureException(
                    "API returned non-test for a started test",
                    None,
                    response,
                    response_data,
                )
        test = Test(self._requestor, response_data["data"], self._sleep)
        # TODO: do something with credits_left and credits_used
        return test

    def list_tests(self, sort=None, filter=None, page_number=0):
        """Get a list of recent tests.

        Note that while *reports* are stored on GTmetrix servers for several (1
        to 6) months, tests are deleted after 24 hours.  Hence, this function
        lists only rather recent tests.

        :param str, optional sort:
            Sort string by one of "created", "started", "finished", optionally
            prefixed with "-" for reverse sorting, defaults to None (no sort).

        :param dict filter:
            Filter tests - argument should be a dict of key/value pairs, where
            key is one of "state", "created", "started", "finished", "browser",
            "location", optionally postfixed with one of ":eq, :lt, :lte, :gt,
            :gte" and value is, well, value (string or number).  Valid values
            for "state" are "queued", "started", "error", and "completed".
            "created", "started" and "finished" are UNIX timestamps.  "browser"
            and "location" are browser and location IDs.

        :rtype: list(Test)

        :examples:

            To get all tests finished successfully within last 10 minutes:

            >>> import time
            >>> now = int(time.time())
            >>> tests = account.list_tests(
            ...     filter={"state": "completed", "created:gt": (now-10*60)})

            To get all tests which ended up with an error, and print the error
            message for each of them:

            >>> tests = account.list_tests(filter={"state": "error"})
            >>> for test in tests:
            ...     print("Test %s failed: %s" % (test["id"], test["attributes"]["error"]))

        """
        query = []
        if sort is not None:
            query.append("sort=" + sort)
        if filter is not None:
            query.extend(["filter[%s]=%s" % (k, v) for (k, v) in filter.items()])

        (response, response_data) = self._requestor.request("tests?" + "&".join(query))
        # TODO: pagination:
        # next_link=first_link
        # results=[]
        # while next_link:
        #  request
        #  results.extend(request_data...)
        #  next_link=request_data.get(..., None)
        if __debug__:
            if not isinstance(response_data["data"], list):
                raise APIFailureException(
                    "API returned non-list for a list of tests",
                    None,
                    response,
                    response_data,
                )
            if not all((dict_is_test(test) for test in response_data["data"])):
                raise APIFailureException(
                    "API returned non-test in a list of tests",
                    None,
                    response,
                    response_data,
                )
        tests = [Test(self._requestor, test_data, self._sleep) for test_data in response_data["data"]]
        return tests

    def status(self):
        """Get the current account details and status.

        Returns :class:`dict` with information about your api key, current API credit balance, and time of next credit refill (Unix timestamp).

        :example:

            >>> account = Account("e8ddc55d93eb0e8281b255ea236dcc4f")
            >>> status = account.status()
            >>> print(json.dumps(status, indent=2))

            would print something like this:

            .. code-block:: json

                {
                  "type": "user",
                  "id":   "e8ddc55d93eb0e8281b255ea236dcc4f",
                  "attributes": {
                    "api_credits": 1497,
                    "api_refill":  1618437519
                  }
                }
        """
        (response, response_data) = self._requestor.request("status")
        if __debug__:
            if not dict_is_user(response_data["data"]):
                raise APIFailureException(
                    "API returned non-user for status",
                    None,
                    response,
                    response_data,
                )
        return response_data["data"]

    def testFromId(self, test_id):
        """Fetches a test with given id and returns the corresponding :class:`Test` object.

        :param str test_id:
            ID of test to fetch. Note that if such test does not exist, an
            exception will be raised.

        :rtype: Test
        """
        return Test._fromURL(
            self._requestor, self._requestor.base_url + "/tests/" + test_id, sleep_function=self._sleep
        )

    def reportFromId(self, report_id):
        """Fetches a report with given id and returns the corresponding :class:`Report` object.

        :param str report_id:
            ID (slug) of report to fetch. Note that if such report does not
            exist, an exception will be raised.

        :rtype: Report
        """
        return Report._fromURL(
            self._requestor, self._requestor.base_url + "/reports/" + report_id, sleep_function=self._sleep
        )


class Test(Object):
    _report = None

    def fetch(self, wait_for_completion=False, retries=10):
        """Ask API server for updated data regarding this test.

        :param bool, optional wait_for_completion:
            Whether to wait until the test is finished, defaults to False

        :param int, optional retries:
            Number of retries before giving up, defaults to 10
        """
        (response, response_data) = self._requestor.request("tests/" + self["id"])
        if __debug__:
            if not dict_is_test(response_data["data"]):
                raise APIFailureException(
                    "API returned non-test for a test",
                    None,
                    response,
                    response_data,
                    self,
                )
        self.update(response_data["data"])
        delay = response.getheader("Retry-After")
        if not wait_for_completion or delay is None or retries <= 0:
            return
        delay = max(1, int(delay))
        self._sleep(delay)
        return self.fetch(wait_for_completion, retries - 1)

    def getreport(self):
        """Returns Report object for this test, if it is available.

        Note that this function does not *check* whether the test has actually
        completed since the last call to API.  For that, you should use
        method :meth:`fetch <Test.fetch>` first.

        Also note that even if report is *finished* (i.e. after
        :meth:`fetch(wait_for_completion=True) <Test.fetch>` returns), it's not
        guaranteed that it *completed successfully* - it could have finished
        with an error - for example, due to certificate or connection error.
        In that case, your test will have `status = "error"` attribute, and
        also `error` attribute explaining what went wrong.

        :rtype: :class:`Report` or None
        """
        if self._report is None:
            if "links" in self and "report" in self["links"]:
                self._report = Report._fromURL(self._requestor, self["links"]["report"], self._sleep)
        return self._report

    @classmethod
    def _fromURL(cls, requestor, url, sleep_function=time.sleep):
        """Given an URL, fetches it and returns an :class:`Test`

        Note that currently only URLs under requestor's base_url are supported
        """
        if url.startswith(requestor.base_url):
            url = url[len(requestor.base_url) :]
        # TODO: fetching from external URL
        (response, response_data) = requestor.request(url)
        if __debug__:
            if not dict_is_test(response_data["data"]):
                raise APIFailureException("API returned non-test for a test", None, response, response_data)
        return Test(requestor, response_data["data"], sleep_function)


class Report(Object):
    @classmethod
    def _fromURL(cls, requestor, url, sleep_function=time.sleep):
        """Given an URL, fetches it and returns an :class:`Report`

        Note that currently only URLs under requestor's base_url are supported
        """
        if url.startswith(requestor.base_url):
            url = url[len(requestor.base_url) :]
        # TODO: fetching from external URL
        (response, response_data) = requestor.request(url)
        if __debug__:
            if not dict_is_report(response_data["data"]):
                raise APIFailureException(
                    "API returned non-report for a report",
                    None,
                    response,
                    response_data,
                )
        return Report(requestor, response_data["data"], sleep_function)

    def delete(self):
        """Delete the report.

        Note that after executing this method, all other methods should error
        with a "404 Report not found" error.
        """
        self._requestor.request("reports/" + self["id"], method="DELETE", return_data=False)

    def retest(self):
        """Retest the report.

        :returns: a new instance of :class:`Test` corresponding to a new running test.

        :rtype: Test
        """
        (response, response_data) = self._requestor.request("reports/%s/retest" % self["id"], method="POST")
        # TODO: this is same as when starting a test
        if __debug__:
            if not dict_is_test(response_data["data"]):
                raise APIFailureException(
                    "API returned non-test for a retest",
                    None,
                    response,
                    response_data,
                )
        test = Test(self._requestor, response_data["data"], self._sleep)
        return test

    def getresource(self, name, destination=None):
        """Get a report resource (such as a PDF file, video, etc)

        Depending on the value of ``destination`` parameter, it might be saved
        to a file, a file-like object, or returned to the caller.  Be careful
        with the latter in case a file is too big, though.

        :param str name:
            Name of the desired resource. It can be either *key* of
            ``report["links"]`` dict (such as "report_pdf", "lighthouse", or
            "har"), or a *filename* to be appended to URL (such as
            "report.pdf", "lighthouse.json", or "net.har").  List of possible
            *keys* you can find by inspecting the ``report["links"]`` dict, and
            full list of possible *filenames* - at the GTmetrix API
            documentation:
            <https://gtmetrix.com/api/docs/2.0/#api-report-resource>

        :param destination:
            Where to save the downloaded resource. If it is ``None``, then
            resource is completely downloaded into RAM and returned to the
            caller.  If it is a string, then the resource is saved into a file
            with that name.  If it is a file-like object, then
            :func:`shutil.copyfileobj` is used to copy the resource into that
            object.
        :type destination: None or str or a file-like object

        """
        if name in self["links"]:
            url = self["links"][name]
            if url.startswith(self._requestor.base_url):
                url = url[len(self._requestor.base_url) :]
            # TODO: fetching from external URL
        else:
            url = "reports/%s/resources/%s" % (self["id"], name)
        (response, response_data) = self._requestor.request(
            url,
            follow_redirects=True,
            return_data=False,
        )
        if destination is None:
            data = b""
            chunk = response.read()
            while chunk:
                data += chunk
                chunk = response.read()
            return data
        elif isinstance(destination, str):
            with open(destination, "wb") as destination_file:
                shutil.copyfileobj(response, destination_file)
        else:
            shutil.copyfileobj(response, destination)
