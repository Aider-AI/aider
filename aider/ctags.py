import json

def print_tags_info():
    with open("tags.jsonl", "r") as tags_file:
        for line in tags_file:
            tag = json.loads(line)
            scope = tag.get("scope", "N/A")
            kind = tag.get("kind", "N/A")
            name = tag.get("name", "N/A")
            signature = tag.get("signature", "N/A")
            print(f"Scope: {scope}, Kind: {kind}, Name: {name}, Signature: {signature}")

if __name__ == "__main__":
    print_tags_info()
