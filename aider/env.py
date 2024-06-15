from pathlib import Path

USER_HOME_PATH = Path.home()


def absolute_path(path, codebase_path=''):
    #Check if the path is already absolute
    if path.startswith(f'{str(USER_HOME_PATH)}/FumeData/{codebase_path}'):
        return path
    file_path = f'{str(USER_HOME_PATH)}/FumeData/{codebase_path}/{path}'
    file_path = str(Path(file_path).resolve())

    return file_path

def relative_path(path,codebase_path='codebase'):
    # Remove the user's home path and FumeData directory from the beginning of the path
    # Do not modify the original path
    #Check if the path is already relative
    if not path.startswith(f'{str(USER_HOME_PATH)}/FumeData/{codebase_path}'):
        return path
    res = path.replace(f'{str(USER_HOME_PATH)}/FumeData/{codebase_path}', '')
    if res.startswith('/'):
        res = res[1:]
    return res