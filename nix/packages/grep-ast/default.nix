{ lib
, buildPythonPackage
, fetchFromGitHub
, tree-sitter-languages
, pathspec
, setuptools
}:

buildPythonPackage rec {
  pname = "grep-ast";
  version = "0.3.2";
  format = "pyproject";

  src = fetchFromGitHub {
    owner = "paul-gauthier";
    repo = pname;
    rev = "3cf620091364e95e501fa2fd1125cc9fae7971e5";
    hash = "sha256-xeHT8Zp1NyLeK2864DsFpNoxrct/EcUEbG+d33Gc/LQ=";
  };

  buildInputs = [
    setuptools
  ];

  propagatedBuildInputs = [
    tree-sitter-languages
    pathspec
  ];

  pythonImportsCheck = [ "grep_ast" ];

  meta = with lib; {
    description = ''
      Grep source code and see useful code context about matching lines
    '';
    homepage = "https://github.com/paul-gauthier/grep-ast";
    license = licenses.asl20;
    maintainers = with maintainers; [ breakds ];
  };
}
