import os

from aider.utils import is_image_file, safe_abs_path


def test_safe_abs_path_symlink_loop(tmp_path):
    # Create circular symlink: a -> b -> a
    link_a = tmp_path / "link_a"
    link_b = tmp_path / "link_b"
    link_a.symlink_to(link_b)
    link_b.symlink_to(link_a)

    # safe_abs_path must not raise, and must return an absolute path
    result = safe_abs_path(str(link_a))
    assert os.path.isabs(result)


def test_is_image_file_is_case_insensitive():
    # Cameras and Windows produce upper/mixed-case extensions
    assert is_image_file("IMG_0001.JPG")
    assert is_image_file("Screenshot.Png")
    assert is_image_file("scan.PDF")
    assert is_image_file("photo.png")


def test_is_image_file_rejects_non_images():
    assert not is_image_file("main.py")
    assert not is_image_file("README.md")
    assert not is_image_file("png")  # the bare word is not an extension
