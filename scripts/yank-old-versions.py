import requests
from packaging import version
from packaging.specifiers import SpecifierSet


def get_versions_supporting_python38_or_lower(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch data for {package_name}")
        return {}

    data = response.json()
    compatible_versions = {}

    for release, release_data in data["releases"].items():
        if not release_data:  # Skip empty releases
            continue

        requires_python = release_data[0].get("requires_python")

        if requires_python is None:
            compatible_versions[release] = (
                "Unspecified (assumed compatible with Python 3.8 and lower)"
            )
        else:
            try:
                spec = SpecifierSet(requires_python)
                if version.parse("3.8") in spec:
                    compatible_versions[release] = (
                        f"Compatible with Python 3.8 (spec: {requires_python})"
                    )
            except ValueError:
                print(f"Invalid requires_python specifier for version {release}: {requires_python}")

    return compatible_versions


def main():
    package_name = "aider-chat"  # Replace with your package name
    compatible_versions = get_versions_supporting_python38_or_lower(package_name)

    print(f"Versions of {package_name} compatible with Python 3.8 or lower:")
    for release, support in sorted(
        compatible_versions.items(), key=lambda x: version.parse(x[0]), reverse=True
    ):
        print(f"{release}: {support}")


if __name__ == "__main__":
    main()
