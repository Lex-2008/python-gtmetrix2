import sys
import json

import python_gtmetrix2


def main(api_key, ids):
    account = python_gtmetrix2.Account(api_key)

    for id in ids:
        print(json.dumps(account.testFromId(id), indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: %s api_key test_id..." % sys.argv[0])
        exit()

    api_key = sys.argv[1]
    urls = sys.argv[2:]

    main(api_key, urls)
