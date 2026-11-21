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


def test_is_image_file_ignores_extension_case():
    # Cameras, scanners and phones often use upper case extensions
    assert is_image_file("photo.png")
    assert is_image_file("photo.PNG")
    assert is_image_file("DSC_0001.JPG")
    assert is_image_file("scan.Pdf")
    assert is_image_file("animation.GIF")
    assert is_image_file("photo.WEBP")

    assert not is_image_file("notes.txt")
    assert not is_image_file("report.md")
