import json
import shutil
import time
import urllib.request


class BaseGTmetrixAPIException(Exception):
    """Base class for all exceptions."""

    def __init__(self, request, response, data, extra=None):
        self.request = request
        self.response = response
        self.data = data
        self.extra = extra


class GTmetrixAPIFailureException(BaseGTmetrixAPIException):
    """API returned unexpected result."""

    def __init__(self, message, request, response, data, extra=None):
        super().__init__(request, response, data, extra)
        self.message = message


class GTmetrixAPIErrorException(BaseGTmetrixAPIException):
    """API returned an error."""

    pass


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
        self._redirect_opener = urllib.request.build_opener(auth_handler)
        self._sleep = sleep_function

    def _plain_request(self, url, opener, **kwargs):
        # method=None, data=None, headers={}, valid_status=None, valid_statuses=None, return_data=True, require_data=True, return_json=True
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
            if "valid_statuses" in kwargs and response.status not in kwargs["valid_statuses"]:
                raise GTmetrixAPIFailureException(
                    ("API returned invalid status: %s" % response.status),
                    request,
                    response,
                    response.read(),
                )
        if not kwargs.get("return_data", True):
            return (response, None)
        data = response.read()
        # TODO: retry reads if you can't read the whole response in one go
        if len(data) == 0:
            if kwargs.get("require_data", True):
                raise GTmetrixAPIFailureException("API returned empty response", request, response, data)
            else:
                return (response, None)
        # if not kwargs.get("return_json", True):
        #     return (response, data)
        try:
            json_data = json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeError) as e:
            raise GTmetrixAPIFailureException("API returned unparsable JSON", request, response, data) from e
        if "errors" in json_data:
            if __debug__:
                if not isinstance(json_data["errors"], list):
                    raise GTmetrixAPIFailureException("API returned non-list of errors", request, response, json_data)
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

    def request(self, url, follow_redirects=False, data=None, **kwargs):
        if follow_redirects:
            opener = self._redirect_opener
        else:
            opener = self._opener
        return self._retry_request(url, opener=opener, data=data, **kwargs)


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


def dict_is_user(data):
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
                self._report = Report.fromURL(self._requestor, self["links"]["report"], self._sleep)
        return self._report

    @classmethod
    def fromURL(cls, requestor, url, sleep_function=time.sleep):
        if url.startswith(requestor.base_url):
            url = url[len(requestor.base_url) :]
        # TODO: fetching from external URL
        (response, response_data) = requestor.request(url)
        if __debug__:
            if not "data" in response_data:
                raise GTmetrixAPIFailureException("API returned no data for a test", None, response, response_data)
            if not dict_is_test(response_data["data"]):
                raise GTmetrixAPIFailureException("API returned non-test for a test", None, response, response_data)
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
                raise GTmetrixAPIFailureException("API returned no data for a report", None, response, response_data)
            if not dict_is_report(response_data["data"]):
                raise GTmetrixAPIFailureException(
                    "API returned non-report for a report",
                    None,
                    response,
                    response_data,
                )
        return Report(requestor, response_data["data"], sleep_function)

    def delete(self):
        self._requestor.request("reports/" + self["id"], method="DELETE", return_data=False)

    def retest(self):
        (response, response_data) = self._requestor.request("reports/%s/retest" % self["id"], method="POST")
        # TODO: this is same as when starting a test
        if __debug__:
            if not "data" in response_data:
                raise GTmetrixAPIFailureException(
                    "API returned no data for a retest",
                    None,
                    response,
                    response_data,
                )
            if not dict_is_test(response_data["data"]):
                raise GTmetrixAPIFailureException(
                    "API returned non-test for a retest",
                    None,
                    response,
                    response_data,
                )
        test = Test(self._requestor, response_data["data"])
        return test

    def getresource(self, name, destination=None):
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


class Interface:
    def __init__(
        self,
        api_key,
        base_url="https://gtmetrix.com/api/2.0/",
        sleep_function=time.sleep,
    ):
        self._requestor = Requestor(api_key, base_url, sleep_function)

    def start_test(self, url, **attributes):
        """Start a Test"""
        attributes["url"] = url
        data = {"type": "test", "attributes": attributes}
        (response, response_data) = self._requestor.request(
            "tests",
            data={"data": data},
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
        test = Test(self._requestor, response_data["data"])
        # TODO: do something with credits_left and credits_used
        return test

    def list_tests(self, sort=None, filter=None, page_number=0):
        """`sort` is a string, one of "created", "started", "finished",
            optionally prefixed with "-".
        `filter` is a dict of key/value pairs,
            where key is one of "state, created, started, finished, browser, location",
                optionally postfixed with one of ":eq, :lt, :lte, :gt, :gte"
            and value is, well, value (string or number).
        TODO: examples would be good.
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
        tests = [Test(self._requestor, test_data) for test_data in response_data["data"]]
        return tests

    def status(self):
        (response, response_data) = self._requestor.request("status")
        if __debug__:
            if not "data" in response_data:
                raise GTmetrixAPIFailureException("API returned no data for status", None, response, response_data)
            if not dict_is_user(response_data["data"]):
                raise GTmetrixAPIFailureException(
                    "API returned non-user for status",
                    None,
                    response,
                    response_data,
                )
        return response_data["data"]
