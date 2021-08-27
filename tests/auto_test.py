import time
import tempfile
import urllib.request

import pytest
from pytest_httpserver import HTTPServer

from src import python_gtmetrix2


class Sleeper:
    def __init__(self, httpserver):
        self.httpserver = httpserver

    def sleep(self, time):
        response = urllib.request.urlopen(self.httpserver.url_for("sleep%d" % time))


def test_requestor_positive(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))

    # test that simple response comes through
    httpserver.expect_oneshot_request("/oneshot").respond_with_json({"data": {"value": 42}})
    with httpserver.wait():
        (response, response_data) = requestor.request("oneshot")
    assert response_data["data"]["value"] == 42

    # test that proper error response raises proper exception
    httpserver.expect_oneshot_request("/oneshot").respond_with_json(
        {"errors": [{"status": "404", "code": "E404", "title": "Not Found"}]}, status=404
    )
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIErrorException) as e:
            requestor.request("/oneshot")
        assert e.value.data["errors"][0]["status"] == "404"


def test_requestor_negative(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))

    httpserver.expect_oneshot_request("/oneshot").respond_with_data("")
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="empty response"):
            requestor.request("/oneshot")

    httpserver.expect_oneshot_request("/oneshot").respond_with_data("{")
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="unparse?able"):
            requestor.request("/oneshot")

    httpserver.expect_oneshot_request("/oneshot").respond_with_json({"errors": 42})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="errors"):
            requestor.request("/oneshot")

    httpserver.expect_oneshot_request("/oneshot").respond_with_data("{}")
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="no data"):
            requestor.request("/oneshot")


def test_requestor_negative_error(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))

    httpserver.expect_oneshot_request("/oneshot").respond_with_data("", status=400)
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIErrorFailureException, match="empty response"):
            requestor.request("/oneshot")

    httpserver.expect_oneshot_request("/oneshot").respond_with_data("{", status=400)
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIErrorFailureException, match="unparse?able"):
            requestor.request("/oneshot")

    httpserver.expect_oneshot_request("/oneshot").respond_with_data("{}", status=400)
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIErrorFailureException, match="no errors"):
            requestor.request("/oneshot")

    httpserver.expect_oneshot_request("/oneshot").respond_with_json({"errors": 42}, status=400)
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIErrorFailureException, match="non-list"):
            requestor.request("/oneshot")

    httpserver.expect_oneshot_request("/oneshot").respond_with_json({"errors": []}, status=400)
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIErrorFailureException, match="empty list"):
            requestor.request("/oneshot")

    # first error is correct, second is empty array
    httpserver.expect_oneshot_request("/oneshot").respond_with_json(
        {"errors": [{"status": "404", "code": "E404", "title": "Not Found"}, {}]}, status=400
    )
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIErrorFailureException, match="non-error"):
            requestor.request("/oneshot")


def test_requestor_retry(httpserver: HTTPServer):
    sleeper = Sleeper(httpserver)
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""), sleeper.sleep)

    httpserver.expect_ordered_request("/ordered").respond_with_json(
        {"errors": [{"status": "429", "code": "E42900", "title": "Wait 3 sec"}]}, status=429
    )
    httpserver.expect_ordered_request("/sleep3").respond_with_data("")
    httpserver.expect_ordered_request("/ordered").respond_with_json({"data": {"value": 42}})
    with httpserver.wait():
        (response, response_data) = requestor.request("ordered")
    assert response_data["data"]["value"] == 42

    httpserver.expect_ordered_request("/ordered").respond_with_json(
        {"errors": [{"status": "429", "code": "E42901", "title": "Wait 1 sec"}]},
        headers={"X-RateLimit-Reset": "1"},
        status=429,
    )
    httpserver.expect_ordered_request("/sleep1").respond_with_data("")
    httpserver.expect_ordered_request("/ordered").respond_with_json({"data": {"value": 42}})
    with httpserver.wait():
        (response, response_data) = requestor.request("ordered")
    assert response_data["data"]["value"] == 42

    httpserver.expect_ordered_request("/ordered").respond_with_json(
        {"errors": [{"status": "429", "code": "E42901", "title": "Wait 1 sec"}]},
        headers={"X-RateLimit-Reset": "1"},
        status=429,
    )
    httpserver.expect_ordered_request("/sleep1").respond_with_data("")
    httpserver.expect_ordered_request("/ordered").respond_with_json(
        {"errors": [{"status": "429", "code": "E42901", "title": "Wait 1 sec"}]},
        headers={"X-RateLimit-Reset": "1"},
        status=429,
    )
    httpserver.expect_ordered_request("/sleep1").respond_with_data("")
    httpserver.expect_ordered_request("/ordered").respond_with_json(
        {"errors": [{"status": "429", "code": "E42901", "title": "Wait 1 sec"}]},
        headers={"X-RateLimit-Reset": "1"},
        status=429,
    )
    httpserver.expect_ordered_request("/sleep1").respond_with_data("")
    httpserver.expect_ordered_request("/ordered").respond_with_json(
        {"errors": [{"status": "429", "code": "E42901", "title": "Wait 1 sec"}]},
        headers={"X-RateLimit-Reset": "1"},
        status=429,
    )
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIErrorException) as e:
            requestor.request("ordered", retries=3)
        assert e.value.data["errors"][0]["code"] == "E42901"

    httpserver.expect_oneshot_request("/oneshot").respond_with_json(
        {"errors": [{"status": "429", "code": "E42902", "title": "unknown code"}]}, status=429
    )
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIErrorException) as e:
            requestor.request("/oneshot")
        assert e.value.data["errors"][0]["code"] == "E42902"


def test_test_fetch(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))

    test_json = {"data": {"type": "test", "id": "a", "attributes": {"n": 1}}}
    test = python_gtmetrix2.Test(requestor, test_json["data"])
    assert test["attributes"]["n"] == 1

    test_json["data"]["attributes"]["n"] = 2
    # should not wait, even when header present
    httpserver.expect_oneshot_request("/tests/a").respond_with_json(
        test_json, status=200, headers={"Retry-After": "1"}
    )
    with httpserver.wait():
        test.fetch()
    assert test["attributes"]["n"] == 2

    test_json["data"]["attributes"]["n"] = 3
    # should not wait, even when wait_for_complete=True passed
    httpserver.expect_oneshot_request("/tests/a").respond_with_json(test_json, status=200)
    with httpserver.wait():
        test.fetch(wait_for_complete=True)
    assert test["attributes"]["n"] == 3

    test_json["data"]["attributes"]["n"] = 4
    # should not follow redirect, even when header present
    httpserver.expect_ordered_request("/tests/a").respond_with_json(
        test_json, status=303, headers={"Location": "/reports/b"}
    )
    with httpserver.wait():
        test.fetch()
    assert test["type"] == "test"
    assert test["attributes"]["n"] == 4


def test_test_fetch_wait(httpserver: HTTPServer):
    sleeper = Sleeper(httpserver)
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""), sleeper.sleep)

    test_json = {"data": {"type": "test", "id": "a", "attributes": {"n": 1}}}
    test = python_gtmetrix2.Test(requestor, test_json["data"], sleeper.sleep)
    assert test["attributes"]["n"] == 1

    test_json["data"]["attributes"]["n"] = 2
    httpserver.expect_ordered_request("/tests/a").respond_with_json(
        test_json, status=200, headers={"Retry-After": "1"}
    )
    httpserver.expect_ordered_request("/sleep1").respond_with_data("")
    test_json["data"]["attributes"]["n"] = 3
    httpserver.expect_ordered_request("/tests/a").respond_with_json(
        test_json, status=303, headers={"Location": "/reports/b"}
    )
    with httpserver.wait():
        test.fetch(True)
    assert test["type"] == "test"
    assert test["attributes"]["n"] == 3

    test_json["data"]["attributes"]["n"] = 5
    httpserver.expect_ordered_request("/tests/a").respond_with_json(
        test_json, status=200, headers={"Retry-After": "1"}
    )
    httpserver.expect_ordered_request("/sleep1").respond_with_data("")
    test_json["data"]["attributes"]["n"] = 6
    httpserver.expect_ordered_request("/tests/a").respond_with_json(
        test_json, status=200, headers={"Retry-After": "1"}
    )
    httpserver.expect_ordered_request("/sleep1").respond_with_data("")
    test_json["data"]["attributes"]["n"] = 7
    httpserver.expect_ordered_request("/tests/a").respond_with_json(
        test_json, status=200, headers={"Retry-After": "1"}
    )
    httpserver.expect_ordered_request("/sleep1").respond_with_data("")
    test_json["data"]["attributes"]["n"] = 8
    httpserver.expect_ordered_request("/tests/a").respond_with_json(
        test_json, status=200, headers={"Retry-After": "1"}
    )
    with httpserver.wait():
        test.fetch(True, retries=3)
    assert test["type"] == "test"
    assert test["attributes"]["n"] == 8


def test_test_fetch_negative(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))

    test_json = {"data": {"type": "test", "id": "a", "attributes": {"n": 1}}}
    test = python_gtmetrix2.Test(requestor, {"id": "a"})

    httpserver.expect_oneshot_request("/tests/a").respond_with_json({})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="no data"):
            test.fetch()

    httpserver.expect_oneshot_request("/tests/a").respond_with_json({"data": {}})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="non-test"):
            test.fetch()


def test_test_getreport(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))

    test_json = {
        "type": "test",
        "id": "a",
        "attributes": {},
        "links": {"report": httpserver.url_for("report1")},
    }
    report_json = {"type": "report", "id": "b", "attributes": {"n": 1}, "links": {}}
    test = python_gtmetrix2.Test(requestor, test_json)
    httpserver.expect_oneshot_request("/report1").respond_with_json({"data": report_json})
    with httpserver.wait():
        report = test.getreport()
    assert isinstance(report, python_gtmetrix2.Report)
    assert report["attributes"]["n"] == 1


def test_test_fromurl_positive(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))
    test_json = {"type": "test", "id": "a", "attributes": {"n": 1}}
    httpserver.expect_oneshot_request("/oneshot").respond_with_json({"data": test_json})
    with httpserver.wait():
        test = python_gtmetrix2.Test.fromURL(requestor, httpserver.url_for("oneshot"))
    assert isinstance(test, python_gtmetrix2.Test)
    assert test["attributes"]["n"] == 1


def test_test_fromurl_negative(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))

    httpserver.expect_oneshot_request("/oneshot").respond_with_json({})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="no data"):
            test = python_gtmetrix2.Test.fromURL(requestor, httpserver.url_for("oneshot"))

    httpserver.expect_oneshot_request("/oneshot").respond_with_json({"data": 42})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="non-test"):
            test = python_gtmetrix2.Test.fromURL(requestor, httpserver.url_for("oneshot"))


def test_report_fromurl_positive(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))
    report_json = {"type": "report", "id": "b", "attributes": {"n": 1}, "links": {}}
    httpserver.expect_oneshot_request("/report1").respond_with_json({"data": report_json})
    with httpserver.wait():
        report = python_gtmetrix2.Report.fromURL(requestor, httpserver.url_for("report1"))
    assert isinstance(report, python_gtmetrix2.Report)
    assert report["attributes"]["n"] == 1


def test_report_fromurl_negative(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))

    httpserver.expect_oneshot_request("/oneshot").respond_with_json({})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="no data"):
            report = python_gtmetrix2.Report.fromURL(requestor, httpserver.url_for("oneshot"))

    httpserver.expect_oneshot_request("/oneshot").respond_with_json({"data": 42})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="non-report"):
            report = python_gtmetrix2.Report.fromURL(requestor, httpserver.url_for("oneshot"))


def test_report_delete(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))
    report_json = {"type": "report", "id": "b", "attributes": {"n": 1}, "links": {}}
    report = python_gtmetrix2.Report(requestor, report_json)
    httpserver.expect_oneshot_request("/reports/b", method="DELETE").respond_with_data("")
    with httpserver.wait():
        report.delete()


def test_report_retest_positive(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))
    report_json = {"type": "report", "id": "b", "attributes": {"n": 1}, "links": {}}
    test_json = {
        "data": {
            "type": "test",
            "id": "a",
            "attributes": {"n": 2},
        }
    }
    report = python_gtmetrix2.Report(requestor, report_json)
    httpserver.expect_oneshot_request("/reports/b/retest", method="POST").respond_with_json(test_json)
    with httpserver.wait():
        test = report.retest()
    assert test["type"] == "test"
    assert test["attributes"]["n"] == 2


def test_report_retest_negative(httpserver: HTTPServer):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))
    report_json = {"type": "report", "id": "b", "attributes": {"n": 1}, "links": {}}
    report = python_gtmetrix2.Report(requestor, report_json)
    httpserver.expect_oneshot_request("/reports/b/retest", method="POST").respond_with_json({})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="no data"):
            report.retest()

    httpserver.expect_oneshot_request("/reports/b/retest", method="POST").respond_with_json({"data": 12})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="non-test"):
            report.retest()


def test_report_getresource(httpserver: HTTPServer, tmp_path):
    requestor = python_gtmetrix2.Requestor("aaa", httpserver.url_for(""))
    report_json = {"type": "report", "id": "b", "attributes": {"n": 1}, "links": {}}
    report = python_gtmetrix2.Report(requestor, report_json)

    httpserver.expect_oneshot_request("/reports/b/resources/a").respond_with_data("x")
    with httpserver.wait():
        result = report.getresource("a")
    assert result == b"x"

    httpserver.expect_oneshot_request("/reports/b/resources/a").respond_with_data("x")
    with httpserver.wait():
        with tempfile.TemporaryFile(dir=str(tmp_path)) as fp:
            report.getresource("a", fp)
            fp.seek(0)
            result = fp.read()
    assert result == b"x"

    httpserver.expect_oneshot_request("/reports/b/resources/a").respond_with_data("x")
    with httpserver.wait():
        (_, tmpfile) = tempfile.mkstemp(dir=str(tmp_path))
        tmpfile = str(tmpfile)
        report.getresource("a", tmpfile)
        with open(tmpfile) as fp:
            fp.seek(0)
            result = fp.read()
    assert result == "x"


def test_interface_start_positive(httpserver: HTTPServer):
    interface = python_gtmetrix2.Interface("aaa", httpserver.url_for(""))
    httpserver.expect_oneshot_request(
        "/tests",
        method="POST",
        headers={"Content-Type": "application/vnd.api+json"},
        json={
            "data": {
                "type": "test",
                "attributes": {"url": "example.com", "key": "value"},
            }
        },
    ).respond_with_json(
        {
            "data": {
                "type": "test",
                "id": "a",
                "attributes": {"source": "api"},
            }
        },
        status=202,
        headers={"Location": httpserver.url_for("/tests/a")},
    )
    with httpserver.wait():
        test = interface.start_test("example.com", key="value")
    assert test["type"] == "test"
    assert test["attributes"]["source"] == "api"


def test_interface_start_negative(httpserver: HTTPServer):
    interface = python_gtmetrix2.Interface("aaa", httpserver.url_for(""))

    httpserver.expect_oneshot_request("/tests", method="POST").respond_with_json({})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="no data"):
            interface.start_test("example.com")

    httpserver.expect_oneshot_request("/tests", method="POST").respond_with_json({"data": 12})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="non-test"):
            interface.start_test("example.com")


def test_interface_list_positive(httpserver: HTTPServer):
    interface = python_gtmetrix2.Interface("aaa", httpserver.url_for(""))
    httpserver.expect_oneshot_request("/tests").respond_with_json(
        {"data": [{"type": "test", "id": "a", "attributes": {}}]}
    )
    with httpserver.wait():
        tests = interface.list_tests()
    assert isinstance(tests, list)
    assert len(tests) == 1
    assert all((isinstance(test, python_gtmetrix2.Test) for test in tests))


def test_interface_list_args(httpserver: HTTPServer):
    interface = python_gtmetrix2.Interface("aaa", httpserver.url_for(""))

    httpserver.expect_oneshot_request("/tests", query_string="sort=this").respond_with_json({"data": []})
    with httpserver.wait():
        tests = interface.list_tests(sort="this")
    assert isinstance(tests, list)
    assert len(tests) == 0

    httpserver.expect_oneshot_request("/tests", query_string="filter[this]=that").respond_with_json({"data": []})
    with httpserver.wait():
        tests = interface.list_tests(filter={"this": "that"})
    assert isinstance(tests, list)
    assert len(tests) == 0

    httpserver.expect_oneshot_request(
        "/tests",
        query_string={
            "sort": "complex",
            "filter[this]": "that",
            "filter[key]": "value",
        },
    ).respond_with_json({"data": []})
    with httpserver.wait():
        tests = interface.list_tests(sort="complex", filter={"this": "that", "key": "value"})
    assert isinstance(tests, list)
    assert len(tests) == 0


def test_interface_list_negative(httpserver: HTTPServer):
    interface = python_gtmetrix2.Interface("aaa", httpserver.url_for(""))

    httpserver.expect_oneshot_request("/tests").respond_with_json({})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="no data"):
            interface.list_tests()

    httpserver.expect_oneshot_request("/tests").respond_with_json({"data": 12})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="non-list"):
            interface.list_tests()

    httpserver.expect_oneshot_request("/tests").respond_with_json(
        {"data": [{"type": "test", "id": "a", "attributes": {}}, {}]}
    )
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="non-test"):
            interface.list_tests()


def test_interface_status_positive(httpserver: HTTPServer):
    interface = python_gtmetrix2.Interface("aaa", httpserver.url_for(""))
    httpserver.expect_oneshot_request("/status").respond_with_json(
        {"data": {"type": "user", "id": "a", "attributes": {"api_credits": 1.2, "api_refill": 3}}}
    )
    with httpserver.wait():
        status = interface.status()
    assert isinstance(status, dict)
    assert status["type"] == "user"
    assert status["attributes"]["api_credits"] == 1.2
    assert status["attributes"]["api_refill"] == 3


def test_interface_status_negative(httpserver: HTTPServer):
    interface = python_gtmetrix2.Interface("aaa", httpserver.url_for(""))

    httpserver.expect_oneshot_request("/status").respond_with_json({})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="no data"):
            interface.status()

    httpserver.expect_oneshot_request("/status").respond_with_json({"data": 12})
    with httpserver.wait():
        with pytest.raises(python_gtmetrix2.GTmetrixAPIFailureException, match="non-user"):
            interface.status()
