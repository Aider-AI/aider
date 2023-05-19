import json
import sys


def print_tags_info(filename):
    last = None
    last_prefix = None
    tags = sorted(get_tags(filename))

    for tag in tags:
        if last is None:
            show = tag
            prefix = None
        else:
            show = []
            prefix = []
            stop = False
            for lst, tg in zip(last, tag):
                if lst == tg and not stop:
                    prefix.append(lst)
                    show.append("")
                else:
                    stop = True
                    show.append(tg)

        if prefix != last_prefix:
            print(prefix)
            last_prefix = prefix
        if not show[-1]:
            show = show[:-1]
        show = "\t".join(show)
        print(show)
        last = tag


def get_tags(filename):
    with open(filename, "r") as tags_file:
        for line in tags_file:
            tag = json.loads(line)
            scope = tag.get("scope", "(top)")
            kind = tag.get("kind", "")
            name = tag.get("name", "")
            signature = tag.get("signature", "")
            yield (scope, kind, name, signature)


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        print_tags_info(filename)
