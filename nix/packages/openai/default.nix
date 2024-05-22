{
  lib,
  anyio,
  buildPythonPackage,
  cached-property,
  dirty-equals,
  distro,
  fetchFromGitHub,
  hatch-fancy-pypi-readme,
  hatchling,
  httpx,
  numpy,
  pandas,
  pandas-stubs,
  pydantic,
  pytest-asyncio,
  pytest-mock,
  pytestCheckHook,
  pythonOlder,
  respx,
  sniffio,
  tqdm,
  typing-extensions,
}:

buildPythonPackage rec {
  pname = "openai";
  version = "1.30.1";
  pyproject = true;

  disabled = pythonOlder "3.7.1";

  src = fetchFromGitHub {
    owner = "openai";
    repo = "openai-python";
    rev = "refs/tags/v${version}";
    hash = "sha256-HREwQvsnG9zzDW8TkTQrvpyDoDxu9j6dOvyUKlBl7cQ=";
  };

  # build-system = [
  nativeBuildInputs = [
    hatchling
    hatch-fancy-pypi-readme
  ];

  # dependencies = [
  propagatedBuildInputs = [
    httpx
    pydantic
    typing-extensions
    anyio
    distro
    sniffio
    tqdm
  ] ++ lib.optionals (pythonOlder "3.8") [ cached-property ];

  passthru.optional-dependencies = {
    datalib = [
      numpy
      pandas
      pandas-stubs
    ];
  };

  pythonImportsCheck = [ "openai" ];

  nativeCheckInputs = [
    pytestCheckHook
    pytest-asyncio
    pytest-mock
    respx
    dirty-equals
  ];

  pytestFlagsArray = [
    "-W"
    "ignore::DeprecationWarning"
  ];

  disabledTests = [
    # Tests make network requests
    "test_streaming_response"
    "test_copy_build_request"

    # Test fails with pytest>=8
    "test_basic_attribute_access_works"
  ];

  disabledTestPaths = [
    # Test makes network requests
    "tests/api_resources"
  ];

  meta = with lib; {
    description = "Python client library for the OpenAI API";
    homepage = "https://github.com/openai/openai-python";
    changelog = "https://github.com/openai/openai-python/releases/tag/v${version}";
    license = licenses.mit;
    maintainers = with maintainers; [ malo ];
    mainProgram = "openai";
  };
}
