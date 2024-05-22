{ lib
, buildPythonApplication
, fetchFromGitHub

# buildInputs
, setuptools

# propagatedBuildInputs
, configargparse
, gitpython
, openai
, tiktoken
, jsonschema
, rich
, prompt-toolkit
, numpy
, scipy
, backoff
, pathspec
, networkx
, diskcache
, grep-ast
, packaging
, sounddevice
, soundfile
, beautifulsoup4
, pyyaml
, pillow
, diff-match-patch
, playwright
, pypandoc
, httpx
, litellm
, streamlit
}:

buildPythonApplication rec {
  pname = "aider";
  version = "0.35.0";
  format = "pyproject";

  src = lib.fileset.toSource {
    root = ../../..;
    fileset = lib.fileset.difference
      (lib.fileset.gitTracked ../../..)
      (lib.fileset.unions [
        ../../../flake.nix
        ../../../flake.lock
        ../../../nix
      ]);
  };

  # src = fetchFromGitHub {
  #   owner = "paul-gauthier";
  #   repo = pname;
  #   rev = "v${version}";
  #   hash = "sha256-oDBPji2PBhsjzX+7OjtUY27DyBFVvwMEooNNIS6Cy3g=";
  # };

  buildInputs = [
    setuptools
  ];

  propagatedBuildInputs = [
    configargparse
    gitpython
    openai
    tiktoken
    jsonschema
    rich
    prompt-toolkit
    numpy
    scipy
    backoff
    pathspec
    networkx
    diskcache
    grep-ast
    packaging
    sounddevice
    soundfile
    beautifulsoup4
    pyyaml
    pillow
    diff-match-patch
    playwright
    pypandoc
    httpx
    litellm
    streamlit
  ];

  meta = with lib; {
    description = ''
      aider is AI pair programming in your terminal
    '';
    homepage = "https://aider.chat/";
    license = licenses.asl20;
    maintainers = with maintainers; [];
  };
}
