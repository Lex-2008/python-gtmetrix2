##### Base exceptions ####


class BaseGTmetrixAPIException(Exception):
    def __init__(self, request, response, data, extra=None):
        self.request = request
        self.response = response
        self.data = data
        self.extra = extra


class GTmetrixAPIFailureException(BaseGTmetrixAPIException):
    """API returned an error."""

    def __init__(self, message, request, response, data, extra=None):
        super().__init__(request, response, data, extra)
        self.message = message


class GTmetrixAPIErrorException(BaseGTmetrixAPIException):
    """API returned an error."""

    pass


import json
import urllib.request
import time

# TODO: __getattr__ to access entries within ["attributes"]
# TODO: test auth
# TODO: Interface.[Test/Report].from[ID/Slug/URL]('...')

# real API tests:
# delete report and fetch test
# delete test

# from https://stackoverflow.com/a/52086806
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Requestor:
    def __init__(self, api_key, base_url, sleep_function=time.sleep):
        self.base_url = base_url
        password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(realm=None, uri=base_url, user=api_key, passwd="")
        auth_handler = urllib.request.HTTPBasicAuthHandler(password_manager)

        self._opener = urllib.request.build_opener(auth_handler, NoRedirect)
        self._sleep = sleep_function

    def _plain_request(self, url, **kwargs):
        # method=None, data=None, headers={}, valid_status=None, valid_statuses=None, require_data=True):
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
            response = self._opener.open(request)
        except urllib.error.HTTPError as e:
            # https://docs.python.org/3/library/urllib.error.html#urllib.error.HTTPError
            # > Though being an exception (a subclass of URLError), an HTTPError
            # > can also function as a non-exceptional file-like return value
            # > (the same thing that urlopen() returns).
            # first seen at https://stackoverflow.com/a/52086806
            response = e
        if __debug__:
            # NOTE: in production, we don't check for status returned by API.
            # However, it might be helpful in CI tests
            if "valid_status" in kwargs:
                kwargs["valid_statuses"] = [kwargs["valid_status"]]
            if (
                "valid_statuses" in kwargs
                and response.status not in kwargs["valid_statuses"]
            ):
                raise GTmetrixAPIFailureException(
                    ("API returned invalid status: %s" % response.status),
                    request,
                    response,
                    response.read(),
                )
        data = response.read()
        if len(data) == 0:
            if kwargs.get("require_data", True):
                raise GTmetrixAPIFailureException(
                    "API returned empty response", request, response, data
                )
            else:
                return (response, None)
        try:
            json_data = json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeError) as e:
            raise GTmetrixAPIFailureException(
                "API returned unparsable JSON", request, response, data
            ) from e
        if "errors" in json_data:
            if __debug__:
                if not isinstance(json_data["errors"], list):
                    raise GTmetrixAPIFailureException(
                        "API returned non-list of errors", request, response, json_data
                    )
                if len(json_data["errors"]) < 1:
                    raise GTmetrixAPIFailureException(
                        "API returned empty list of errors",
                        request,
                        response,
                        json_data,
                    )
                if not all((dict_is_error(x) for x in json_data["errors"])):
                    raise GTmetrixAPIFailureException(
                        "API returned non-error in error list",
                        request,
                        response,
                        json_data,
                    )
            raise GTmetrixAPIErrorException(request, response, json_data)
        return (response, json_data)

    def _retry_request(self, url, retries=10, **kwargs):
        # rest of arguments are same as for _plain request
        try:
            return self._plain_request(url, **kwargs)
        except GTmetrixAPIErrorException as e:
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

    def request(self, url, data=None, **kwargs):
        return self._retry_request(url, data=data, **kwargs)


def dict_is_error(data):
    return (
        isinstance(data, dict)
        and "status" in data
        and "code" in data
        and "title" in data
    )
    # optionally, it can have "description" field


def dict_is_test(data):
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


class Object(dict):
    def __init__(self, requestor, data, sleep_function=time.sleep):
        super().__init__(**data)
        self._requestor = requestor
        self._sleep = sleep_function


class Test(Object):
    def __init__(self, requestor, data, sleep_function=time.sleep):
        super().__init__(requestor, data, sleep_function)
        self._report = None

    def fetch(self, wait_for_complete=False, retries=10):
        (response, response_data) = self._requestor.request("tests/" + self["id"])
        if __debug__:
            if not "data" in response_data:
                raise GTmetrixAPIFailureException(
                    "API returned no data for a test",
                    None,
                    response,
                    response_data,
                    self,
                )
            if not dict_is_test(response_data["data"]):
                raise GTmetrixAPIFailureException(
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
        if self._report is None:
            if "links" in self and "report" in self["links"]:
                self._report = Report.fromURL(
                    self._requestor, self["links"]["report"], self._sleep
                )
        return self._report

    @classmethod
    def fromURL(cls, requestor, url, sleep_function=time.sleep):
        if url.startswith(requestor.base_url):
            url = url[len(requestor.base_url) :]
        # TODO: fetching from external URL
        (response, response_data) = requestor.request(url)
        if __debug__:
            if not "data" in response_data:
                raise GTmetrixAPIFailureException(
                    "API returned no data for a test", None, response, response_data
                )
            if not dict_is_test(response_data["data"]):
                raise GTmetrixAPIFailureException(
                    "API returned non-test for a test", None, response, response_data
                )
        return Test(requestor, response_data["data"], sleep_function)


class Report(Object):
    @classmethod
    def fromURL(cls, requestor, url, sleep_function=time.sleep):
        if url.startswith(requestor.base_url):
            url = url[len(requestor.base_url) :]
        # TODO: fetching from external URL
        (response, response_data) = requestor.request(url)
        if __debug__:
            if not "data" in response_data:
                raise GTmetrixAPIFailureException(
                    "API returned no data for a report", None, response, response_data
                )
            if not dict_is_report(response_data["data"]):
                raise GTmetrixAPIFailureException(
                    "API returned non-report for a report",
                    None,
                    response,
                    response_data,
                )
        return Report(requestor, response_data["data"], sleep_function)


class Interface:
    def __init__(
        self,
        api_key,
        base_url="https://gtmetrix.com/api/2.0/",
        sleep_function=time.sleep,
    ):
        self.requestor = Requestor(api_key, base_url, sleep_function)

    def start_test(self, url, **attributes):
        """Start a Test"""
        attributes["url"] = url
        data = {"type": "test", "attributes": attributes}
        (response, response_data) = self.requestor.request(
            "tests",
            {"data": data},
            method="POST",
            headers={"Content-Type": "application/vnd.api+json"},
        )
        if __debug__:
            if not "data" in response_data:
                raise GTmetrixAPIFailureException(
                    "API returned no data for a started test",
                    None,
                    response,
                    response_data,
                )
            if not dict_is_test(response_data["data"]):
                raise GTmetrixAPIFailureException(
                    "API returned non-test for a started test",
                    None,
                    response,
                    response_data,
                )
        test = Test(self.requestor, response_data["data"])
        # TODO: do something with credits_left and credits_used
        return test

    def list_tests(self):
        # TODO: sort, filter, page(?)
        (response, response_data) = self.requestor.request("tests")
        # TODO: pagination
        if __debug__:
            if not "data" in response_data:
                raise GTmetrixAPIFailureException(
                    "API returned no data for a list of tests",
                    None,
                    response,
                    response_data,
                )
            if not isinstance(response_data["data"], list):
                raise GTmetrixAPIFailureException(
                    "API returned non-list for a list of tests",
                    None,
                    response,
                    response_data,
                )
            if not all((dict_is_test(test) for test in response_data["data"])):
                raise GTmetrixAPIFailureException(
                    "API returned non-test in a list of tests",
                    None,
                    response,
                    response_data,
                )
        tests = [Test(self.requestor, test_data) for test_data in response_data["data"]]
        return tests
