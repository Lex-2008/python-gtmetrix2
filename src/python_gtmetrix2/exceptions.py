# python-gtmetrix2
#
# Exceptions
# ==========
"""
Overview
--------

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

Reference
---------
"""


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
