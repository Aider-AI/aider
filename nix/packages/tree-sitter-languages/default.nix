{ lib
, stdenv
, buildPythonPackage
, autoPatchelfHook
, python
, fetchurl
, tree-sitter
}:

let wheels = {
      "x86_64-linux-python-3.10" = {
        url = https://files.pythonhosted.org/packages/f4/86/b50a1a5cc7058bf572acceb8b005c77e2f43b06a13fdb7a52c38b0f8e6fa/tree_sitter_languages-1.10.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl;
        sha256 = "0lv1nml1lfc9017s001pfqmyy8pl6l1r8grzyfwcwq746gh8aqqw";
      };
      "x86_64-linux-python-3.11" = {
        url = https://files.pythonhosted.org/packages/96/81/ab4eda8dbd3f736fcc9a508bc69232d3b9076cd46b932d9bf9d49b9a1ec9/tree_sitter_languages-1.10.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl;
        sha256 = "0jdqscis0lzf4ypjdlabilfpd05cq6agk84q97i0n5x72k1lmqws";
      };
      "x86_64-linux-python-3.12" = {
        url = https://files.pythonhosted.org/packages/f2/e6/eddc76ad899d77adcb5fca6cdf651eb1d33b4a799456bf303540f6cf8204/tree_sitter_languages-1.10.2-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl;
        sha256 = "0q6jykj5wgmcb78m2a3mxlfwyj7ivi4pvdn2z4r57mmxs78iqbvd";
      };
    };

in buildPythonPackage rec {
  pname = "tree-sitter-languages";
  version = "1.10.2";
  format = "wheel";

  src = fetchurl wheels."${stdenv.system}-python-${python.pythonVersion}";

  buildInputs = [
    stdenv.cc.cc.lib
  ];

  nativeBuildInputs = [
    autoPatchelfHook
  ];

  propagatedBuildInputs = [
    tree-sitter
  ];

  meta = with lib; {
    description = ''
      Binary Python wheels for all tree sitter languages
    '';
    homepage = "https://github.com/grantjenks/py-tree-sitter-languages";
    license = licenses.asl20;
    maintainers = with maintainers; [ breakds ];
  };
}
