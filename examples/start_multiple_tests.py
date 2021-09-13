"""11
Start multiple tests
--------------------

Example which shows how to start multiple tests in parallel, wait for them to
finish, and fetch reports for tests that completed successfully.

Note that GTmetrix limits the number of tests you can run in parallel (2
concurrent tests on a Basic account, 8 concurrent tests on a PRO account).
This example does not impose any concurrency limits by itself, but instead
relies on GTmetrix API to reply with 429 HTTP error and retries.
"""

import sys
import json

import python_gtmetrix2


def main(api_key, urls):
    account = python_gtmetrix2.Account(api_key)

    print("=== starting tests ===")

    tests = []
    for url in urls:
        test = account.start_test(url)
        print(json.dumps(test))
        tests.append(test)

    print("=== wait for tests to finish ===")

    for test in tests:
        test.fetch(wait_for_completion=True)

    print("=== fetching report for each test ===")

    for test in tests:

        report = test.getreport()

        if report is None:
            print("No report for test %s" % test["id"])
        else:
            print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: %s api_key url..." % sys.argv[0])
        exit()

    api_key = sys.argv[1]
    urls = sys.argv[2:]

    main(api_key, urls)
