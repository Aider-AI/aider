{
  lib,
  buildPythonPackage,
  fetchFromGitHub,
  setuptools,
  pythonOlder,
  pytestCheckHook,
  requests,
  typing-extensions,
}:

buildPythonPackage rec {
  pname = "resend";
  version = "1.1.0";
  pyproject = true;

  disabled = pythonOlder "3.7";

  src = fetchFromGitHub {
    owner = "resend";
    repo = "resend-python";
    rev = "refs/tags/v${version}";
    hash = "sha256-xLrqkOHdynlwuY3+9aHWgCz8TX9v4RiVCvvPtu6k14c=";
  };

  # build-system = [ setuptools ];
  nativeBuildInputs = [ setuptools ];

  # dependencies = [
  propagatedBuildInputs = [
    requests
    typing-extensions
  ];

  nativeCheckInputs = [ pytestCheckHook ];

  pythonImportsCheck = [ "resend" ];

  meta = with lib; {
    description = "SDK for Resend";
    homepage = "https://github.com/resend/resend-python";
    changelog = "https://github.com/resend/resend-python/releases/tag/v${version}";
    license = licenses.mit;
    maintainers = with maintainers; [ fab ];
  };
}
