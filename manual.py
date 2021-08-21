import sys
import json

import python_gtmetrix2

if len(sys.argv) < 2:
    print("Usage: %s api_key [url]..." % sys.argv[0])
    exit()

api_key = sys.argv[1]
urls = sys.argv[2:]

interface = python_gtmetrix2.Interface(api_key)

tests = interface.list_tests()
for test in tests:
    print(json.dumps(test))

print("old reports")

reports = [test.getreport() for test in tests]
for report in reports:
    print(json.dumps(report))

print("start testing")

tests = [interface.start_test(url) for url in urls]
for test in tests:
    print(json.dumps(test))

print("wait for tests to finish")

for test in tests:
    test.fetch(True)

print("new reports")

reports = [test.getreport() for test in tests]
for report in reports:
    print(json.dumps(report))
