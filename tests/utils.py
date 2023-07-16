import tempfile


class IgnorantTemporaryDirectory:
    def __init__(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def __enter__(self):
        return self.temp_dir.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.temp_dir.__exit__(exc_type, exc_val, exc_tb)
        except OSError:
            pass  # Ignore errors (Windows)
