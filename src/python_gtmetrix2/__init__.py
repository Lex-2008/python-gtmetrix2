# python-gtmetrix2
#
# a Python client library for GTmetrix REST API v2.0 (hence 2 in the name).

# Library overview
# ================
"""
Primary classes
---------------

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

Exceptions
----------

Basically, there are two main exception classes:
:exc:`APIFailureException` and :exc:`APIErrorException`.

First of them (the "failure" one) happens when API server returns something
what was not expected by the library: for example, when library expects to
receive a JSON, but can't parse the response. Cases like this should not
happen outside of unittests, so if you encounter one - please file an issue.

Second one (the "error" one) happens when API server returns (properly
formatted) error response.  In that case, it is assumed that it was a problem
with how the library is used.  But if you disagree - please file an issue.

Both of these classes are based on the :exc:`BaseAPIException`, and has
the following attributes usually set: ``request``, ``response``, ``data``.
``request`` and ``response`` link to relevant instances of
:class:`urllib.request.Request`, :class:`http.client.HTTPResponse`, or
:class:`urllib.error.HTTPError`, if they were available at the moment when the
exception was raised. In addition to this, :exc:`APIFailureException`
has a ``message`` attribute, which contains a text description of the problem.

Also, there is a :exc:`APIErrorFailureException`, which is raised if
:exc:`APIFailureException` (i.e. unparsable or invalid JSON) happens.
It's a subclass of :class:`APIFailureException`, so you don't need to
care about it, unless you're interested in it.

Further details
---------------

All requests are made by the instance of :class:`Requestor` which is created by
the :class:`Account` class and is usually shared between all instances
created from it.

It also uses :class:`NoRedirect` to avoid redirections when API returns both
30x redirect code and actual data in response body.  It is important, for
example, when requesting data for a finished test (:meth:`Test.fetch`) - in
that case, we would like to store received data in the :class:`Test` object,
but by default Python will throw away received data and follow redirect.

There are four helper functions to check if received JSON represents a valid
:meth:`error <dict_is_error>`, :meth:`test <dict_is_test>`, :meth:`report
<dict_is_report>`, :meth:`user <dict_is_user>`.

:class:`Test` and :class:`Report` classes have a same parent class
:class:`Object`, which holds elements that are common to both of them
(basically, constructor and parent class)

Module reference
----------------

Sorry, due to ``sphinx.ext.autodoc`` limitations, there will be no more entries
in the sidebar TOC.
"""
import json
import shutil
import time
import urllib.request



class BaseAPIException(Exception):
    """Base class for all exceptions in this library.
    Passed parameter are available as attributes.

    :param request: Request which was sent to the API server, if available.
    :type request: :class:`urllib.request.Request` or None

    :param response: Response from the API server.
    :type response: :class:`http.client.HTTPResponse` or :class:`urllib.error.HTTPError`

    :param data: data received from the API server, if any.
    :type data: None, bytes or dict (in case it was parsed from JSON)

    :param extra: extra information, if available, defaults to None.
    """

    def __init__(self, request, response, data, extra=None):
        self.request = request
        self.response = response
        self.data = data
        self.extra = extra


class APIFailureException(BaseAPIException):
    """API server returned an unexpected response.

    There was a disagreement between API server and this library:
    server returned something what the library did not expect to receive.

    :param str message: text explaining the error.

    other parameters are same as for parent class :exc:`BaseAPIException`.
    """

    def __init__(self, message, *args):
        super().__init__(*args)
        self.message = message


class APIErrorFailureException(APIFailureException):
    """APIFailureException happened when processing an error response.

    Parameters are the same as for parent class :exc:`APIFailureException`.
    """

    pass


class APIErrorException(BaseAPIException):
    """API returned an error.

    Parameters are the same as for parent class :exc:`BaseAPIException`.

    You can inspect error details in the `data` attribute of this object,
    it usually looks like this:

    .. code-block:: json

        {
          "errors": [
            {
              "status": "405",
              "code": "E40500",
              "title": "HTTP method not allowed",
              "detail": "Method is not supported by the endpoint"
            }
          ]
        }
    """

    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Helper class for avoiding redirection on 30x responses.
    From https://stackoverflow.com/a/52086806
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Returns None to avoid redirection."""
        return None


class Requestor:
    """Class for making requests.

    It also manages authentication, optionally follows redirects,
    and retries on "429" responses.

    Note that usually objects of this class should not be instantiated
    directly - you can use methods of :class:`Account` class instead.

    Parameters are the same as for :class:`Account`
    """
    def __init__(self, api_key, base_url="https://gtmetrix.com/api/2.0/", sleep_function=time.sleep):
        self.base_url = base_url
        password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(realm=None, uri=base_url, user=api_key, passwd="")
        auth_handler = urllib.request.HTTPBasicAuthHandler(password_manager)

        self._opener = urllib.request.build_opener(auth_handler, NoRedirect)
        self._redirect_opener = urllib.request.build_opener(auth_handler)
        self._sleep = sleep_function

    def _plain_request(self, url, opener, **kwargs):
        """Core function that makes requests."""
        # method=None, data=None, headers={}, return_data=True
        data = kwargs.get("data", None)
        if isinstance(data, dict):
            data = json.dumps(data)
        if isinstance(data, str):
            data = data.encode()
        request = urllib.request.Request(
            self.base_url + url,
            data=data,
            headers=kwargs.get("headers", {}),
            method=kwargs.get("method", None),
        )
        try:
            response = opener.open(request)
            response_code = response.status  # HTTP code, like 200 or 404
        except urllib.error.HTTPError as e:
            # https://docs.python.org/3/library/urllib.error.html#urllib.error.HTTPError
            # > Though being an exception (a subclass of URLError), an HTTPError
            # > can also function as a non-exceptional file-like return value
            # > (the same thing that urlopen() returns).
            # first seen at https://stackoverflow.com/a/52086806
            response = e
            response_code = response.code  # HTTP code, like 200 or 404
        if response_code >= 400:
            # That's an error
            data = response.read()
            if __debug__ and len(data) == 0:
                raise APIErrorFailureException("API returned empty response", request, response, data)
            try:
                json_data = json.loads(data.decode())
            except (json.JSONDecodeError, UnicodeError) as e:
                raise APIErrorFailureException("API returned unparsable JSON", request, response, data) from e
            if __debug__:
                if "errors" not in json_data:
                    raise APIErrorFailureException(
                        "API returned no errors with an HTTP code 400 or over", request, response, json_data
                    )
                if not isinstance(json_data["errors"], list):
                    raise APIErrorFailureException(
                        "API returned non-list of errors", request, response, json_data
                    )
                if len(json_data["errors"]) < 1:
                    raise APIErrorFailureException(
                        "API returned empty list of errors", request, response, json_data
                    )
                if not all((dict_is_error(x) for x in json_data["errors"])):
                    raise APIErrorFailureException(
                        "API returned non-error in error list", request, response, json_data
                    )
            raise APIErrorException(request, response, json_data)
        if not kwargs.get("return_data", True):
            return (response, None)
        data = response.read()
        # TODO: retry reads until the one which returns nothing
        if __debug__ and len(data) == 0:
            raise APIFailureException("API returned empty response", request, response, data)
        try:
            json_data = json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeError) as e:
            raise APIFailureException("API returned unparsable JSON", request, response, data) from e
        if __debug__:
            if "errors" in json_data:
                raise APIFailureException(
                    "API returned errors with an HTTP code %s under 400" % response_code, request, response, json_data
                )
            if "data" not in json_data:
                raise APIFailureException("API returned no data", request, response, json_data)
        return (response, json_data)

    def _retry_request(self, url, retries=10, **kwargs):
        """ Wrapper around self._plain_request which catches "429 Rate limit exceeded" errors
        and retries after specified time, up to max retries.
        """
        # other parameters are same as for _plain_request
        try:
            return self._plain_request(url, **kwargs)
        except APIErrorException as e:
            for error in e.data["errors"]:
                if error["status"] != "429":
                    # we're interested only in 429
                    raise
                if error["code"] == "E42900":
                    # Too many tests pending (Please retry after your existing tests have completed)
                    # The recommended poll interval is 3 seconds.
                    delay = 3
                elif error["code"] == "E42901":
                    # Rate limit exceeded
                    # X-RateLimit-Reset contains # of Seconds remaining until the end of the current window
                    delay = e.response.getheader("X-RateLimit-Reset", 3)
                    delay = max(1, int(delay))
                    # TODO: error code E42901 but no ratelimit header - raise some exception instead of defaulting to 3?
                else:
                    raise
                if retries <= 0:
                    raise
                self._sleep(delay)
                return self._retry_request(url, retries - 1, **kwargs)

    def request(self, url, follow_redirects=False, data=None, **kwargs):
        """Make a request and return the response.

        :param str url: URL to request (base URL will be prepended)

        :param bool, optional follow_redirects:
            Whether to follow 30x redirects, defaults to False.

        :param data:
            data to send as request body (usually with a POST request),
            defaults to None
        :type data: dict (to be JSON-encoded), string or bytes, optional 

        :param str, optional method:
            method to use for request ("GET", "POST", etc.), defaults to None
            to let urllib to decide (POST if data is provided, GET otherwise)

        :param dict, optional headers:
            headers to send with the request, in format understood by urllib,
            defaults to {}

        :param int, optional retries:
            Number of times to retry on "429 Rate limit exceeded" responses,
            defaults to 10

        :param bool, optional return_data:
            whether this function should read() the response, parse it as JSON,
            validate it (check that it's a dict and has a "data" key), and
            return that JSON - **or** if it should let the caller deal with it.
            Latter is useful for API calls which return files instead of JSON.

        :returns: Tuple of 2 elements: response object and response data.
            When API returns HTTP status code in [200..299] range, "response
            object" is an instance of :class:`http.client.HTTPResponse`.
            However, when API returns code 30x, Python considers it an error,
            so "response object" is an instance of
            :class:`urllib.error.HTTPError` instead.  Second element of the
            returned tuple is parsed JSON (:class:`dict`), *unless*
            `return_data` parameter was `False`.  In latter case, it's
            responsibility of the caller to call `read` method on the response
            object (conveniently, both types of returned objects support it).

        :rtype: tuple(http.client.HTTPResponse or urllib.error.HTTPError, dict or None)
        """
        if follow_redirects:
            opener = self._redirect_opener
        else:
            opener = self._opener
        return self._retry_request(url, opener=opener, data=data, **kwargs)


def dict_is_error(data):
    """helper function to check whether passed argument is a proper :class:`dict` object describing an error.

    :param dict data: value to check
    :rtype: bool
    """
    return (
        isinstance(data, dict)
        and "status" in data
        and "code" in data
        and "title" in data
    )
    # optionally, it can have "description" field


def dict_is_test(data):
    """helper function to check whether passed argument is a proper :class:`dict` object describing a test.

    :param dict data: value to check
    :rtype: bool
    """
    return (
        isinstance(data, dict)
        and "type" in data
        and data["type"] == "test"
        and "id" in data
        and "attributes" in data
        and isinstance(data["attributes"], dict)
    )
    # optionally, it can have "links" dict


def dict_is_report(data):
    """helper function to check whether passed argument is a proper :class:`dict` object describing a report.

    :param dict data: value to check
    :rtype: bool
    """
    return (
        isinstance(data, dict)
        and "type" in data
        and data["type"] == "report"
        and "id" in data
        and "attributes" in data
        and isinstance(data["attributes"], dict)
        and "links" in data
        and isinstance(data["links"], dict)
    )


def dict_is_user(data):
    """helper function to check whether passed argument is a proper :class:`dict` object describing a user.

    :param dict data: value to check
    :rtype: bool
    """
    return (
        isinstance(data, dict)
        and "type" in data
        and data["type"] == "user"
        and "id" in data
        and "attributes" in data
        and isinstance(data["attributes"], dict)
        and "api_credits" in data["attributes"]
        and "api_refill" in data["attributes"]
    )


class Object(dict):
    """Base class for :class:`Test` and :class:`Report` classes.

    Note that usually objects of these classes should not be instantiated
    directly - you can use methods of :class:`Account` class instead.

    Also note that since they are descendants of the :class:`dict`, you can
    simply :func:`json.dumps` them to inspect their internals.

    :param Requestor requestor:
        Requestor object to use for requests made by this object

    :param dict data:
        initial data. Note that it is responsibility of the caller to ensure
        that it contains valid data (passes respective `dict_is_*` check).

    :param method, optional sleep_function:
        the function to execute when waiting between retries (after receiving a
        "429" response) - useful for testing, or if someone wants to add some
        logging or notification of a delayed request, defaults to
        :func:`time.sleep`
    """
    def __init__(self, requestor, data, sleep_function=time.sleep):
        super().__init__(**data)
        self._requestor = requestor
        self._sleep = sleep_function


class Test(Object):
    _report = None

    def fetch(self, wait_for_complete=False, retries=10):
        """Ask API server for updated data regarding this test.

        :param bool, optional wait_for_complete: 
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
        if not wait_for_complete or delay is None or retries <= 0:
            return
        delay = max(1, int(delay))
        self._sleep(delay)
        return self.fetch(wait_for_complete, retries - 1)

    def getreport(self):
        """Returns Report object for this test, if it is available.

        Note that this function does not *check* whether the test has actually
        completed since the last call to API.  For that, you should use
        method :meth:`fetch <Test.fetch>` first.

        Also note that even if report is *finished* (i.e. after
        :meth:`fetch(wait_for_complete=True) <Test.fetch>` returns), it's not
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
            Name of the desired resource.
            You can find full list at the GTmetrix API documentation:
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
        (response, response_data) = self._requestor.request(
            "reports/%s/resources/%s" % (self["id"], name),
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

    def start_test(self, url:str, **attributes) -> Test:
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
        call :meth:`test.fetch(wait_for_complete=True) <Test.fetch>` after
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
