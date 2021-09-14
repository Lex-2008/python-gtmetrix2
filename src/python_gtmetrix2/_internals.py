# python-gtmetrix2
#
# Internal details
# ================
"""
.. warning::

   Contents of this module considered to be internal and therefore may change
   without warning. If your code uses something in this module, please let the
   developer know about it so we could consider adding it to public API.

Overview
--------

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

Reference
---------
"""
import json
import time
import urllib.request

from .exceptions import *


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
        # NOTE: different openers must use different auth_handlers
        auth_handler1 = urllib.request.HTTPBasicAuthHandler(password_manager)
        auth_handler2 = urllib.request.HTTPBasicAuthHandler(password_manager)

        self._opener = urllib.request.build_opener(auth_handler1, NoRedirect)
        self._redirect_opener = urllib.request.build_opener(auth_handler2)
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
                    raise APIErrorFailureException("API returned non-list of errors", request, response, json_data)
                if len(json_data["errors"]) < 1:
                    raise APIErrorFailureException("API returned empty list of errors", request, response, json_data)
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
        """Wrapper around self._plain_request which catches "429 Rate limit exceeded" errors
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
