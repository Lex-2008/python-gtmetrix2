"""12
List recent tests
-----------------

Example which shows what can be done with result of :meth:`Account.list_tests` method.

You can either treat it as a JSON-like `dict` object, or use
:meth:`Test.getreport` function to get corresponding report, *if it exists*.
:class:`Report` is also a JSON-like `dict` object.
"""

import sys
import json

import python_gtmetrix2


def main(api_key):
    account = python_gtmetrix2.Account(api_key)

    print("=== fetching tests ===")

    tests = account.list_tests()

    if len(tests) == 0:
        print("No tests found! Note that only tests started within last 24 hours are available via this API.")
        return

    for test in tests:
        print(json.dumps(test, indent=2))

    print("=== fetching report for each test ===")

    for test in tests:

        report = test.getreport()

        if report is None:
            print("No report for test %s" % test["id"])
        else:
            print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: %s api_key" % sys.argv[0])
        exit()

    main(sys.argv[1])
