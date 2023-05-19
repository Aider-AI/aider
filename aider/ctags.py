import json
import sys

def print_tags_info(filename):
    with open(filename, "r") as tags_file:
        for line in tags_file:
            tag = json.loads(line)
            scope = tag.get("scope", "N/A")
            kind = tag.get("kind", "N/A")
            name = tag.get("name", "N/A")
            signature = tag.get("signature", "N/A")
            print(scope, kind, name, signature)

if __name__ == "__main__":
    for filename in sys.argv[1:]:
        print_tags_info(filename)
