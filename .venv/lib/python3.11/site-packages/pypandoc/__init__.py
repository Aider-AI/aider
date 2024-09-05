# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, with_statement
from typing import Iterable
from typing import Union
from typing import Generator

import os
import re
import subprocess
import sys
import tempfile
import textwrap
import glob
from pathlib import Path

from .handler import logger, _check_log_handler
from .pandoc_download import DEFAULT_TARGET_FOLDER, download_pandoc
from .py3compat import cast_bytes, cast_unicode, string_types, url2path, urlparse

__author__ = u'Juho Vepsäläinen'
__author_email__ = "bebraw@gmail.com"
__maintainer__ = u'Jessica Tegner'
__url__ = 'https://github.com/JessicaTegner/pypandoc'
__version__ = '1.13'
__license__ = 'MIT'
__description__ = "Thin wrapper for pandoc."
__python_requires__ = ">=3.6"
__setup_requires__ = ['setuptools', 'pip>=8.1.0', 'wheel>=0.25.0']
__classifiers__ = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Text Processing',
        'Topic :: Text Processing :: Filters',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ]

__all__ = ['convert_file', 'convert_text',
           'get_pandoc_formats', 'get_pandoc_version', 'get_pandoc_path',
           'download_pandoc']

def convert_text(source:str, to:str, format:str, extra_args:Iterable=(), encoding:str='utf-8',
                 outputfile:Union[None, str, Path]=None, filters:Union[Iterable, None]=None, verify_format:bool=True,
                 sandbox:bool=False, cworkdir:Union[str, None]=None) -> str:
    """Converts given `source` from `format` to `to`.

    :param str source: Unicode string or bytes (see encoding)

    :param str to: format into which the input should be converted; can be one of
            `pypandoc.get_pandoc_formats()[1]`

    :param str format: the format of the inputs; can be one of `pypandoc.get_pandoc_formats()[1]`

    :param list extra_args: extra arguments (list of strings) to be passed to pandoc
            (Default value = ())

    :param str encoding: the encoding of the input bytes (Default value = 'utf-8')

    :param str outputfile: output will be written to outputfile or the converted content
            returned if None. The output filename can be specified as a string
            or pathlib.Path object. (Default value = None)

    :param list filters: pandoc filters e.g. filters=['pandoc-citeproc']

    :param bool verify_format: Verify from and to format before converting. Should only be set False when confident of the formats and performance is an issue.
            (Default value = True)

    :param bool sandbox: Run pandoc in pandocs own sandbox mode, limiting IO operations in readers and writers to reading the files specified on the command line. Anyone using pandoc on untrusted user input should use this option. Note: This only does something, on pandoc >= 2.15
            (Default value = False)

    :returns: converted string (unicode) or an empty string if an outputfile was given
    :rtype: unicode

    :raises RuntimeError: if any of the inputs are not valid of if pandoc fails with an error
    :raises OSError: if pandoc is not found; make sure it has been installed and is available at
            path.
    """
    source = _as_unicode(source, encoding)
    return _convert_input(source, format, 'string', to, extra_args=extra_args,
                          outputfile=outputfile, filters=filters,
                          verify_format=verify_format, sandbox=sandbox,
                          cworkdir=cworkdir)


def convert_file(source_file:Union[list, str, Path, Generator], to:str, format:Union[str, None]=None,
                 extra_args:Iterable=(), encoding:str='utf-8', outputfile:Union[None, str, Path]=None,
                 filters:Union[Iterable, None]=None, verify_format:bool=True, sandbox:bool=False,
                 cworkdir:Union[str, None]=None) -> str:
    """Converts given `source` from `format` to `to`.

    :param (str, list, pathlib.Path) source_file: If a string, should be either
            an absolute file path, relative file path, or a file pattern (like dir/*.md).
            If a list, should be a list of file paths, file patterns, or pathlib.Path
            objects. In addition, pathlib.Path objects as well as the generators produced by
            pathlib.Path.glob may be specified.

    :param str to: format into which the input should be converted; can be one of
            `pypandoc.get_pandoc_formats()[1]`

    :param str format: the format of the inputs; will be inferred from the source_file with an
            known filename extension; can be one of `pypandoc.get_pandoc_formats()[1]`
            (Default value = None)

    :param list extra_args: extra arguments (list of strings) to be passed to pandoc
            (Default value = ())

    :param str encoding (deprecated): the encoding of the input bytes (Default value = 'utf-8')

    :param str outputfile: output will be written to outputfile or the converted content
            returned if None. The output filename can be specified as a string
            or pathlib.Path object. (Default value = None)

    :param list filters: pandoc filters e.g. filters=['pandoc-citeproc']

    :param bool verify_format: Verify from and to format before converting. Should only be set False when confident of the formats and performance is an issue.
            (Default value = True)

    :param bool sandbox: Run pandoc in pandocs own sandbox mode, limiting IO operations in readers and writers to reading the files specified on the command line. Anyone using pandoc on untrusted user input should use this option. Note: This only does something, on pandoc >= 2.15
            (Default value = False)

    :returns: converted string (unicode) or an empty string if an outputfile was given
    :rtype: unicode

    :raises RuntimeError: if any of the inputs are not valid of if pandoc fails with an error
    :raises OSError: if pandoc is not found; make sure it has been installed and is available at
            path.
    """
    # check if we have a working directory
    # if we don't, we use the current working directory
    if cworkdir is None:
        cworkdir = os.getcwd()

    # TODO: remove 'encoding' parameter and warning
    if encoding != "utf-8":
        logger.warning("The 'encoding' parameter will be removed in version 1.13. Just remove the parameter, because currently the method does not use it.")

    if _is_network_path(source_file): # if the source_file is an url
        format = _identify_format_from_path(source_file, format)
        return _convert_input(source_file, format, 'path', to, extra_args=extra_args,
                          outputfile=outputfile, filters=filters,
                          verify_format=verify_format, sandbox=sandbox,
                          cworkdir=cworkdir)

    # convert the source file to a path object internally
    if isinstance(source_file, str):
        source_file = Path(source_file)
    elif isinstance(source_file, list):
        source_file = [Path(x) for x in source_file]
    elif isinstance(source_file, Generator):
        source_file = [Path(x) for x in source_file]


    # we are basically interested to figure out if its an absolute path or not
    # if it's not, we want to prefix the working directory
    # if it's a list, we want to prefix the working directory to each item if it's not an absolute path
    # if it is, just use the absolute path
    if isinstance(source_file, list):
        source_file = [x if x.is_absolute() else Path(cworkdir, x) for x in source_file]
    elif isinstance(source_file, Generator):
        source_file = (x if x.is_absolute() else Path(cworkdir, x) for x in source_file)
    # check ifjust a single path was given
    elif isinstance(source_file, Path):
        source_file = source_file if source_file.is_absolute() else Path(cworkdir, source_file)


    discovered_source_files = []
    # if we have a list of files, we need to glob them
    # if we have a single file, we need to glob it
    # remember that we already converted the source_file to a path object
    # so for glob.glob use both the dir and file name
    if isinstance(source_file, list):
        for single_source in source_file:
            discovered_source_files.extend(glob.glob(str(single_source)))
        if discovered_source_files == []:
            discovered_source_files = source_file
    else:
        discovered_source_files.extend(glob.glob(str(source_file)))
        if discovered_source_files == []:
            discovered_source_files = [source_file]

    if not _identify_path(discovered_source_files):
        raise RuntimeError("source_file is not a valid path")
    format = _identify_format_from_path(discovered_source_files[0], format)
    if len(discovered_source_files) == 1:
        discovered_source_files = discovered_source_files[0]

    return _convert_input(discovered_source_files, format, 'path', to, extra_args=extra_args,
                      outputfile=outputfile, filters=filters,
                      verify_format=verify_format, sandbox=sandbox,
                      cworkdir=cworkdir)


def _identify_path(source) -> bool:
    if isinstance(source, list):
        for single_source in source:
            if not _identify_path(single_source):
                return False
        return True
    is_path = False
    try:
        is_path = os.path.exists(source)
    except UnicodeEncodeError:
        is_path = os.path.exists(source.encode('utf-8'))
    except:  # noqa
        # still false
        pass

    if not is_path:
        try:
            is_path = len(glob.glob(source)) >= 1
        except UnicodeEncodeError:
            is_path = len(glob.glob(source.encode('utf-8'))) >= 1
        except:  # noqa
            # still false
            pass
    
    if not is_path:
        try:
            # check if it's an URL
            result = urlparse(source)
            if result.scheme in ["http", "https"]:
                is_path = True
            elif result.scheme and result.netloc and result.path:
                # complete uri including one with a network path
                is_path = True
            elif result.scheme == "file" and result.path:
                is_path = os.path.exists(url2path(source))
        except AttributeError:
            pass

    return is_path

def _is_network_path(source):
    try:
        # check if it's an URL
        result = urlparse(source)
        if result.scheme in ["http", "https"]:
            return True
        elif result.scheme and result.netloc and result.path:
            # complete uri including one with a network path
            return True
        elif result.scheme == "file" and result.path:
            return os.path.exists(url2path(source))
    except AttributeError:
        pass
    return False


def _identify_format_from_path(sourcefile:str, format:str) -> str:
    return format or os.path.splitext(sourcefile)[1].strip('.')


def _as_unicode(source:any, encoding:str) -> any:
    if encoding != 'utf-8':
        # if a source and a different encoding is given, try to decode the the source into a
        # unicode string
        try:
            source = cast_unicode(source, encoding=encoding)
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
    return source


def _identify_input_type(source:any, format:str, encoding:str='utf-8'):
    path = _identify_path(source)
    if path:
        format = _identify_format_from_path(source, format)
        input_type = 'path'
    else:
        source = _as_unicode(source, encoding)
        input_type = 'string'
    return source, format, input_type


def normalize_format(fmt):
    formats = {
        'dbk': 'docbook',
        'md': 'markdown',
        'tex': 'latex',
    }
    fmt = formats.get(fmt, fmt)
    # rst format can have extensions
    if fmt[:4] == "rest":
        fmt = "rst" + fmt[4:]
    return fmt


def _validate_formats(format, to, outputfile):

    format = normalize_format(format)
    to = normalize_format(to)

    if not format:
        raise RuntimeError('Missing format!')

    from_formats, to_formats = get_pandoc_formats()

    if _get_base_format(format) not in from_formats:
        raise RuntimeError(
            'Invalid input format! Got "%s" but expected one of these: %s' % (
                _get_base_format(format), ', '.join(from_formats)))

    base_to_format = _get_base_format(to)

    file_extension = os.path.splitext(to)[1]

    if (base_to_format not in to_formats and
            base_to_format != "pdf" and  # pdf is handled later # noqa: E127
            file_extension != '.lua'):
        raise RuntimeError(
            'Invalid output format! Got %s but expected one of these: %s' % (
                base_to_format, ', '.join(to_formats)))

    # list from https://github.com/jgm/pandoc/blob/master/pandoc.hs
    # `[...] where binaries = ["odt","docx","epub","epub3"] [...]`
    # pdf has the same restriction
    if base_to_format in ["odt", "docx", "epub", "epub3", "pdf"] and not outputfile:
        raise RuntimeError(
            'Output to %s only works by using a outputfile.' % base_to_format
        )

    if base_to_format == "pdf":
        # pdf formats needs to actually have a to format of latex and a
        # filename with an ending pf .pdf
        if isinstance(outputfile, str):
            if outputfile[-4:] != ".pdf":
                raise RuntimeError(
                    'PDF output needs an outputfile with ".pdf" as a fileending.'
                )
        elif isinstance(outputfile, Path):
            if outputfile.suffix != ".pdf":
                raise RuntimeError(
                    'PDF output needs an outputfile with ".pdf" as a fileending.'
                )
        # to is not allowed to contain pdf, but must point to latex
        # it's also not allowed to contain extensions according to the docs
        if to != base_to_format:
            raise RuntimeError("PDF output can't contain any extensions: %s" % to)
        to = "latex"

    return format, to


def _convert_input(source, format, input_type, to, extra_args=(),
                   outputfile=None, filters=None, verify_format=True,
                   sandbox=False, cworkdir=None):
    
    _check_log_handler()

    logger.debug("Ensuring pandoc path...")
    _ensure_pandoc_path()

    if verify_format:
        logger.debug("Verifying format...")
        format, to = _validate_formats(format, to, outputfile)
    else:
        format = normalize_format(format)
        to = normalize_format(to)

    logger.debug("Identifying input type...")
    string_input = input_type == 'string'
    if not string_input:
        if isinstance(source, str):
            input_file = [source]
        else:
            input_file = source
    else:
        input_file = []
    
    input_file = sorted(input_file)
    args = [__pandoc_path, '--from=' + format]

    args.append('--to=' + to)

    args += input_file

    if outputfile:
        args.append("--output=" + str(outputfile))

    if sandbox:
        if ensure_pandoc_minimal_version(2,15): # sandbox was introduced in pandoc 2.15, so only add if we are using 2.15 or above.
            logger.debug("Adding sandbox argument...")
            args.append("--sandbox")
        else:
            logger.warning("Sandbox argument was used, but pandoc version is too low. Ignoring argument.")

    args.extend(extra_args)

    # adds the proper filter syntax for each item in the filters list
    if filters is not None:
        if isinstance(filters, string_types):
            filters = filters.split()
        f = ['--lua-filter=' + x if x.endswith(".lua") else '--filter=' + x for x in filters]
        args.extend(f)

    # To get access to pandoc-citeproc when we use a included copy of pandoc,
    # we need to add the pypandoc/files dir to the PATH
    new_env = os.environ.copy()
    files_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "files")
    new_env["PATH"] = new_env.get("PATH", "") + os.pathsep + files_path
    creation_flag = 0x08000000 if sys.platform == "win32" else 0 # set creation flag to not open pandoc in new console on windows

    old_wd = os.getcwd()
    if cworkdir and old_wd != cworkdir:
        os.chdir(cworkdir)

    logger.debug("Running pandoc...")
    p = subprocess.Popen(
        args,
        stdin=subprocess.PIPE if string_input else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=new_env,
        creationflags=creation_flag)

    if cworkdir is not None:
        os.chdir(old_wd)

    # something else than 'None' indicates that the process already terminated
    if not (p.returncode is None):
        raise RuntimeError(
            'Pandoc died with exitcode "%s" before receiving input: %s' % (p.returncode,
                                                                           p.stderr.read())
        )

    if string_input:
        try:
            source = cast_bytes(source, encoding='utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            # assume that it is already a utf-8 encoded string
            pass
    try:
        stdout, stderr = p.communicate(source if string_input else None)
    except OSError:
        # this is happening only on Py2.6 when pandoc dies before reading all
        # the input. We treat that the same as when we exit with an error...
        raise RuntimeError('Pandoc died with exitcode "%s" during conversion.' % (p.returncode))

    try:
        if not (to in ["odt", "docx", "epub", "epub3", "pdf"] and outputfile == "-"):
            stdout = stdout.decode('utf-8')
    except UnicodeDecodeError:
        # this shouldn't happen: pandoc more or less guarantees that the output is utf-8!
        raise RuntimeError('Pandoc output was not utf-8.')
           
    try:
        stderr = stderr.decode('utf-8')
    except UnicodeDecodeError:
        # this shouldn't happen: pandoc more or less guarantees that the output is utf-8!
        raise RuntimeError('Pandoc output was not utf-8.')

    # check that pandoc returned successfully
    if p.returncode != 0:
        raise RuntimeError(
            'Pandoc died with exitcode "%s" during conversion: %s' % (p.returncode, stderr)
        )
    
    # if there is output on stderr, process it and send to logger
    if stderr:
        for level, msg in _classify_pandoc_logging(stderr):
            logger.log(level, msg)

    # if there is an outputfile, then stdout is likely empty!
    return stdout


def _classify_pandoc_logging(raw, default_level="WARNING"):
    # Process raw and yield the contained logging levels and messages.
    # Assumes that the messages are formatted like "[LEVEL] message". If the 
    # first message does not have a level or any other message has a level 
    # that does not conform to the pandoc standard, use the default_level 
    # value instead.
    
    # Available pandoc logging levels adapted from:
    # https://github.com/jgm/pandoc/blob/5e1249481b2e3fc27e845245a0c96c3687a23c3d/src/Text/Pandoc/Logging.hs#L44
    def get_python_level(pandoc_level):
        
        level_map = {"ERROR": 40,
                     "WARNING": 30,
                     "INFO": 20,
                     "DEBUG": 10}
        
        if pandoc_level not in level_map:
            level = level_map[default_level]
        else:
            level = level_map[pandoc_level]
        
        return level
    
    msgs = raw.split("\n")
    first = msgs.pop(0)
    
    search = re.search(r"\[(.*?)\]", first)
    
    # Use the default if the first message doesn't have a level
    if search is None:
        pandoc_level = default_level
    else:
        pandoc_level = first[search.start(1):search.end(1)]
    
    log_msgs = [first.replace('[{}] '.format(pandoc_level), '')]
    
    for msg in msgs:
        
        search = re.search(r"\[(.*?)\]", msg)
        
        if search is not None:
            yield get_python_level(pandoc_level), "\n".join(log_msgs)
            pandoc_level = msg[search.start(1):search.end(1)]
            log_msgs = [msg.replace('[{}] '.format(pandoc_level), '')]
            continue
        
        log_msgs.append(msg)
    
    yield get_python_level(pandoc_level), "\n".join(log_msgs)


def _get_base_format(format):
    '''
    According to http://johnmacfarlane.net/pandoc/README.html#general-options,
    syntax extensions for markdown can be individually enabled or disabled by
    appending +EXTENSION or -EXTENSION to the format name.
    Return the base format without any extensions.
    '''
    return re.split(r'\+|-', format)[0]


def get_pandoc_formats() -> Iterable:
    '''
    Dynamic preprocessor for Pandoc formats.
    Return 2 lists. "from_formats" and "to_formats".
    '''
    _ensure_pandoc_path()
    creation_flag = 0x08000000 if sys.platform == "win32" else 0 # set creation flag to not open pandoc in new console on windows
    p = subprocess.Popen(
        [__pandoc_path, '--list-output-formats'],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        creationflags=creation_flag)

    comm = p.communicate()
    out = comm[0].decode().splitlines(False)
    if p.returncode != 0:
        # try the old version and see if that returns something
        return get_pandoc_formats_pre_1_18()

    p = subprocess.Popen(
        [__pandoc_path, '--list-input-formats'],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        creationflags=creation_flag)

    comm = p.communicate()
    in_ = comm[0].decode().splitlines(False)

    return [f.strip() for f in in_], [f.strip() for f in out]


def get_pandoc_formats_pre_1_18() -> Iterable:
    '''
    Dynamic preprocessor for Pandoc formats for version < 1.18.
    Return 2 lists. "from_formats" and "to_formats".
    '''
    _ensure_pandoc_path()
    creation_flag = 0x08000000 if sys.platform == "win32" else 0 # set creation flag to not open pandoc in new console on windows
    p = subprocess.Popen(
        [__pandoc_path, '-h'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        creationflags=creation_flag)

    comm = p.communicate()
    help_text = comm[0].decode().splitlines(False)
    if p.returncode != 0 or 'Options:' not in help_text:
        raise RuntimeError("Couldn't call pandoc to get output formats. Output from pandoc:\n%s" %
                           str(comm))
    txt = ' '.join(help_text[1:help_text.index('Options:')])

    aux = txt.split('Output formats: ')
    in_ = re.sub(r'Input\sformats:\s|\*|\[.*?\]', '', aux[0]).split(',')
    out = re.sub(r'\*|\[.*?\]', '', aux[1]).split(',')

    return [f.strip() for f in in_], [f.strip() for f in out]


# copied and adapted from jupyter_nbconvert/utils/pandoc.py, Modified BSD License

def _get_pandoc_version(pandoc_path:str) -> str:
    new_env = os.environ.copy()
    creation_flag = 0x08000000 if sys.platform == "win32" else 0 # set creation flag to not open pandoc in new console on windows
    if 'HOME' not in os.environ:
        new_env['HOME'] = tempfile.gettempdir()
    p = subprocess.Popen(
        [pandoc_path, '--version'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        env=new_env,
        creationflags=creation_flag)
    comm = p.communicate()
    out_lines = comm[0].decode().splitlines(False)
    if p.returncode != 0 or len(out_lines) == 0:
        raise RuntimeError("Couldn't call pandoc to get version information. Output from "
                           "pandoc:\n%s" % str(comm))

    version_pattern = re.compile(r"^\d+(\.\d+){1,}$")
    for tok in out_lines[0].split():
        if version_pattern.match(tok):
            version = tok
            break
    return version


def get_pandoc_version() -> str:
    """Gets the Pandoc version if Pandoc is installed.

    It will probe Pandoc for its version, cache it and return that value. If a cached version is
    found, it will return the cached version and stop probing Pandoc
    (unless :func:`clean_version_cache()` is called).

    :raises OSError: if pandoc is not found; make sure it has been installed and is available at
            path.
    """
    global __version

    if __version is None:
        _ensure_pandoc_path()
        __version = _get_pandoc_version(__pandoc_path)
    return __version


def get_pandoc_path() -> str:
    """Gets the Pandoc path if Pandoc is installed.

    It will return a path to pandoc which is used by pypandoc.

    This might be a full path or, if pandoc is on PATH, simple `pandoc`. It's guaranteed
    to be callable (i.e. we could get version information from `pandoc --version`).
    If `PYPANDOC_PANDOC` is set and valid, it will return that value. If the environment
    variable is not set, either the full path to the included pandoc or the pandoc in
    `PATH` or a pandoc in some of the more usual (platform specific) install locations
    (whatever is the higher version) will be returned.

    If a cached path is found, it will return the cached path and stop probing Pandoc
    (unless :func:`clean_pandocpath_cache()` is called).

    :raises OSError: if pandoc is not found
    """
    _ensure_pandoc_path()
    return __pandoc_path

def ensure_pandoc_minimal_version(major:int, minor:int=0) -> bool:
    """Check if the used pandoc fulfill a minimal version requirement.

    :param int major: pandoc major version, such as 1 or 2.

    :param int minor: pandoc minor version, such as 10 or 11.

    :returns: True if the installed pandoc is above the minimal version, False otherwise.
    :rtype: bool
    """
    version = [int(x) for x in get_pandoc_version().split(".")]
    if version[0] > int(major): # if we have pandoc2 but major is request to be 1
        return True
    return version[0] >= int(major) and version[1] >= int(minor)
    


def ensure_pandoc_maximal_version(major:int, minor:int=9999) -> bool:
    """Check if the used pandoc fulfill a maximal version requirement.

    :param int major: pandoc major version, such as 1 or 2.

    :param int minor: pandoc minor version, such as 10 or 11.

    :returns: True if the installed pandoc is below the maximal version, False otherwise.
    :rtype: bool
    """
    version = [int(x) for x in get_pandoc_version().split(".")]
    if version[0] < int(major): # if we have pandoc1 but major is request to be 2
        return True
    return version[0] <= int(major) and version[1] <= int(minor)


def _ensure_pandoc_path() -> None:
    global __pandoc_path
    
    _check_log_handler()
    
    if __pandoc_path is None:
        included_pandoc = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       "files", "pandoc")
        search_paths = ["pandoc", included_pandoc]
        pf = "linux" if sys.platform.startswith("linux") else sys.platform
        try:
            if pf == "win32":
                search_paths.append(os.path.join(DEFAULT_TARGET_FOLDER[pf], "pandoc.exe"))
            else:
                search_paths.append(os.path.join(DEFAULT_TARGET_FOLDER[pf], "pandoc"))
        except:  # noqa
            # not one of the know platforms...
            pass
        if pf == "linux":
            # Currently we install into ~/bin, but this is equally likely...
            search_paths.append("~/.bin/pandoc")
        # Also add the interpreter script path, as that's where pandoc could be
        # installed if it's an environment and the environment wasn't activated
        if pf == "win32":
            search_paths.append(os.path.join(sys.exec_prefix, "Scripts", "pandoc.exe"))

            # Since this only runs on Windows, use Windows slashes
            if os.getenv('ProgramFiles', None):
                search_paths.append(os.path.expandvars("${ProgramFiles}\\Pandoc\\pandoc.exe"))
                search_paths.append(os.path.expandvars("${ProgramFiles}\\Pandoc\\Pandoc.exe"))
            if os.getenv('ProgramFiles(x86)', None):
                search_paths.append(os.path.expandvars("${ProgramFiles(x86)}\\Pandoc\\pandoc.exe"))
                search_paths.append(os.path.expandvars("${ProgramFiles(x86)}\\Pandoc\\Pandoc.exe"))

        # bin can also be used on windows (conda at least has it in path), so
        # include it unconditionally
        search_paths.append(os.path.join(sys.exec_prefix, "bin", "pandoc.exe"))
        search_paths.append(os.path.join(sys.exec_prefix, "bin", "pandoc"))
        # If a user added the complete path to pandoc to an env, use that as the
        # only way to get pandoc so that a user can overwrite even a higher
        # version in some other places.
        if os.getenv('PYPANDOC_PANDOC', None):
            search_paths = [os.getenv('PYPANDOC_PANDOC')]
        curr_version = [0, 0, 0]
        for path in search_paths:
            # Needed for windows and subprocess which can't expand it on it's
            # own...
            path = os.path.expanduser(path)
            version_string = "0.0.0"
            # print("Trying: %s" % path)
            try:
                version_string = _get_pandoc_version(path)
            except Exception:
                # we can't use that path...
                if os.path.exists(path):
                    # path exist but is not usable -> not executable?
                    log_msg = ("Found {}, but not using it because of an "
                               "error:".format(path))
                    logger.exception(log_msg)
                continue
            version = [int(x) for x in version_string.split(".")]
            while len(version) < len(curr_version):
                version.append(0)
            # print("%s, %s" % (path, version))
            # Only use the new version if it is any bigger...
            if version > curr_version:
                # print("Found: %s" % path)
                __pandoc_path = path
                curr_version = version

        if __pandoc_path is None:
            # Only print hints if requested
            if os.path.exists('/usr/local/bin/brew'):
                logger.info(textwrap.dedent("""\
                    Maybe try:

                        brew install pandoc
                """))
            elif os.path.exists('/usr/bin/apt-get'):
                logger.info(textwrap.dedent("""\
                    Maybe try:

                        sudo apt-get install pandoc
                """))
            elif os.path.exists('/usr/bin/yum'):
                logger.info(textwrap.dedent("""\
                    Maybe try:

                    sudo yum install pandoc
                """))
            logger.info(textwrap.dedent("""\
                See http://johnmacfarlane.net/pandoc/installing.html
                for installation options
            """))
            logger.info(textwrap.dedent("""\
                ---------------------------------------------------------------

            """))
            raise OSError("No pandoc was found: either install pandoc and add it\n"
                          "to your PATH or or call pypandoc.download_pandoc(...) or\n"
                          "install pypandoc wheels with included pandoc.")


def ensure_pandoc_installed(url:Union[str, None]=None, 
                            targetfolder:Union[str, None]=None,
                            version:str="latest",
                            delete_installer:bool=False) -> None:
    """Try to install pandoc if it isn't installed.

    Parameters are passed to download_pandoc()

    :raises OSError: if pandoc cannot be installed
    """

    # Append targetfolder to the PATH environment variable so it is found by subprocesses
    if targetfolder is not None:
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + os.path.abspath(os.path.expanduser(targetfolder))

    try:
        _ensure_pandoc_path()

    except OSError:
        download_pandoc(url=url,
                        targetfolder=targetfolder,
                        version=version,
                        delete_installer=delete_installer)

        # Show errors in case of secondary failure
        _ensure_pandoc_path()


# -----------------------------------------------------------------------------
# Internal state management
# -----------------------------------------------------------------------------
def clean_version_cache():
    global __version
    __version = None


def clean_pandocpath_cache():
    global __pandoc_path
    __pandoc_path = None


__version = None
__pandoc_path = None
