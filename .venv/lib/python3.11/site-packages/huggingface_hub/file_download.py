import contextlib
import copy
import errno
import fnmatch
import inspect
import json
import os
import re
import shutil
import stat
import time
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Dict, Literal, NoReturn, Optional, Tuple, Union
from urllib.parse import quote, urlparse

import requests

from . import __version__  # noqa: F401 # for backward compatibility
from ._local_folder import (
    get_local_download_paths,
    read_download_metadata,
    write_download_metadata,
)
from .constants import (
    DEFAULT_ETAG_TIMEOUT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_REVISION,
    DOWNLOAD_CHUNK_SIZE,
    ENDPOINT,
    HF_HUB_CACHE,
    HF_HUB_DISABLE_SYMLINKS_WARNING,
    HF_HUB_DOWNLOAD_TIMEOUT,
    HF_HUB_ENABLE_HF_TRANSFER,
    HF_HUB_ETAG_TIMEOUT,
    HF_TRANSFER_CONCURRENCY,
    HUGGINGFACE_CO_URL_TEMPLATE,
    HUGGINGFACE_HEADER_X_LINKED_ETAG,
    HUGGINGFACE_HEADER_X_LINKED_SIZE,
    HUGGINGFACE_HEADER_X_REPO_COMMIT,
    HUGGINGFACE_HUB_CACHE,  # noqa: F401 # for backward compatibility
    REPO_ID_SEPARATOR,
    REPO_TYPES,
    REPO_TYPES_URL_PREFIXES,
)
from .utils import (
    EntryNotFoundError,
    FileMetadataError,
    GatedRepoError,
    LocalEntryNotFoundError,
    OfflineModeIsEnabled,
    RepositoryNotFoundError,
    RevisionNotFoundError,
    SoftTemporaryDirectory,
    WeakFileLock,
    build_hf_headers,
    get_fastai_version,  # noqa: F401 # for backward compatibility
    get_fastcore_version,  # noqa: F401 # for backward compatibility
    get_graphviz_version,  # noqa: F401 # for backward compatibility
    get_jinja_version,  # noqa: F401 # for backward compatibility
    get_pydot_version,  # noqa: F401 # for backward compatibility
    get_session,
    get_tf_version,  # noqa: F401 # for backward compatibility
    get_torch_version,  # noqa: F401 # for backward compatibility
    hf_raise_for_status,
    is_fastai_available,  # noqa: F401 # for backward compatibility
    is_fastcore_available,  # noqa: F401 # for backward compatibility
    is_graphviz_available,  # noqa: F401 # for backward compatibility
    is_jinja_available,  # noqa: F401 # for backward compatibility
    is_pydot_available,  # noqa: F401 # for backward compatibility
    is_tf_available,  # noqa: F401 # for backward compatibility
    is_torch_available,  # noqa: F401 # for backward compatibility
    logging,
    reset_sessions,
    tqdm,
    validate_hf_hub_args,
)
from .utils._deprecation import _deprecate_arguments, _deprecate_method
from .utils._runtime import _PY_VERSION  # noqa: F401 # for backward compatibility
from .utils._typing import HTTP_METHOD_T
from .utils.insecure_hashlib import sha256
from .utils.sha import sha_fileobj


logger = logging.get_logger(__name__)

# Return value when trying to load a file from cache but the file does not exist in the distant repo.
_CACHED_NO_EXIST = object()
_CACHED_NO_EXIST_T = Any

# Regex to get filename from a "Content-Disposition" header for CDN-served files
HEADER_FILENAME_PATTERN = re.compile(r'filename="(?P<filename>.*?)";')

# Regex to check if the revision IS directly a commit_hash
REGEX_COMMIT_HASH = re.compile(r"^[0-9a-f]{40}$")

# Regex to check if the file etag IS a valid sha256
REGEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_are_symlinks_supported_in_dir: Dict[str, bool] = {}


def are_symlinks_supported(cache_dir: Union[str, Path, None] = None) -> bool:
    """Return whether the symlinks are supported on the machine.

    Since symlinks support can change depending on the mounted disk, we need to check
    on the precise cache folder. By default, the default HF cache directory is checked.

    Args:
        cache_dir (`str`, `Path`, *optional*):
            Path to the folder where cached files are stored.

    Returns: [bool] Whether symlinks are supported in the directory.
    """
    # Defaults to HF cache
    if cache_dir is None:
        cache_dir = HF_HUB_CACHE
    cache_dir = str(Path(cache_dir).expanduser().resolve())  # make it unique

    # Check symlink compatibility only once (per cache directory) at first time use
    if cache_dir not in _are_symlinks_supported_in_dir:
        _are_symlinks_supported_in_dir[cache_dir] = True

        os.makedirs(cache_dir, exist_ok=True)
        with SoftTemporaryDirectory(dir=cache_dir) as tmpdir:
            src_path = Path(tmpdir) / "dummy_file_src"
            src_path.touch()
            dst_path = Path(tmpdir) / "dummy_file_dst"

            # Relative source path as in `_create_symlink``
            relative_src = os.path.relpath(src_path, start=os.path.dirname(dst_path))
            try:
                os.symlink(relative_src, dst_path)
            except OSError:
                # Likely running on Windows
                _are_symlinks_supported_in_dir[cache_dir] = False

                if not HF_HUB_DISABLE_SYMLINKS_WARNING:
                    message = (
                        "`huggingface_hub` cache-system uses symlinks by default to"
                        " efficiently store duplicated files but your machine does not"
                        f" support them in {cache_dir}. Caching files will still work"
                        " but in a degraded version that might require more space on"
                        " your disk. This warning can be disabled by setting the"
                        " `HF_HUB_DISABLE_SYMLINKS_WARNING` environment variable. For"
                        " more details, see"
                        " https://huggingface.co/docs/huggingface_hub/how-to-cache#limitations."
                    )
                    if os.name == "nt":
                        message += (
                            "\nTo support symlinks on Windows, you either need to"
                            " activate Developer Mode or to run Python as an"
                            " administrator. In order to see activate developer mode,"
                            " see this article:"
                            " https://docs.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development"
                        )
                    warnings.warn(message)

    return _are_symlinks_supported_in_dir[cache_dir]


@dataclass(frozen=True)
class HfFileMetadata:
    """Data structure containing information about a file versioned on the Hub.

    Returned by [`get_hf_file_metadata`] based on a URL.

    Args:
        commit_hash (`str`, *optional*):
            The commit_hash related to the file.
        etag (`str`, *optional*):
            Etag of the file on the server.
        location (`str`):
            Location where to download the file. Can be a Hub url or not (CDN).
        size (`size`):
            Size of the file. In case of an LFS file, contains the size of the actual
            LFS file, not the pointer.
    """

    commit_hash: Optional[str]
    etag: Optional[str]
    location: str
    size: Optional[int]


@validate_hf_hub_args
def hf_hub_url(
    repo_id: str,
    filename: str,
    *,
    subfolder: Optional[str] = None,
    repo_type: Optional[str] = None,
    revision: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> str:
    """Construct the URL of a file from the given information.

    The resolved address can either be a huggingface.co-hosted url, or a link to
    Cloudfront (a Content Delivery Network, or CDN) for large files which are
    more than a few MBs.

    Args:
        repo_id (`str`):
            A namespace (user or an organization) name and a repo name separated
            by a `/`.
        filename (`str`):
            The name of the file in the repo.
        subfolder (`str`, *optional*):
            An optional value corresponding to a folder inside the repo.
        repo_type (`str`, *optional*):
            Set to `"dataset"` or `"space"` if downloading from a dataset or space,
            `None` or `"model"` if downloading from a model. Default is `None`.
        revision (`str`, *optional*):
            An optional Git revision id which can be a branch name, a tag, or a
            commit hash.

    Example:

    ```python
    >>> from huggingface_hub import hf_hub_url

    >>> hf_hub_url(
    ...     repo_id="julien-c/EsperBERTo-small", filename="pytorch_model.bin"
    ... )
    'https://huggingface.co/julien-c/EsperBERTo-small/resolve/main/pytorch_model.bin'
    ```

    <Tip>

    Notes:

        Cloudfront is replicated over the globe so downloads are way faster for
        the end user (and it also lowers our bandwidth costs).

        Cloudfront aggressively caches files by default (default TTL is 24
        hours), however this is not an issue here because we implement a
        git-based versioning system on huggingface.co, which means that we store
        the files on S3/Cloudfront in a content-addressable way (i.e., the file
        name is its hash). Using content-addressable filenames means cache can't
        ever be stale.

        In terms of client-side caching from this library, we base our caching
        on the objects' entity tag (`ETag`), which is an identifier of a
        specific version of a resource [1]_. An object's ETag is: its git-sha1
        if stored in git, or its sha256 if stored in git-lfs.

    </Tip>

    References:

    -  [1] https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag
    """
    if subfolder == "":
        subfolder = None
    if subfolder is not None:
        filename = f"{subfolder}/{filename}"

    if repo_type not in REPO_TYPES:
        raise ValueError("Invalid repo type")

    if repo_type in REPO_TYPES_URL_PREFIXES:
        repo_id = REPO_TYPES_URL_PREFIXES[repo_type] + repo_id

    if revision is None:
        revision = DEFAULT_REVISION
    url = HUGGINGFACE_CO_URL_TEMPLATE.format(
        repo_id=repo_id, revision=quote(revision, safe=""), filename=quote(filename)
    )
    # Update endpoint if provided
    if endpoint is not None and url.startswith(ENDPOINT):
        url = endpoint + url[len(ENDPOINT) :]
    return url


@_deprecate_method(version="0.26", message="Use `hf_hub_download` to benefit from the new cache layout.")
def url_to_filename(url: str, etag: Optional[str] = None) -> str:
    """Generate a local filename from a url.

    Convert `url` into a hashed filename in a reproducible way. If `etag` is
    specified, append its hash to the url's, delimited by a period. If the url
    ends with .h5 (Keras HDF5 weights) adds '.h5' to the name so that TF 2.0 can
    identify it as a HDF5 file (see
    https://github.com/tensorflow/tensorflow/blob/00fad90125b18b80fe054de1055770cfb8fe4ba3/tensorflow/python/keras/engine/network.py#L1380)

    Args:
        url (`str`):
            The address to the file.
        etag (`str`, *optional*):
            The ETag of the file.

    Returns:
        The generated filename.
    """
    url_bytes = url.encode("utf-8")
    filename = sha256(url_bytes).hexdigest()

    if etag:
        etag_bytes = etag.encode("utf-8")
        filename += "." + sha256(etag_bytes).hexdigest()

    if url.endswith(".h5"):
        filename += ".h5"

    return filename


@_deprecate_method(version="0.26", message="Use `hf_hub_url` instead.")
def filename_to_url(
    filename,
    cache_dir: Optional[str] = None,
    legacy_cache_layout: bool = False,
) -> Tuple[str, str]:
    """
    Return the url and etag (which may be `None`) stored for `filename`. Raise
    `EnvironmentError` if `filename` or its stored metadata do not exist.

    Args:
        filename (`str`):
            The name of the file
        cache_dir (`str`, *optional*):
            The cache directory to use instead of the default one.
        legacy_cache_layout (`bool`, *optional*, defaults to `False`):
            If `True`, uses the legacy file cache layout i.e. just call `hf_hub_url`
            then `cached_download`. This is deprecated as the new cache layout is
            more powerful.
    """
    if not legacy_cache_layout:
        warnings.warn(
            "`filename_to_url` uses the legacy way cache file layout",
            FutureWarning,
        )

    if cache_dir is None:
        cache_dir = HF_HUB_CACHE
    if isinstance(cache_dir, Path):
        cache_dir = str(cache_dir)

    cache_path = os.path.join(cache_dir, filename)
    if not os.path.exists(cache_path):
        raise EnvironmentError(f"file {cache_path} not found")

    meta_path = cache_path + ".json"
    if not os.path.exists(meta_path):
        raise EnvironmentError(f"file {meta_path} not found")

    with open(meta_path, encoding="utf-8") as meta_file:
        metadata = json.load(meta_file)
    url = metadata["url"]
    etag = metadata["etag"]

    return url, etag


def _request_wrapper(
    method: HTTP_METHOD_T, url: str, *, follow_relative_redirects: bool = False, **params
) -> requests.Response:
    """Wrapper around requests methods to follow relative redirects if `follow_relative_redirects=True` even when
    `allow_redirection=False`.

    Args:
        method (`str`):
            HTTP method, such as 'GET' or 'HEAD'.
        url (`str`):
            The URL of the resource to fetch.
        follow_relative_redirects (`bool`, *optional*, defaults to `False`)
            If True, relative redirection (redirection to the same site) will be resolved even when `allow_redirection`
            kwarg is set to False. Useful when we want to follow a redirection to a renamed repository without
            following redirection to a CDN.
        **params (`dict`, *optional*):
            Params to pass to `requests.request`.
    """
    # Recursively follow relative redirects
    if follow_relative_redirects:
        response = _request_wrapper(
            method=method,
            url=url,
            follow_relative_redirects=False,
            **params,
        )

        # If redirection, we redirect only relative paths.
        # This is useful in case of a renamed repository.
        if 300 <= response.status_code <= 399:
            parsed_target = urlparse(response.headers["Location"])
            if parsed_target.netloc == "":
                # This means it is a relative 'location' headers, as allowed by RFC 7231.
                # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
                # We want to follow this relative redirect !
                #
                # Highly inspired by `resolve_redirects` from requests library.
                # See https://github.com/psf/requests/blob/main/requests/sessions.py#L159
                next_url = urlparse(url)._replace(path=parsed_target.path).geturl()
                return _request_wrapper(method=method, url=next_url, follow_relative_redirects=True, **params)
        return response

    # Perform request and return if status_code is not in the retry list.
    response = get_session().request(method=method, url=url, **params)
    hf_raise_for_status(response)
    return response


def http_get(
    url: str,
    temp_file: BinaryIO,
    *,
    proxies: Optional[Dict] = None,
    resume_size: float = 0,
    headers: Optional[Dict[str, str]] = None,
    expected_size: Optional[int] = None,
    displayed_filename: Optional[str] = None,
    _nb_retries: int = 5,
    _tqdm_bar: Optional[tqdm] = None,
) -> None:
    """
    Download a remote file. Do not gobble up errors, and will return errors tailored to the Hugging Face Hub.

    If ConnectionError (SSLError) or ReadTimeout happen while streaming data from the server, it is most likely a
    transient error (network outage?). We log a warning message and try to resume the download a few times before
    giving up. The method gives up after 5 attempts if no new data has being received from the server.

    Args:
        url (`str`):
            The URL of the file to download.
        temp_file (`BinaryIO`):
            The file-like object where to save the file.
        proxies (`dict`, *optional*):
            Dictionary mapping protocol to the URL of the proxy passed to `requests.request`.
        resume_size (`float`, *optional*):
            The number of bytes already downloaded. If set to 0 (default), the whole file is download. If set to a
            positive number, the download will resume at the given position.
        headers (`dict`, *optional*):
            Dictionary of HTTP Headers to send with the request.
        expected_size (`int`, *optional*):
            The expected size of the file to download. If set, the download will raise an error if the size of the
            received content is different from the expected one.
        displayed_filename (`str`, *optional*):
            The filename of the file that is being downloaded. Value is used only to display a nice progress bar. If
            not set, the filename is guessed from the URL or the `Content-Disposition` header.
    """
    hf_transfer = None
    if HF_HUB_ENABLE_HF_TRANSFER:
        if resume_size != 0:
            warnings.warn("'hf_transfer' does not support `resume_size`: falling back to regular download method")
        elif proxies is not None:
            warnings.warn("'hf_transfer' does not support `proxies`: falling back to regular download method")
        else:
            try:
                import hf_transfer  # type: ignore[no-redef]
            except ImportError:
                raise ValueError(
                    "Fast download using 'hf_transfer' is enabled"
                    " (HF_HUB_ENABLE_HF_TRANSFER=1) but 'hf_transfer' package is not"
                    " available in your environment. Try `pip install hf_transfer`."
                )

    initial_headers = headers
    headers = copy.deepcopy(headers) or {}
    if resume_size > 0:
        headers["Range"] = "bytes=%d-" % (resume_size,)

    r = _request_wrapper(
        method="GET", url=url, stream=True, proxies=proxies, headers=headers, timeout=HF_HUB_DOWNLOAD_TIMEOUT
    )
    hf_raise_for_status(r)
    content_length = r.headers.get("Content-Length")

    # NOTE: 'total' is the total number of bytes to download, not the number of bytes in the file.
    #       If the file is compressed, the number of bytes in the saved file will be higher than 'total'.
    total = resume_size + int(content_length) if content_length is not None else None

    if displayed_filename is None:
        displayed_filename = url
        content_disposition = r.headers.get("Content-Disposition")
        if content_disposition is not None:
            match = HEADER_FILENAME_PATTERN.search(content_disposition)
            if match is not None:
                # Means file is on CDN
                displayed_filename = match.groupdict()["filename"]

    # Truncate filename if too long to display
    if len(displayed_filename) > 40:
        displayed_filename = f"(…){displayed_filename[-40:]}"

    consistency_error_message = (
        f"Consistency check failed: file should be of size {expected_size} but has size"
        f" {{actual_size}} ({displayed_filename}).\nWe are sorry for the inconvenience. Please retry"
        " with `force_download=True`.\nIf the issue persists, please let us know by opening an issue "
        "on https://github.com/huggingface/huggingface_hub."
    )

    # Stream file to buffer
    progress_cm: tqdm = (
        tqdm(  # type: ignore[assignment]
            unit="B",
            unit_scale=True,
            total=total,
            initial=resume_size,
            desc=displayed_filename,
            disable=True if (logger.getEffectiveLevel() == logging.NOTSET) else None,
            # ^ set `disable=None` rather than `disable=False` by default to disable progress bar when no TTY attached
            # see https://github.com/huggingface/huggingface_hub/pull/2000
            name="huggingface_hub.http_get",
        )
        if _tqdm_bar is None
        else contextlib.nullcontext(_tqdm_bar)
        # ^ `contextlib.nullcontext` mimics a context manager that does nothing
        #   Makes it easier to use the same code path for both cases but in the later
        #   case, the progress bar is not closed when exiting the context manager.
    )

    with progress_cm as progress:
        if hf_transfer and total is not None and total > 5 * DOWNLOAD_CHUNK_SIZE:
            supports_callback = "callback" in inspect.signature(hf_transfer.download).parameters
            if not supports_callback:
                warnings.warn(
                    "You are using an outdated version of `hf_transfer`. "
                    "Consider upgrading to latest version to enable progress bars "
                    "using `pip install -U hf_transfer`."
                )
            try:
                hf_transfer.download(
                    url=url,
                    filename=temp_file.name,
                    max_files=HF_TRANSFER_CONCURRENCY,
                    chunk_size=DOWNLOAD_CHUNK_SIZE,
                    headers=headers,
                    parallel_failures=3,
                    max_retries=5,
                    **({"callback": progress.update} if supports_callback else {}),
                )
            except Exception as e:
                raise RuntimeError(
                    "An error occurred while downloading using `hf_transfer`. Consider"
                    " disabling HF_HUB_ENABLE_HF_TRANSFER for better error handling."
                ) from e
            if not supports_callback:
                progress.update(total)
            if expected_size is not None and expected_size != os.path.getsize(temp_file.name):
                raise EnvironmentError(
                    consistency_error_message.format(
                        actual_size=os.path.getsize(temp_file.name),
                    )
                )
            return
        new_resume_size = resume_size
        try:
            for chunk in r.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                if chunk:  # filter out keep-alive new chunks
                    progress.update(len(chunk))
                    temp_file.write(chunk)
                    new_resume_size += len(chunk)
                    # Some data has been downloaded from the server so we reset the number of retries.
                    _nb_retries = 5
        except (requests.ConnectionError, requests.ReadTimeout) as e:
            # If ConnectionError (SSLError) or ReadTimeout happen while streaming data from the server, it is most likely
            # a transient error (network outage?). We log a warning message and try to resume the download a few times
            # before giving up. Tre retry mechanism is basic but should be enough in most cases.
            if _nb_retries <= 0:
                logger.warning("Error while downloading from %s: %s\nMax retries exceeded.", url, str(e))
                raise
            logger.warning("Error while downloading from %s: %s\nTrying to resume download...", url, str(e))
            time.sleep(1)
            reset_sessions()  # In case of SSLError it's best to reset the shared requests.Session objects
            return http_get(
                url=url,
                temp_file=temp_file,
                proxies=proxies,
                resume_size=new_resume_size,
                headers=initial_headers,
                expected_size=expected_size,
                _nb_retries=_nb_retries - 1,
                _tqdm_bar=_tqdm_bar,
            )

    if expected_size is not None and expected_size != temp_file.tell():
        raise EnvironmentError(
            consistency_error_message.format(
                actual_size=temp_file.tell(),
            )
        )


@validate_hf_hub_args
@_deprecate_method(version="0.26", message="Use `hf_hub_download` instead.")
def cached_download(
    url: str,
    *,
    library_name: Optional[str] = None,
    library_version: Optional[str] = None,
    cache_dir: Union[str, Path, None] = None,
    user_agent: Union[Dict, str, None] = None,
    force_download: bool = False,
    force_filename: Optional[str] = None,
    proxies: Optional[Dict] = None,
    etag_timeout: float = DEFAULT_ETAG_TIMEOUT,
    resume_download: Optional[bool] = None,
    token: Union[bool, str, None] = None,
    local_files_only: bool = False,
    legacy_cache_layout: bool = False,
) -> str:
    """
    Download from a given URL and cache it if it's not already present in the
    local cache.

    Given a URL, this function looks for the corresponding file in the local
    cache. If it's not there, download it. Then return the path to the cached
    file.

    Will raise errors tailored to the Hugging Face Hub.

    Args:
        url (`str`):
            The path to the file to be downloaded.
        library_name (`str`, *optional*):
            The name of the library to which the object corresponds.
        library_version (`str`, *optional*):
            The version of the library.
        cache_dir (`str`, `Path`, *optional*):
            Path to the folder where cached files are stored.
        user_agent (`dict`, `str`, *optional*):
            The user-agent info in the form of a dictionary or a string.
        force_download (`bool`, *optional*, defaults to `False`):
            Whether the file should be downloaded even if it already exists in
            the local cache.
        force_filename (`str`, *optional*):
            Use this name instead of a generated file name.
        proxies (`dict`, *optional*):
            Dictionary mapping protocol to the URL of the proxy passed to
            `requests.request`.
        etag_timeout (`float`, *optional* defaults to `10`):
            When fetching ETag, how many seconds to wait for the server to send
            data before giving up which is passed to `requests.request`.
        token (`bool`, `str`, *optional*):
            A token to be used for the download.
                - If `True`, the token is read from the HuggingFace config
                  folder.
                - If a string, it's used as the authentication token.
        local_files_only (`bool`, *optional*, defaults to `False`):
            If `True`, avoid downloading the file and return the path to the
            local cached file if it exists.
        legacy_cache_layout (`bool`, *optional*, defaults to `False`):
            Set this parameter to `True` to mention that you'd like to continue
            the old cache layout. Putting this to `True` manually will not raise
            any warning when using `cached_download`. We recommend using
            `hf_hub_download` to take advantage of the new cache.

    Returns:
        Local path (string) of file or if networking is off, last version of
        file cached on disk.

    <Tip>

    Raises the following errors:

        - [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
          if `token=True` and the token cannot be found.
        - [`OSError`](https://docs.python.org/3/library/exceptions.html#OSError)
          if ETag cannot be determined.
        - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
          if some parameter value is invalid
        - [`~utils.RepositoryNotFoundError`]
          If the repository to download from cannot be found. This may be because it doesn't exist,
          or because it is set to `private` and you do not have access.
        - [`~utils.RevisionNotFoundError`]
          If the revision to download from cannot be found.
        - [`~utils.EntryNotFoundError`]
          If the file to download cannot be found.
        - [`~utils.LocalEntryNotFoundError`]
          If network is disabled or unavailable and file is not found in cache.

    </Tip>
    """
    if HF_HUB_ETAG_TIMEOUT != DEFAULT_ETAG_TIMEOUT:
        # Respect environment variable above user value
        etag_timeout = HF_HUB_ETAG_TIMEOUT

    if not legacy_cache_layout:
        warnings.warn(
            "'cached_download' is the legacy way to download files from the HF hub, please consider upgrading to"
            " 'hf_hub_download'",
            FutureWarning,
        )
    if resume_download is not None:
        warnings.warn(
            "`resume_download` is deprecated and will be removed in version 1.0.0. "
            "Downloads always resume when possible. "
            "If you want to force a new download, use `force_download=True`.",
            FutureWarning,
        )

    if cache_dir is None:
        cache_dir = HF_HUB_CACHE
    if isinstance(cache_dir, Path):
        cache_dir = str(cache_dir)

    os.makedirs(cache_dir, exist_ok=True)

    headers = build_hf_headers(
        token=token,
        library_name=library_name,
        library_version=library_version,
        user_agent=user_agent,
    )

    url_to_download = url
    etag = None
    expected_size = None
    if not local_files_only:
        try:
            # Temporary header: we want the full (decompressed) content size returned to be able to check the
            # downloaded file size
            headers["Accept-Encoding"] = "identity"
            r = _request_wrapper(
                method="HEAD",
                url=url,
                headers=headers,
                allow_redirects=False,
                follow_relative_redirects=True,
                proxies=proxies,
                timeout=etag_timeout,
            )
            headers.pop("Accept-Encoding", None)
            hf_raise_for_status(r)
            etag = r.headers.get(HUGGINGFACE_HEADER_X_LINKED_ETAG) or r.headers.get("ETag")
            # We favor a custom header indicating the etag of the linked resource, and
            # we fallback to the regular etag header.
            # If we don't have any of those, raise an error.
            if etag is None:
                raise FileMetadataError(
                    "Distant resource does not have an ETag, we won't be able to reliably ensure reproducibility."
                )
            # We get the expected size of the file, to check the download went well.
            expected_size = _int_or_none(r.headers.get("Content-Length"))
            # In case of a redirect, save an extra redirect on the request.get call,
            # and ensure we download the exact atomic version even if it changed
            # between the HEAD and the GET (unlikely, but hey).
            # Useful for lfs blobs that are stored on a CDN.
            if 300 <= r.status_code <= 399:
                url_to_download = r.headers["Location"]
                headers.pop("authorization", None)
                expected_size = None  # redirected -> can't know the expected size
        except (requests.exceptions.SSLError, requests.exceptions.ProxyError):
            # Actually raise for those subclasses of ConnectionError
            raise
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            OfflineModeIsEnabled,
        ):
            # Otherwise, our Internet connection is down.
            # etag is None
            pass

    filename = force_filename if force_filename is not None else url_to_filename(url, etag)

    # get cache path to put the file
    cache_path = os.path.join(cache_dir, filename)

    # etag is None == we don't have a connection or we passed local_files_only.
    # try to get the last downloaded one
    if etag is None:
        if os.path.exists(cache_path) and not force_download:
            return cache_path
        else:
            matching_files = [
                file
                for file in fnmatch.filter(os.listdir(cache_dir), filename.split(".")[0] + ".*")
                if not file.endswith(".json") and not file.endswith(".lock")
            ]
            if len(matching_files) > 0 and not force_download and force_filename is None:
                return os.path.join(cache_dir, matching_files[-1])
            else:
                # If files cannot be found and local_files_only=True,
                # the models might've been found if local_files_only=False
                # Notify the user about that
                if local_files_only:
                    raise LocalEntryNotFoundError(
                        "Cannot find the requested files in the cached path and"
                        " outgoing traffic has been disabled. To enable model look-ups"
                        " and downloads online, set 'local_files_only' to False."
                    )
                else:
                    raise LocalEntryNotFoundError(
                        "Connection error, and we cannot find the requested files in"
                        " the cached path. Please try again or make sure your Internet"
                        " connection is on."
                    )

    # From now on, etag is not None.
    if os.path.exists(cache_path) and not force_download:
        return cache_path

    # Prevent parallel downloads of the same file with a lock.
    lock_path = cache_path + ".lock"

    # Some Windows versions do not allow for paths longer than 255 characters.
    # In this case, we must specify it is an extended path by using the "\\?\" prefix.
    if os.name == "nt" and len(os.path.abspath(lock_path)) > 255:
        lock_path = "\\\\?\\" + os.path.abspath(lock_path)

    if os.name == "nt" and len(os.path.abspath(cache_path)) > 255:
        cache_path = "\\\\?\\" + os.path.abspath(cache_path)

    with WeakFileLock(lock_path):
        _download_to_tmp_and_move(
            incomplete_path=Path(cache_path + ".incomplete"),
            destination_path=Path(cache_path),
            url_to_download=url_to_download,
            proxies=proxies,
            headers=headers,
            expected_size=expected_size,
            filename=filename,
            force_download=force_download,
        )

        if force_filename is None:
            logger.info("creating metadata file for %s", cache_path)
            meta = {"url": url, "etag": etag}
            meta_path = cache_path + ".json"
            with open(meta_path, "w") as meta_file:
                json.dump(meta, meta_file)

    return cache_path


def _normalize_etag(etag: Optional[str]) -> Optional[str]:
    """Normalize ETag HTTP header, so it can be used to create nice filepaths.

    The HTTP spec allows two forms of ETag:
      ETag: W/"<etag_value>"
      ETag: "<etag_value>"

    For now, we only expect the second form from the server, but we want to be future-proof so we support both. For
    more context, see `TestNormalizeEtag` tests and https://github.com/huggingface/huggingface_hub/pull/1428.

    Args:
        etag (`str`, *optional*): HTTP header

    Returns:
        `str` or `None`: string that can be used as a nice directory name.
        Returns `None` if input is None.
    """
    if etag is None:
        return None
    return etag.lstrip("W/").strip('"')


def _create_relative_symlink(src: str, dst: str, new_blob: bool = False) -> None:
    """Alias method used in `transformers` conversion script."""
    return _create_symlink(src=src, dst=dst, new_blob=new_blob)


def _create_symlink(src: str, dst: str, new_blob: bool = False) -> None:
    """Create a symbolic link named dst pointing to src.

    By default, it will try to create a symlink using a relative path. Relative paths have 2 advantages:
    - If the cache_folder is moved (example: back-up on a shared drive), relative paths within the cache folder will
      not break.
    - Relative paths seems to be better handled on Windows. Issue was reported 3 times in less than a week when
      changing from relative to absolute paths. See https://github.com/huggingface/huggingface_hub/issues/1398,
      https://github.com/huggingface/diffusers/issues/2729 and https://github.com/huggingface/transformers/pull/22228.
      NOTE: The issue with absolute paths doesn't happen on admin mode.
    When creating a symlink from the cache to a local folder, it is possible that a relative path cannot be created.
    This happens when paths are not on the same volume. In that case, we use absolute paths.


    The result layout looks something like
        └── [ 128]  snapshots
            ├── [ 128]  2439f60ef33a0d46d85da5001d52aeda5b00ce9f
            │   ├── [  52]  README.md -> ../../../blobs/d7edf6bd2a681fb0175f7735299831ee1b22b812
            │   └── [  76]  pytorch_model.bin -> ../../../blobs/403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd

    If symlinks cannot be created on this platform (most likely to be Windows), the workaround is to avoid symlinks by
    having the actual file in `dst`. If it is a new file (`new_blob=True`), we move it to `dst`. If it is not a new file
    (`new_blob=False`), we don't know if the blob file is already referenced elsewhere. To avoid breaking existing
    cache, the file is duplicated on the disk.

    In case symlinks are not supported, a warning message is displayed to the user once when loading `huggingface_hub`.
    The warning message can be disabled with the `DISABLE_SYMLINKS_WARNING` environment variable.
    """
    try:
        os.remove(dst)
    except OSError:
        pass

    abs_src = os.path.abspath(os.path.expanduser(src))
    abs_dst = os.path.abspath(os.path.expanduser(dst))
    abs_dst_folder = os.path.dirname(abs_dst)

    # Use relative_dst in priority
    try:
        relative_src = os.path.relpath(abs_src, abs_dst_folder)
    except ValueError:
        # Raised on Windows if src and dst are not on the same volume. This is the case when creating a symlink to a
        # local_dir instead of within the cache directory.
        # See https://docs.python.org/3/library/os.path.html#os.path.relpath
        relative_src = None

    try:
        commonpath = os.path.commonpath([abs_src, abs_dst])
        _support_symlinks = are_symlinks_supported(commonpath)
    except ValueError:
        # Raised if src and dst are not on the same volume. Symlinks will still work on Linux/Macos.
        # See https://docs.python.org/3/library/os.path.html#os.path.commonpath
        _support_symlinks = os.name != "nt"
    except PermissionError:
        # Permission error means src and dst are not in the same volume (e.g. destination path has been provided
        # by the user via `local_dir`. Let's test symlink support there)
        _support_symlinks = are_symlinks_supported(abs_dst_folder)
    except OSError as e:
        # OS error (errno=30) means that the commonpath is readonly on Linux/MacOS.
        if e.errno == errno.EROFS:
            _support_symlinks = are_symlinks_supported(abs_dst_folder)
        else:
            raise

    # Symlinks are supported => let's create a symlink.
    if _support_symlinks:
        src_rel_or_abs = relative_src or abs_src
        logger.debug(f"Creating pointer from {src_rel_or_abs} to {abs_dst}")
        try:
            os.symlink(src_rel_or_abs, abs_dst)
            return
        except FileExistsError:
            if os.path.islink(abs_dst) and os.path.realpath(abs_dst) == os.path.realpath(abs_src):
                # `abs_dst` already exists and is a symlink to the `abs_src` blob. It is most likely that the file has
                # been cached twice concurrently (exactly between `os.remove` and `os.symlink`). Do nothing.
                return
            else:
                # Very unlikely to happen. Means a file `dst` has been created exactly between `os.remove` and
                # `os.symlink` and is not a symlink to the `abs_src` blob file. Raise exception.
                raise
        except PermissionError:
            # Permission error means src and dst are not in the same volume (e.g. download to local dir) and symlink
            # is supported on both volumes but not between them. Let's just make a hard copy in that case.
            pass

    # Symlinks are not supported => let's move or copy the file.
    if new_blob:
        logger.info(f"Symlink not supported. Moving file from {abs_src} to {abs_dst}")
        shutil.move(abs_src, abs_dst, copy_function=_copy_no_matter_what)
    else:
        logger.info(f"Symlink not supported. Copying file from {abs_src} to {abs_dst}")
        shutil.copyfile(abs_src, abs_dst)


def _cache_commit_hash_for_specific_revision(storage_folder: str, revision: str, commit_hash: str) -> None:
    """Cache reference between a revision (tag, branch or truncated commit hash) and the corresponding commit hash.

    Does nothing if `revision` is already a proper `commit_hash` or reference is already cached.
    """
    if revision != commit_hash:
        ref_path = Path(storage_folder) / "refs" / revision
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        if not ref_path.exists() or commit_hash != ref_path.read_text():
            # Update ref only if has been updated. Could cause useless error in case
            # repo is already cached and user doesn't have write access to cache folder.
            # See https://github.com/huggingface/huggingface_hub/issues/1216.
            ref_path.write_text(commit_hash)


@validate_hf_hub_args
def repo_folder_name(*, repo_id: str, repo_type: str) -> str:
    """Return a serialized version of a hf.co repo name and type, safe for disk storage
    as a single non-nested folder.

    Example: models--julien-c--EsperBERTo-small
    """
    # remove all `/` occurrences to correctly convert repo to directory name
    parts = [f"{repo_type}s", *repo_id.split("/")]
    return REPO_ID_SEPARATOR.join(parts)


def _check_disk_space(expected_size: int, target_dir: Union[str, Path]) -> None:
    """Check disk usage and log a warning if there is not enough disk space to download the file.

    Args:
        expected_size (`int`):
            The expected size of the file in bytes.
        target_dir (`str`):
            The directory where the file will be stored after downloading.
    """

    target_dir = Path(target_dir)  # format as `Path`
    for path in [target_dir] + list(target_dir.parents):  # first check target_dir, then each parents one by one
        try:
            target_dir_free = shutil.disk_usage(path).free
            if target_dir_free < expected_size:
                warnings.warn(
                    "Not enough free disk space to download the file. "
                    f"The expected file size is: {expected_size / 1e6:.2f} MB. "
                    f"The target location {target_dir} only has {target_dir_free / 1e6:.2f} MB free disk space."
                )
            return
        except OSError:  # raise on anything: file does not exist or space disk cannot be checked
            pass


@_deprecate_arguments(
    version="0.26.0",
    deprecated_args=["legacy_cache_layout"],
    custom_message=(
        "Legacy cache layout has been deprecated since August 2022 and will soon be removed. "
        "See https://huggingface.co/docs/huggingface_hub/guides/manage-cache for more details."
    ),
)
@validate_hf_hub_args
def hf_hub_download(
    repo_id: str,
    filename: str,
    *,
    subfolder: Optional[str] = None,
    repo_type: Optional[str] = None,
    revision: Optional[str] = None,
    library_name: Optional[str] = None,
    library_version: Optional[str] = None,
    cache_dir: Union[str, Path, None] = None,
    local_dir: Union[str, Path, None] = None,
    user_agent: Union[Dict, str, None] = None,
    force_download: bool = False,
    proxies: Optional[Dict] = None,
    etag_timeout: float = DEFAULT_ETAG_TIMEOUT,
    token: Union[bool, str, None] = None,
    local_files_only: bool = False,
    headers: Optional[Dict[str, str]] = None,
    endpoint: Optional[str] = None,
    # Deprecated args
    legacy_cache_layout: bool = False,
    resume_download: Optional[bool] = None,
    force_filename: Optional[str] = None,
    local_dir_use_symlinks: Union[bool, Literal["auto"]] = "auto",
) -> str:
    """Download a given file if it's not already present in the local cache.

    The new cache file layout looks like this:
    - The cache directory contains one subfolder per repo_id (namespaced by repo type)
    - inside each repo folder:
        - refs is a list of the latest known revision => commit_hash pairs
        - blobs contains the actual file blobs (identified by their git-sha or sha256, depending on
          whether they're LFS files or not)
        - snapshots contains one subfolder per commit, each "commit" contains the subset of the files
          that have been resolved at that particular commit. Each filename is a symlink to the blob
          at that particular commit.

    ```
    [  96]  .
    └── [ 160]  models--julien-c--EsperBERTo-small
        ├── [ 160]  blobs
        │   ├── [321M]  403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd
        │   ├── [ 398]  7cb18dc9bafbfcf74629a4b760af1b160957a83e
        │   └── [1.4K]  d7edf6bd2a681fb0175f7735299831ee1b22b812
        ├── [  96]  refs
        │   └── [  40]  main
        └── [ 128]  snapshots
            ├── [ 128]  2439f60ef33a0d46d85da5001d52aeda5b00ce9f
            │   ├── [  52]  README.md -> ../../blobs/d7edf6bd2a681fb0175f7735299831ee1b22b812
            │   └── [  76]  pytorch_model.bin -> ../../blobs/403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd
            └── [ 128]  bbc77c8132af1cc5cf678da3f1ddf2de43606d48
                ├── [  52]  README.md -> ../../blobs/7cb18dc9bafbfcf74629a4b760af1b160957a83e
                └── [  76]  pytorch_model.bin -> ../../blobs/403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd
    ```

    If `local_dir` is provided, the file structure from the repo will be replicated in this location. When using this
    option, the `cache_dir` will not be used and a `.cache/huggingface/` folder will be created at the root of `local_dir`
    to store some metadata related to the downloaded files. While this mechanism is not as robust as the main
    cache-system, it's optimized for regularly pulling the latest version of a repository.

    Args:
        repo_id (`str`):
            A user or an organization name and a repo name separated by a `/`.
        filename (`str`):
            The name of the file in the repo.
        subfolder (`str`, *optional*):
            An optional value corresponding to a folder inside the model repo.
        repo_type (`str`, *optional*):
            Set to `"dataset"` or `"space"` if downloading from a dataset or space,
            `None` or `"model"` if downloading from a model. Default is `None`.
        revision (`str`, *optional*):
            An optional Git revision id which can be a branch name, a tag, or a
            commit hash.
        library_name (`str`, *optional*):
            The name of the library to which the object corresponds.
        library_version (`str`, *optional*):
            The version of the library.
        cache_dir (`str`, `Path`, *optional*):
            Path to the folder where cached files are stored.
        local_dir (`str` or `Path`, *optional*):
            If provided, the downloaded file will be placed under this directory.
        user_agent (`dict`, `str`, *optional*):
            The user-agent info in the form of a dictionary or a string.
        force_download (`bool`, *optional*, defaults to `False`):
            Whether the file should be downloaded even if it already exists in
            the local cache.
        proxies (`dict`, *optional*):
            Dictionary mapping protocol to the URL of the proxy passed to
            `requests.request`.
        etag_timeout (`float`, *optional*, defaults to `10`):
            When fetching ETag, how many seconds to wait for the server to send
            data before giving up which is passed to `requests.request`.
        token (`str`, `bool`, *optional*):
            A token to be used for the download.
                - If `True`, the token is read from the HuggingFace config
                  folder.
                - If a string, it's used as the authentication token.
        local_files_only (`bool`, *optional*, defaults to `False`):
            If `True`, avoid downloading the file and return the path to the
            local cached file if it exists.
        headers (`dict`, *optional*):
            Additional headers to be sent with the request.
        legacy_cache_layout (`bool`, *optional*, defaults to `False`):
            If `True`, uses the legacy file cache layout i.e. just call [`hf_hub_url`]
            then `cached_download`. This is deprecated as the new cache layout is
            more powerful.

    Returns:
        `str`: Local path of file or if networking is off, last version of file cached on disk.

    Raises:
        [`~utils.RepositoryNotFoundError`]
            If the repository to download from cannot be found. This may be because it doesn't exist,
            or because it is set to `private` and you do not have access.
        [`~utils.RevisionNotFoundError`]
            If the revision to download from cannot be found.
        [`~utils.EntryNotFoundError`]
            If the file to download cannot be found.
        [`~utils.LocalEntryNotFoundError`]
            If network is disabled or unavailable and file is not found in cache.
        [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
            If `token=True` but the token cannot be found.
        [`OSError`](https://docs.python.org/3/library/exceptions.html#OSError)
            If ETag cannot be determined.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If some parameter value is invalid.

    """
    if HF_HUB_ETAG_TIMEOUT != DEFAULT_ETAG_TIMEOUT:
        # Respect environment variable above user value
        etag_timeout = HF_HUB_ETAG_TIMEOUT

    if force_filename is not None:
        warnings.warn(
            "The `force_filename` parameter is deprecated as a new caching system, "
            "which keeps the filenames as they are on the Hub, is now in place.",
            FutureWarning,
        )
        legacy_cache_layout = True
    if resume_download is not None:
        warnings.warn(
            "`resume_download` is deprecated and will be removed in version 1.0.0. "
            "Downloads always resume when possible. "
            "If you want to force a new download, use `force_download=True`.",
            FutureWarning,
        )

    if legacy_cache_layout:
        url = hf_hub_url(
            repo_id,
            filename,
            subfolder=subfolder,
            repo_type=repo_type,
            revision=revision,
            endpoint=endpoint,
        )

        return cached_download(
            url,
            library_name=library_name,
            library_version=library_version,
            cache_dir=cache_dir,
            user_agent=user_agent,
            force_download=force_download,
            force_filename=force_filename,
            proxies=proxies,
            etag_timeout=etag_timeout,
            token=token,
            local_files_only=local_files_only,
            legacy_cache_layout=legacy_cache_layout,
        )

    if cache_dir is None:
        cache_dir = HF_HUB_CACHE
    if revision is None:
        revision = DEFAULT_REVISION
    if isinstance(cache_dir, Path):
        cache_dir = str(cache_dir)
    if isinstance(local_dir, Path):
        local_dir = str(local_dir)

    if subfolder == "":
        subfolder = None
    if subfolder is not None:
        # This is used to create a URL, and not a local path, hence the forward slash.
        filename = f"{subfolder}/{filename}"

    if repo_type is None:
        repo_type = "model"
    if repo_type not in REPO_TYPES:
        raise ValueError(f"Invalid repo type: {repo_type}. Accepted repo types are: {str(REPO_TYPES)}")

    headers = build_hf_headers(
        token=token,
        library_name=library_name,
        library_version=library_version,
        user_agent=user_agent,
        headers=headers,
    )

    if local_dir is not None:
        if local_dir_use_symlinks != "auto":
            warnings.warn(
                "`local_dir_use_symlinks` parameter is deprecated and will be ignored. "
                "The process to download files to a local folder has been updated and do "
                "not rely on symlinks anymore. You only need to pass a destination folder "
                "as`local_dir`.\n"
                "For more details, check out https://huggingface.co/docs/huggingface_hub/main/en/guides/download#download-files-to-local-folder."
            )

        return _hf_hub_download_to_local_dir(
            # Destination
            local_dir=local_dir,
            # File info
            repo_id=repo_id,
            repo_type=repo_type,
            filename=filename,
            revision=revision,
            # HTTP info
            endpoint=endpoint,
            etag_timeout=etag_timeout,
            headers=headers,
            proxies=proxies,
            token=token,
            # Additional options
            cache_dir=cache_dir,
            force_download=force_download,
            local_files_only=local_files_only,
        )
    else:
        return _hf_hub_download_to_cache_dir(
            # Destination
            cache_dir=cache_dir,
            # File info
            repo_id=repo_id,
            filename=filename,
            repo_type=repo_type,
            revision=revision,
            # HTTP info
            endpoint=endpoint,
            etag_timeout=etag_timeout,
            headers=headers,
            proxies=proxies,
            token=token,
            # Additional options
            local_files_only=local_files_only,
            force_download=force_download,
        )


def _hf_hub_download_to_cache_dir(
    *,
    # Destination
    cache_dir: str,
    # File info
    repo_id: str,
    filename: str,
    repo_type: str,
    revision: str,
    # HTTP info
    endpoint: Optional[str],
    etag_timeout: float,
    headers: Dict[str, str],
    proxies: Optional[Dict],
    token: Optional[Union[bool, str]],
    # Additional options
    local_files_only: bool,
    force_download: bool,
) -> str:
    """Download a given file to a cache folder, if not already present.

    Method should not be called directly. Please use `hf_hub_download` instead.
    """
    locks_dir = os.path.join(cache_dir, ".locks")
    storage_folder = os.path.join(cache_dir, repo_folder_name(repo_id=repo_id, repo_type=repo_type))

    # cross platform transcription of filename, to be used as a local file path.
    relative_filename = os.path.join(*filename.split("/"))
    if os.name == "nt":
        if relative_filename.startswith("..\\") or "\\..\\" in relative_filename:
            raise ValueError(
                f"Invalid filename: cannot handle filename '{relative_filename}' on Windows. Please ask the repository"
                " owner to rename this file."
            )

    # if user provides a commit_hash and they already have the file on disk, shortcut everything.
    if REGEX_COMMIT_HASH.match(revision):
        pointer_path = _get_pointer_path(storage_folder, revision, relative_filename)
        if os.path.exists(pointer_path) and not force_download:
            return pointer_path

    # Try to get metadata (etag, commit_hash, url, size) from the server.
    # If we can't, a HEAD request error is returned.
    (url_to_download, etag, commit_hash, expected_size, head_call_error) = _get_metadata_or_catch_error(
        repo_id=repo_id,
        filename=filename,
        repo_type=repo_type,
        revision=revision,
        endpoint=endpoint,
        proxies=proxies,
        etag_timeout=etag_timeout,
        headers=headers,
        token=token,
        local_files_only=local_files_only,
        storage_folder=storage_folder,
        relative_filename=relative_filename,
    )

    # etag can be None for several reasons:
    # 1. we passed local_files_only.
    # 2. we don't have a connection
    # 3. Hub is down (HTTP 500, 503, 504)
    # 4. repo is not found -for example private or gated- and invalid/missing token sent
    # 5. Hub is blocked by a firewall or proxy is not set correctly.
    # => Try to get the last downloaded one from the specified revision.
    #
    # If the specified revision is a commit hash, look inside "snapshots".
    # If the specified revision is a branch or tag, look inside "refs".
    if head_call_error is not None:
        # Couldn't make a HEAD call => let's try to find a local file
        if not force_download:
            commit_hash = None
            if REGEX_COMMIT_HASH.match(revision):
                commit_hash = revision
            else:
                ref_path = os.path.join(storage_folder, "refs", revision)
                if os.path.isfile(ref_path):
                    with open(ref_path) as f:
                        commit_hash = f.read()

            # Return pointer file if exists
            if commit_hash is not None:
                pointer_path = _get_pointer_path(storage_folder, commit_hash, relative_filename)
                if os.path.exists(pointer_path) and not force_download:
                    return pointer_path

        # Otherwise, raise appropriate error
        _raise_on_head_call_error(head_call_error, force_download, local_files_only)

    # From now on, etag, commit_hash, url and size are not None.
    assert etag is not None, "etag must have been retrieved from server"
    assert commit_hash is not None, "commit_hash must have been retrieved from server"
    assert url_to_download is not None, "file location must have been retrieved from server"
    assert expected_size is not None, "expected_size must have been retrieved from server"
    blob_path = os.path.join(storage_folder, "blobs", etag)
    pointer_path = _get_pointer_path(storage_folder, commit_hash, relative_filename)

    os.makedirs(os.path.dirname(blob_path), exist_ok=True)
    os.makedirs(os.path.dirname(pointer_path), exist_ok=True)

    # if passed revision is not identical to commit_hash
    # then revision has to be a branch name or tag name.
    # In that case store a ref.
    _cache_commit_hash_for_specific_revision(storage_folder, revision, commit_hash)

    # If file already exists, return it (except if force_download=True)
    if not force_download:
        if os.path.exists(pointer_path):
            return pointer_path

        if os.path.exists(blob_path):
            # we have the blob already, but not the pointer
            _create_symlink(blob_path, pointer_path, new_blob=False)
            return pointer_path

    # Prevent parallel downloads of the same file with a lock.
    # etag could be duplicated across repos,
    lock_path = os.path.join(locks_dir, repo_folder_name(repo_id=repo_id, repo_type=repo_type), f"{etag}.lock")

    # Some Windows versions do not allow for paths longer than 255 characters.
    # In this case, we must specify it as an extended path by using the "\\?\" prefix.
    if os.name == "nt" and len(os.path.abspath(lock_path)) > 255:
        lock_path = "\\\\?\\" + os.path.abspath(lock_path)

    if os.name == "nt" and len(os.path.abspath(blob_path)) > 255:
        blob_path = "\\\\?\\" + os.path.abspath(blob_path)

    Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
    with WeakFileLock(lock_path):
        _download_to_tmp_and_move(
            incomplete_path=Path(blob_path + ".incomplete"),
            destination_path=Path(blob_path),
            url_to_download=url_to_download,
            proxies=proxies,
            headers=headers,
            expected_size=expected_size,
            filename=filename,
            force_download=force_download,
        )
        _create_symlink(blob_path, pointer_path, new_blob=True)

    return pointer_path


def _hf_hub_download_to_local_dir(
    *,
    # Destination
    local_dir: Union[str, Path],
    # File info
    repo_id: str,
    repo_type: str,
    filename: str,
    revision: str,
    # HTTP info
    endpoint: Optional[str],
    etag_timeout: float,
    headers: Dict[str, str],
    proxies: Optional[Dict],
    token: Union[bool, str, None],
    # Additional options
    cache_dir: str,
    force_download: bool,
    local_files_only: bool,
) -> str:
    """Download a given file to a local folder, if not already present.

    Method should not be called directly. Please use `hf_hub_download` instead.
    """
    # Some Windows versions do not allow for paths longer than 255 characters.
    # In this case, we must specify it as an extended path by using the "\\?\" prefix.
    if os.name == "nt" and len(os.path.abspath(local_dir)) > 255:
        local_dir = "\\\\?\\" + os.path.abspath(local_dir)
    local_dir = Path(local_dir)
    paths = get_local_download_paths(local_dir=local_dir, filename=filename)
    local_metadata = read_download_metadata(local_dir=local_dir, filename=filename)

    # Local file exists + metadata exists + commit_hash matches => return file
    if (
        not force_download
        and REGEX_COMMIT_HASH.match(revision)
        and paths.file_path.is_file()
        and local_metadata is not None
        and local_metadata.commit_hash == revision
    ):
        return str(paths.file_path)

    # Local file doesn't exist or commit_hash doesn't match => we need the etag
    (url_to_download, etag, commit_hash, expected_size, head_call_error) = _get_metadata_or_catch_error(
        repo_id=repo_id,
        filename=filename,
        repo_type=repo_type,
        revision=revision,
        endpoint=endpoint,
        proxies=proxies,
        etag_timeout=etag_timeout,
        headers=headers,
        token=token,
        local_files_only=local_files_only,
    )

    if head_call_error is not None:
        # No HEAD call but local file exists => default to local file
        if not force_download and paths.file_path.is_file():
            logger.warning(
                f"Couldn't access the Hub to check for update but local file already exists. Defaulting to existing file. (error: {head_call_error})"
            )
            return str(paths.file_path)
        # Otherwise => raise
        _raise_on_head_call_error(head_call_error, force_download, local_files_only)

    # From now on, etag, commit_hash, url and size are not None.
    assert etag is not None, "etag must have been retrieved from server"
    assert commit_hash is not None, "commit_hash must have been retrieved from server"
    assert url_to_download is not None, "file location must have been retrieved from server"
    assert expected_size is not None, "expected_size must have been retrieved from server"

    # Local file exists => check if it's up-to-date
    if not force_download and paths.file_path.is_file():
        # etag matches => update metadata and return file
        if local_metadata is not None and local_metadata.etag == etag:
            write_download_metadata(local_dir=local_dir, filename=filename, commit_hash=commit_hash, etag=etag)
            return str(paths.file_path)

        # metadata is outdated + etag is a sha256
        # => means it's an LFS file (large)
        # => let's compute local hash and compare
        # => if match, update metadata and return file
        if local_metadata is None and REGEX_SHA256.match(etag) is not None:
            with open(paths.file_path, "rb") as f:
                file_hash = sha_fileobj(f).hex()
            if file_hash == etag:
                write_download_metadata(local_dir=local_dir, filename=filename, commit_hash=commit_hash, etag=etag)
                return str(paths.file_path)

    # Local file doesn't exist or etag isn't a match => retrieve file from remote (or cache)

    # If we are lucky enough, the file is already in the cache => copy it
    if not force_download:
        cached_path = try_to_load_from_cache(
            repo_id=repo_id,
            filename=filename,
            cache_dir=cache_dir,
            revision=commit_hash,
            repo_type=repo_type,
        )
        if isinstance(cached_path, str):
            with WeakFileLock(paths.lock_path):
                paths.file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cached_path, paths.file_path)
            write_download_metadata(local_dir=local_dir, filename=filename, commit_hash=commit_hash, etag=etag)
            return str(paths.file_path)

    # Otherwise, let's download the file!
    with WeakFileLock(paths.lock_path):
        paths.file_path.unlink(missing_ok=True)  # delete outdated file first
        _download_to_tmp_and_move(
            incomplete_path=paths.incomplete_path(etag),
            destination_path=paths.file_path,
            url_to_download=url_to_download,
            proxies=proxies,
            headers=headers,
            expected_size=expected_size,
            filename=filename,
            force_download=force_download,
        )

    write_download_metadata(local_dir=local_dir, filename=filename, commit_hash=commit_hash, etag=etag)
    return str(paths.file_path)


@validate_hf_hub_args
def try_to_load_from_cache(
    repo_id: str,
    filename: str,
    cache_dir: Union[str, Path, None] = None,
    revision: Optional[str] = None,
    repo_type: Optional[str] = None,
) -> Union[str, _CACHED_NO_EXIST_T, None]:
    """
    Explores the cache to return the latest cached file for a given revision if found.

    This function will not raise any exception if the file in not cached.

    Args:
        cache_dir (`str` or `os.PathLike`):
            The folder where the cached files lie.
        repo_id (`str`):
            The ID of the repo on huggingface.co.
        filename (`str`):
            The filename to look for inside `repo_id`.
        revision (`str`, *optional*):
            The specific model version to use. Will default to `"main"` if it's not provided and no `commit_hash` is
            provided either.
        repo_type (`str`, *optional*):
            The type of the repository. Will default to `"model"`.

    Returns:
        `Optional[str]` or `_CACHED_NO_EXIST`:
            Will return `None` if the file was not cached. Otherwise:
            - The exact path to the cached file if it's found in the cache
            - A special value `_CACHED_NO_EXIST` if the file does not exist at the given commit hash and this fact was
              cached.

    Example:

    ```python
    from huggingface_hub import try_to_load_from_cache, _CACHED_NO_EXIST

    filepath = try_to_load_from_cache()
    if isinstance(filepath, str):
        # file exists and is cached
        ...
    elif filepath is _CACHED_NO_EXIST:
        # non-existence of file is cached
        ...
    else:
        # file is not cached
        ...
    ```
    """
    if revision is None:
        revision = "main"
    if repo_type is None:
        repo_type = "model"
    if repo_type not in REPO_TYPES:
        raise ValueError(f"Invalid repo type: {repo_type}. Accepted repo types are: {str(REPO_TYPES)}")
    if cache_dir is None:
        cache_dir = HF_HUB_CACHE

    object_id = repo_id.replace("/", "--")
    repo_cache = os.path.join(cache_dir, f"{repo_type}s--{object_id}")
    if not os.path.isdir(repo_cache):
        # No cache for this model
        return None

    refs_dir = os.path.join(repo_cache, "refs")
    snapshots_dir = os.path.join(repo_cache, "snapshots")
    no_exist_dir = os.path.join(repo_cache, ".no_exist")

    # Resolve refs (for instance to convert main to the associated commit sha)
    if os.path.isdir(refs_dir):
        revision_file = os.path.join(refs_dir, revision)
        if os.path.isfile(revision_file):
            with open(revision_file) as f:
                revision = f.read()

    # Check if file is cached as "no_exist"
    if os.path.isfile(os.path.join(no_exist_dir, revision, filename)):
        return _CACHED_NO_EXIST

    # Check if revision folder exists
    if not os.path.exists(snapshots_dir):
        return None
    cached_shas = os.listdir(snapshots_dir)
    if revision not in cached_shas:
        # No cache for this revision and we won't try to return a random revision
        return None

    # Check if file exists in cache
    cached_file = os.path.join(snapshots_dir, revision, filename)
    return cached_file if os.path.isfile(cached_file) else None


@validate_hf_hub_args
def get_hf_file_metadata(
    url: str,
    token: Union[bool, str, None] = None,
    proxies: Optional[Dict] = None,
    timeout: Optional[float] = DEFAULT_REQUEST_TIMEOUT,
    library_name: Optional[str] = None,
    library_version: Optional[str] = None,
    user_agent: Union[Dict, str, None] = None,
    headers: Optional[Dict[str, str]] = None,
) -> HfFileMetadata:
    """Fetch metadata of a file versioned on the Hub for a given url.

    Args:
        url (`str`):
            File url, for example returned by [`hf_hub_url`].
        token (`str` or `bool`, *optional*):
            A token to be used for the download.
                - If `True`, the token is read from the HuggingFace config
                  folder.
                - If `False` or `None`, no token is provided.
                - If a string, it's used as the authentication token.
        proxies (`dict`, *optional*):
            Dictionary mapping protocol to the URL of the proxy passed to
            `requests.request`.
        timeout (`float`, *optional*, defaults to 10):
            How many seconds to wait for the server to send metadata before giving up.
        library_name (`str`, *optional*):
            The name of the library to which the object corresponds.
        library_version (`str`, *optional*):
            The version of the library.
        user_agent (`dict`, `str`, *optional*):
            The user-agent info in the form of a dictionary or a string.
        headers (`dict`, *optional*):
            Additional headers to be sent with the request.

    Returns:
        A [`HfFileMetadata`] object containing metadata such as location, etag, size and
        commit_hash.
    """
    headers = build_hf_headers(
        token=token,
        library_name=library_name,
        library_version=library_version,
        user_agent=user_agent,
        headers=headers,
    )
    headers["Accept-Encoding"] = "identity"  # prevent any compression => we want to know the real size of the file

    # Retrieve metadata
    r = _request_wrapper(
        method="HEAD",
        url=url,
        headers=headers,
        allow_redirects=False,
        follow_relative_redirects=True,
        proxies=proxies,
        timeout=timeout,
    )
    hf_raise_for_status(r)

    # Return
    return HfFileMetadata(
        commit_hash=r.headers.get(HUGGINGFACE_HEADER_X_REPO_COMMIT),
        # We favor a custom header indicating the etag of the linked resource, and
        # we fallback to the regular etag header.
        etag=_normalize_etag(r.headers.get(HUGGINGFACE_HEADER_X_LINKED_ETAG) or r.headers.get("ETag")),
        # Either from response headers (if redirected) or defaults to request url
        # Do not use directly `url`, as `_request_wrapper` might have followed relative
        # redirects.
        location=r.headers.get("Location") or r.request.url,  # type: ignore
        size=_int_or_none(r.headers.get(HUGGINGFACE_HEADER_X_LINKED_SIZE) or r.headers.get("Content-Length")),
    )


def _get_metadata_or_catch_error(
    *,
    repo_id: str,
    filename: str,
    repo_type: str,
    revision: str,
    endpoint: Optional[str],
    proxies: Optional[Dict],
    etag_timeout: Optional[float],
    headers: Dict[str, str],  # mutated inplace!
    token: Union[bool, str, None],
    local_files_only: bool,
    relative_filename: Optional[str] = None,  # only used to store `.no_exists` in cache
    storage_folder: Optional[str] = None,  # only used to store `.no_exists` in cache
) -> Union[
    # Either an exception is caught and returned
    Tuple[None, None, None, None, Exception],
    # Or the metadata is returned as
    # `(url_to_download, etag, commit_hash, expected_size, None)`
    Tuple[str, str, str, int, None],
]:
    """Get metadata for a file on the Hub, safely handling network issues.

    Returns either the etag, commit_hash and expected size of the file, or the error
    raised while fetching the metadata.

    NOTE: This function mutates `headers` inplace! It removes the `authorization` header
          if the file is a LFS blob and the domain of the url is different from the
          domain of the location (typically an S3 bucket).
    """
    if local_files_only:
        return (
            None,
            None,
            None,
            None,
            OfflineModeIsEnabled(
                f"Cannot access file since 'local_files_only=True' as been set. (repo_id: {repo_id}, repo_type: {repo_type}, revision: {revision}, filename: {filename})"
            ),
        )

    url = url = hf_hub_url(repo_id, filename, repo_type=repo_type, revision=revision, endpoint=endpoint)
    url_to_download: str = url
    etag: Optional[str] = None
    commit_hash: Optional[str] = None
    expected_size: Optional[int] = None
    head_error_call: Optional[Exception] = None

    # Try to get metadata from the server.
    # Do not raise yet if the file is not found or not accessible.
    if not local_files_only:
        try:
            try:
                metadata = get_hf_file_metadata(
                    url=url, proxies=proxies, timeout=etag_timeout, headers=headers, token=token
                )
            except EntryNotFoundError as http_error:
                if storage_folder is not None and relative_filename is not None:
                    # Cache the non-existence of the file
                    commit_hash = http_error.response.headers.get(HUGGINGFACE_HEADER_X_REPO_COMMIT)
                    if commit_hash is not None:
                        no_exist_file_path = Path(storage_folder) / ".no_exist" / commit_hash / relative_filename
                        no_exist_file_path.parent.mkdir(parents=True, exist_ok=True)
                        no_exist_file_path.touch()
                        _cache_commit_hash_for_specific_revision(storage_folder, revision, commit_hash)
                raise

            # Commit hash must exist
            commit_hash = metadata.commit_hash
            if commit_hash is None:
                raise FileMetadataError(
                    "Distant resource does not seem to be on huggingface.co. It is possible that a configuration issue"
                    " prevents you from downloading resources from https://huggingface.co. Please check your firewall"
                    " and proxy settings and make sure your SSL certificates are updated."
                )

            # Etag must exist
            # If we don't have any of those, raise an error.
            etag = metadata.etag
            if etag is None:
                raise FileMetadataError(
                    "Distant resource does not have an ETag, we won't be able to reliably ensure reproducibility."
                )

            # Size must exist
            expected_size = metadata.size
            if expected_size is None:
                raise FileMetadataError("Distant resource does not have a Content-Length.")

            # In case of a redirect, save an extra redirect on the request.get call,
            # and ensure we download the exact atomic version even if it changed
            # between the HEAD and the GET (unlikely, but hey).
            #
            # If url domain is different => we are downloading from a CDN => url is signed => don't send auth
            # If url domain is the same => redirect due to repo rename AND downloading a regular file => keep auth
            if url != metadata.location:
                url_to_download = metadata.location
                if urlparse(url).netloc != urlparse(metadata.location).netloc:
                    # Remove authorization header when downloading a LFS blob
                    headers.pop("authorization", None)
        except (requests.exceptions.SSLError, requests.exceptions.ProxyError):
            # Actually raise for those subclasses of ConnectionError
            raise
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            OfflineModeIsEnabled,
        ) as error:
            # Otherwise, our Internet connection is down.
            # etag is None
            head_error_call = error
        except (RevisionNotFoundError, EntryNotFoundError):
            # The repo was found but the revision or entry doesn't exist on the Hub (never existed or got deleted)
            raise
        except requests.HTTPError as error:
            # Multiple reasons for an http error:
            # - Repository is private and invalid/missing token sent
            # - Repository is gated and invalid/missing token sent
            # - Hub is down (error 500 or 504)
            # => let's switch to 'local_files_only=True' to check if the files are already cached.
            #    (if it's not the case, the error will be re-raised)
            head_error_call = error
        except FileMetadataError as error:
            # Multiple reasons for a FileMetadataError:
            # - Wrong network configuration (proxy, firewall, SSL certificates)
            # - Inconsistency on the Hub
            # => let's switch to 'local_files_only=True' to check if the files are already cached.
            #    (if it's not the case, the error will be re-raised)
            head_error_call = error

    if not (local_files_only or etag is not None or head_error_call is not None):
        raise RuntimeError("etag is empty due to uncovered problems")

    return (url_to_download, etag, commit_hash, expected_size, head_error_call)  # type: ignore [return-value]


def _raise_on_head_call_error(head_call_error: Exception, force_download: bool, local_files_only: bool) -> NoReturn:
    """Raise an appropriate error when the HEAD call failed and we cannot locate a local file."""

    # No head call => we cannot force download.
    if force_download:
        if local_files_only:
            raise ValueError("Cannot pass 'force_download=True' and 'local_files_only=True' at the same time.")
        elif isinstance(head_call_error, OfflineModeIsEnabled):
            raise ValueError("Cannot pass 'force_download=True' when offline mode is enabled.") from head_call_error
        else:
            raise ValueError("Force download failed due to the above error.") from head_call_error

    # No head call + couldn't find an appropriate file on disk => raise an error.
    if local_files_only:
        raise LocalEntryNotFoundError(
            "Cannot find the requested files in the disk cache and outgoing traffic has been disabled. To enable"
            " hf.co look-ups and downloads online, set 'local_files_only' to False."
        )
    elif isinstance(head_call_error, RepositoryNotFoundError) or isinstance(head_call_error, GatedRepoError):
        # Repo not found or gated => let's raise the actual error
        raise head_call_error
    else:
        # Otherwise: most likely a connection issue or Hub downtime => let's warn the user
        raise LocalEntryNotFoundError(
            "An error happened while trying to locate the file on the Hub and we cannot find the requested files"
            " in the local cache. Please check your connection and try again or make sure your Internet connection"
            " is on."
        ) from head_call_error


def _download_to_tmp_and_move(
    incomplete_path: Path,
    destination_path: Path,
    url_to_download: str,
    proxies: Optional[Dict],
    headers: Dict[str, str],
    expected_size: Optional[int],
    filename: str,
    force_download: bool,
) -> None:
    """Download content from a URL to a destination path.

    Internal logic:
    - return early if file is already downloaded
    - resume download if possible (from incomplete file)
    - do not resume download if `force_download=True` or `HF_HUB_ENABLE_HF_TRANSFER=True`
    - check disk space before downloading
    - download content to a temporary file
    - set correct permissions on temporary file
    - move the temporary file to the destination path

    Both `incomplete_path` and `destination_path` must be on the same volume to avoid a local copy.
    """
    if destination_path.exists() and not force_download:
        # Do nothing if already exists (except if force_download=True)
        return

    if incomplete_path.exists() and (force_download or (HF_HUB_ENABLE_HF_TRANSFER and not proxies)):
        # By default, we will try to resume the download if possible.
        # However, if the user has set `force_download=True` or if `hf_transfer` is enabled, then we should
        # not resume the download => delete the incomplete file.
        message = f"Removing incomplete file '{incomplete_path}'"
        if force_download:
            message += " (force_download=True)"
        elif HF_HUB_ENABLE_HF_TRANSFER and not proxies:
            message += " (hf_transfer=True)"
        logger.info(message)
        incomplete_path.unlink(missing_ok=True)

    with incomplete_path.open("ab") as f:
        resume_size = f.tell()
        message = f"Downloading '{filename}' to '{incomplete_path}'"
        if resume_size > 0 and expected_size is not None:
            message += f" (resume from {resume_size}/{expected_size})"
        logger.info(message)

        if expected_size is not None:  # might be None if HTTP header not set correctly
            # Check disk space in both tmp and destination path
            _check_disk_space(expected_size, incomplete_path.parent)
            _check_disk_space(expected_size, destination_path.parent)

        http_get(
            url_to_download,
            f,
            proxies=proxies,
            resume_size=resume_size,
            headers=headers,
            expected_size=expected_size,
        )

    logger.info(f"Download complete. Moving file to {destination_path}")
    _chmod_and_move(incomplete_path, destination_path)


def _int_or_none(value: Optional[str]) -> Optional[int]:
    try:
        return int(value)  # type: ignore
    except (TypeError, ValueError):
        return None


def _chmod_and_move(src: Path, dst: Path) -> None:
    """Set correct permission before moving a blob from tmp directory to cache dir.

    Do not take into account the `umask` from the process as there is no convenient way
    to get it that is thread-safe.

    See:
    - About umask: https://docs.python.org/3/library/os.html#os.umask
    - Thread-safety: https://stackoverflow.com/a/70343066
    - About solution: https://github.com/huggingface/huggingface_hub/pull/1220#issuecomment-1326211591
    - Fix issue: https://github.com/huggingface/huggingface_hub/issues/1141
    - Fix issue: https://github.com/huggingface/huggingface_hub/issues/1215
    """
    # Get umask by creating a temporary file in the cached repo folder.
    tmp_file = dst.parent.parent / f"tmp_{uuid.uuid4()}"
    try:
        tmp_file.touch()
        cache_dir_mode = Path(tmp_file).stat().st_mode
        os.chmod(str(src), stat.S_IMODE(cache_dir_mode))
    except OSError as e:
        logger.warning(
            f"Could not set the permissions on the file '{src}'. "
            f"Error: {e}.\nContinuing without setting permissions."
        )
    finally:
        try:
            tmp_file.unlink()
        except OSError:
            # fails if `tmp_file.touch()` failed => do nothing
            # See https://github.com/huggingface/huggingface_hub/issues/2359
            pass

    shutil.move(str(src), str(dst), copy_function=_copy_no_matter_what)


def _copy_no_matter_what(src: str, dst: str) -> None:
    """Copy file from src to dst.

    If `shutil.copy2` fails, fallback to `shutil.copyfile`.
    """
    try:
        # Copy file with metadata and permission
        # Can fail e.g. if dst is an S3 mount
        shutil.copy2(src, dst)
    except OSError:
        # Copy only file content
        shutil.copyfile(src, dst)


def _get_pointer_path(storage_folder: str, revision: str, relative_filename: str) -> str:
    # Using `os.path.abspath` instead of `Path.resolve()` to avoid resolving symlinks
    snapshot_path = os.path.join(storage_folder, "snapshots")
    pointer_path = os.path.join(snapshot_path, revision, relative_filename)
    if Path(os.path.abspath(snapshot_path)) not in Path(os.path.abspath(pointer_path)).parents:
        raise ValueError(
            "Invalid pointer path: cannot create pointer path in snapshot folder if"
            f" `storage_folder='{storage_folder}'`, `revision='{revision}'` and"
            f" `relative_filename='{relative_filename}'`."
        )
    return pointer_path
