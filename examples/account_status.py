import sys
import json

import python_gtmetrix2


def main(api_key):
    interface = python_gtmetrix2.Interface(api_key)

    status = interface.status()

    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: %s api_key" % sys.argv[0])
        exit()

    main(sys.argv[1])
