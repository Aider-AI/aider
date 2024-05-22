{ lib
, buildPythonPackage
, click
, fetchFromGitHub
, httpx
, jinja2
, nodeenv
, pydantic
, pytestCheckHook
, python-dotenv
, pythonOlder
, setuptools
, strenum
, tomlkit
, typing-extensions
}:

buildPythonPackage rec {
  pname = "prisma";
  version = "0.13.1";
  pyproject = true;

  disabled = pythonOlder "3.8";

  src = fetchFromGitHub {
    owner = "RobertCraigie";
    repo = "prisma-client-py";
    rev = "refs/tags/v${version}";
    hash = "sha256-7pibexiFsyrwC6rVv0CGHRbQU4G3rOXVhQW/7c/vKJA=";
  };

  # build-system = [
  nativeBuildInputs = [
    setuptools
  ];

  # dependencies = [
  propagatedBuildInputs = [
    click
    httpx
    jinja2
    nodeenv
    pydantic
    python-dotenv
    tomlkit
    typing-extensions
  ] ++ lib.optionals (pythonOlder "3.11") [
    strenum
  ];

  # Building the client requires network access
  doCheck = false;

  pythonImportsCheck = [
    "prisma"
  ];

  meta = with lib; {
    description = "Auto-generated and fully type-safe database client for prisma";
    homepage = "https://github.com/RobertCraigie/prisma-client-py";
    changelog = "https://github.com/RobertCraigie/prisma-client-py/releases/tag/v${version}";
    license = licenses.asl20;
    maintainers = with maintainers; [ fab ];
  };
}
