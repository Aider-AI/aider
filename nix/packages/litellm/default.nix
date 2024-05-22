{ lib
, aiohttp
, apscheduler
, azure-identity
, azure-keyvault-secrets
, backoff
, buildPythonPackage
, click
, fastapi
, fastapi-sso
, fetchFromGitHub
, google-cloud-kms
, gunicorn
, importlib-metadata
, jinja2
, openai
, orjson
, poetry-core
, prisma
, pyjwt
, python-dotenv
, python-multipart
, pythonOlder
, pyyaml
, requests
, resend
, rq
, streamlit
, tiktoken
, tokenizers
, uvicorn
}:

buildPythonPackage rec {
  pname = "litellm";
  version = "1.37.16";
  pyproject = true;

  disabled = pythonOlder "3.8";

  src = fetchFromGitHub {
    owner = "BerriAI";
    repo = "litellm";
    rev = "refs/tags/v${version}";
    hash = "sha256-WOkblyzncIn1F67qlh8rTosCal6j4zlXsHHrWbwhJOo=";
  };

  postPatch = ''
    rm -rf dist
  '';

  # build-system = [
  nativeBuildInputs = [
    poetry-core
  ];

  # dependencies = [
  propagatedBuildInputs = [
    aiohttp
    click
    importlib-metadata
    jinja2
    openai
    requests
    python-dotenv
    tiktoken
    tokenizers
  ];

  passthru.optional-dependencies = {
    proxy = [
      apscheduler
      backoff
      fastapi
      fastapi-sso
      gunicorn
      orjson
      pyjwt
      python-multipart
      pyyaml
      rq
      uvicorn
    ];
    extra_proxy = [
      azure-identity
      azure-keyvault-secrets
      google-cloud-kms
      prisma
      resend
      streamlit
    ];
  };

  # the import check phase fails trying to do a network request to openai
  # pythonImportsCheck = [ "litellm" ];

  # no tests
  doCheck = false;

  meta = with lib; {
    description = "Use any LLM as a drop in replacement for gpt-3.5-turbo. Use Azure, OpenAI, Cohere, Anthropic, Ollama, VLLM, Sagemaker, HuggingFace, Replicate (100+ LLMs)";
    mainProgram = "litellm";
    homepage = "https://github.com/BerriAI/litellm";
    changelog = "https://github.com/BerriAI/litellm/releases/tag/v${version}";
    license = licenses.mit;
    maintainers = with maintainers; [ happysalada ];
  };
}
