import requests
from packaging import version
from packaging.specifiers import SpecifierSet


def get_versions_supporting_python38(package_name):
    # Fetch package information from PyPI
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch data for {package_name}")
        return []

    data = response.json()
    compatible_versions = []

    for release, release_data in data["releases"].items():
        if not release_data:  # Skip empty releases
            continue

        # Check the 'requires_python' field
        requires_python = release_data[0].get("requires_python")

        if requires_python is None:
            # If 'requires_python' is not specified, assume it's compatible
            compatible_versions.append(release)
        else:
            # Parse the requires_python specifier
            try:
                spec = SpecifierSet(requires_python)
                if version.parse("3.8") in spec:
                    compatible_versions.append(release)
            except ValueError:
                print(f"Invalid requires_python specifier for version {release}: {requires_python}")

    return compatible_versions


def main():
    package_name = "aider-chat"  # Replace with your package name
    compatible_versions = get_versions_supporting_python38(package_name)

    print(f"Versions of {package_name} compatible with Python 3.8 or lower:")
    for v in compatible_versions:
        print(v)


if __name__ == "__main__":
    main()
