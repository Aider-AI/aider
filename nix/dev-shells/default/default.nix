{
  aider,
  fetchFromGitHub,
  imgcat,
  lib,
  mkShell,
  pre-commit,
  python,
  typer,
  writeText,
  # black,
  # mypy,
}: let
  # Environment with plannet dependencies
  pythonEnv = python.withPackages (
    pythonPkgs:
      with pythonPkgs;
        [
          flake8
          pytest
          # lox (not available in nixpkgs)
          matplotlib
          pandas
          pip-tools
        ]
        ++ aider.propagatedBuildInputs
  );
in
  mkShell {
    buildInputs = [
      # See dev-requirements.in
      pythonEnv
      typer
      imgcat
      pre-commit
      # black
      # mypy
    ];

    shellHook = let
      nocolor = "\\e[0m";
      white = "\\e[1;37m";
    in ''
      clear -x
      printf "${white}"
      echo "-----------------------"
      echo "Development environment"
      echo "-----------------------"
      printf "${nocolor}"
      echo

      export PYTHONPATH="$(pwd):$PYTHONPATH"
    '';
  }
