import sys
import json

import python_gtmetrix2


def main(api_key, urls):
    account = python_gtmetrix2.Account(api_key)

    print("=== starting tests ===")

    tests = [account.start_test(url) for url in urls]
    for test in tests:
        print(json.dumps(test))

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
