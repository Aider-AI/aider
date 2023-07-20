import requests
import pkg_resources

def check_version():
    response = requests.get('https://pypi.org/pypi/aider/json')
    data = response.json()
    latest_version = data['info']['version']
    current_version = pkg_resources.get_distribution('aider').version

    if pkg_resources.parse_version(latest_version) > pkg_resources.parse_version(current_version):
        print(f"A newer version of 'aider' is available: {latest_version}")
    else:
        print("You are using the latest version of 'aider'.")

if __name__ == "__main__":
    check_version()
