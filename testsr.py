import sys
import re

def wordcount(text):
    """Count the number of words in the given text."""
    return len(text.split())

def process_markdown(filename):
    try:
        with open(filename, 'r') as file:
            content = file.read()

        # Split the content into sections based on '####' headers
        sections = re.split(r'(?=####\s)', content)

        for section in sections:
            if section.strip():  # Ignore empty sections
                # Extract the header (if present)
                header = section.split('\n')[0].strip()
                # Get the content (everything after the header)
                content = '\n'.join(section.split('\n')[1:]).strip()
                
                # Count words
                count = wordcount(content)
                
                print(f"{header}: {count} words")

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python testsr.py <markdown_filename>")
    else:
        process_markdown(sys.argv[1])
