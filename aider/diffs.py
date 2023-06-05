import sys
import difflib

def main():
    if len(sys.argv) != 3:
        print("Usage: python diffs.py file1 file2")
        sys.exit(1)

    file1, file2 = sys.argv[1], sys.argv[2]

    with open(file1, 'r') as f1:
        content1 = f1.readlines()

    with open(file2, 'r') as f2:
        content2 = f2.readlines()

    differences = list(difflib.unified_diff(content1, content2, fromfile=file1, tofile=file2))

    for line in differences:
        sys.stdout.write(line)

if __name__ == "__main__":
    main()
