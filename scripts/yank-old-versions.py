import requests
from packaging import version
from packaging.specifiers import SpecifierSet


def get_python_support_for_versions(package_name):
    # Fetch package information from PyPI
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch data for {package_name}")
        return {}

    data = response.json()
    version_support = {}

    for release, release_data in data["releases"].items():
        if not release_data:  # Skip empty releases
            continue

        # Check the 'requires_python' field
        requires_python = release_data[0].get("requires_python")

        if requires_python is None:
            version_support[release] = "Unspecified (assumed compatible with all versions)"
        else:
            try:
                spec = SpecifierSet(requires_python)
                supported_versions = []
                for py_version in ["3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12"]:
                    if version.parse(py_version) in spec:
                        supported_versions.append(py_version)
                version_support[release] = (
                    ", ".join(supported_versions)
                    if supported_versions
                    else "No supported versions found"
                )
            except ValueError:
                version_support[release] = f"Invalid specifier: {requires_python}"

    return version_support


def main():
    package_name = "aider-chat"  # Replace with your package name
    version_support = get_python_support_for_versions(package_name)

    print(f"Python version support for each release of {package_name}:")
    for release, support in sorted(
        version_support.items(), key=lambda x: version.parse(x[0]), reverse=True
    ):
        print(f"{release}: {support}")


if __name__ == "__main__":
    main()
