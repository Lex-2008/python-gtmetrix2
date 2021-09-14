"""21
Operations on report
--------------------

Example which shows some possible uses of report:

    * You can treat it as a JSON-like `dict` object and access any properties you want

    * You can request report to be deleted or retested

    * You can download a single report resource (such as a PDF version)

Also, this example demonstrates how you can work with JSON resources, like a har file.

Note how it uses :meth:`Account.reportFromId` method to get report from its ID.
When running examples, you can get report ID from "links.report" attribute of
the test object (note that it points to the whole report URL, and the report ID
is the part which comes after `/reports/` part), or from report's `id`
attribute.

When using this library, you can also use :meth:`Test.getreport` method to get
report object for a specific test object.
"""

import sys
import json

import python_gtmetrix2

def main(api_key, report_id, operation="print", *args):
    """Usage: %s api_key report_id [operation]
    or: %s api_key report_id getresource resource [filename]

    where operation is one of: print (default), delete, retest, size, getresource

    getresource operation requires one extra argument: what resource to get,
    and one optional: filename where to save it. If filename is not provided,
    resource is printed to stdout.
    """

    account = python_gtmetrix2.Account(api_key)
    report = account.reportFromId(report_id)

    if operation == "print":
        print(json.dumps(report, indent=2))
        # print(report["attributes"]["first_contentful_paint"])

    elif operation == "delete":
        report.delete()
        print("Report deleted.")

    elif operation == "retest":
        test = report.retest()
        print("new test:")
        print(json.dumps(test, indent=2))

    elif operation == "getresource":
        if len(args) not in [1, 2]:
            print("Usage: %s api_key report_id getresource resource [filename]" % sys.argv[0])
            print("If filename is not provided, resource is printed to stdout.")
            exit()
        getresource(report, *args)

    elif operation == "size":
        har = json.loads(report.getresource("net.har").decode())
        size_bytes = summarizeHar(har)
        size_kb = size_bytes/1024
        size_mb = size_kb/1024
        print("Total size of all resources, uncompressed: %d bytes = %.1f kb = %.1f MB" % (size_bytes, size_kb, size_mb))

    else:
        print("Usage: %s api_key report_id [operation]" % sys.argv[0])
        print("or: %s api_key report_id getresource resource [filename]" % sys.argv[0])
        print("where operation is one of: print (default), delete, retest, size, getresource")


def getresource(report, resource, filename=sys.stdout.buffer):
    """Gets report resource and saves it to filename (stdout by default)"""
    report.getresource(resource, filename)


def summarizeHar(har):
    """Given a har file (parsed json object), returns total size of all responses, in bytes."""
    return sum((entry["response"]["content"]["size"] for entry in har["log"]["entries"]))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(main.__doc__ % (sys.argv[0], sys.argv[0]))
        exit()

    main(*sys.argv[1:])
