import os

class Coder:
    def __init__(self):
        pass

    def get_all_files(self):
        files = []
        for root, dirs, filenames in os.walk(".", topdown=True):
            # Exclude directories starting with a dot
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files
