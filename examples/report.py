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
    else:
        print("Usage: %s api_key report_id [operation]" % sys.argv[0])
        print("or: %s api_key report_id getresource resource [filename]" % sys.argv[0])
        print("where operation is one of: print (default), delete, retest, getresource")


def getresource(report, resource, filename=sys.stdout.buffer):
    report.getresource(resource, filename)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: %s api_key report_id [operation]" % sys.argv[0])
        print("or: %s api_key report_id getresource resource [filename]" % sys.argv[0])
        print("where operation is one of: print (default), delete, retest, getresource")
        print("getresource operation requires one extra argument: what resource to get,")
        print("and one optional: filename where to save it.")
        print("If filename is not provided, resource is printed to stdout.")
        exit()

    main(*sys.argv[1:])
