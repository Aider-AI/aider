{ lib
, buildPythonPackage
, ddt
, fetchFromGitHub
, gitdb
, pkgs
, pythonOlder
, substituteAll
, typing-extensions
}:

buildPythonPackage rec {
  pname = "gitpython";
  version = "3.1.43";
  format = "setuptools";

  disabled = pythonOlder "3.7";

  src = fetchFromGitHub {
    owner = "gitpython-developers";
    repo = "GitPython";
    rev = "refs/tags/${version}";
    hash = "sha256-HO6t5cOHyDJVz+Bma4Lkn503ZfDmiQxUfSLaSZtUrTk=";
  };

  propagatedBuildInputs = [
    ddt
    gitdb
    pkgs.gitMinimal
  ] ++ lib.optionals (pythonOlder "3.10") [
    typing-extensions
  ];

  postPatch = ''
    substituteInPlace git/cmd.py \
      --replace 'git_exec_name = "git"' 'git_exec_name = "${pkgs.gitMinimal}/bin/git"'
  '';

  # Tests require a git repo
  doCheck = false;

  pythonImportsCheck = [
    "git"
  ];

  meta = with lib; {
    description = "Python Git Library";
    homepage = "https://github.com/gitpython-developers/GitPython";
    changelog = "https://github.com/gitpython-developers/GitPython/blob/${version}/doc/source/changes.rst";
    license = licenses.bsd3;
    maintainers = with maintainers; [ fab ];
  };
}
