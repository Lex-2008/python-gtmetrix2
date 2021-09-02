import sys
import json

import python_gtmetrix2


def main(api_key, report_id, operation="print", *args):
    account = python_gtmetrix2.Account(api_key)

    report = account.reportFromId(report_id)

    if operation == "print":
        print(json.dumps(report, indent=2))
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
    report.getresource(resource, filename)


def summarizeHar(har):
    """Given a har file (parsed json object), returns total size of all responses, in bytes."""
    return sum((entry["response"]["content"]["size"] for entry in har["log"]["entries"]))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: %s api_key report_id [operation]" % sys.argv[0])
        print("or: %s api_key report_id getresource resource [filename]" % sys.argv[0])
        print("where operation is one of: print (default), delete, retest, size, getresource")
        print("getresource operation requires one extra argument: what resource to get,")
        print("and one optional: filename where to save it.")
        print("If filename is not provided, resource is printed to stdout.")
        exit()

    main(*sys.argv[1:])
