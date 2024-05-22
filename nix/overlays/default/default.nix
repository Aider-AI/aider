{ flake }: final: prev: let
  pythonOverrides = final: prev: {
    grep-ast = final.callPackage ../../packages/grep-ast {};
    tree-sitter-languages = final.callPackage ../../packages/tree-sitter-languages {};
    openai = final.callPackage ../../packages/openai {};
    litellm = final.callPackage ../../packages/litellm {};
    fastapi-sso = final.callPackage ../../packages/fastapi-sso {};
    prisma = final.callPackage ../../packages/prisma {};
    resend = final.callPackage ../../packages/resend {};
    gitpython = final.callPackage ../../packages/gitpython {};
    streamlit = final.callPackage ../../packages/streamlit {};

    # Fixes
    eventlet = prev.eventlet.overrideAttrs (oldAttrs: { doCheck = false; });
  };
in {
  python310 = prev.python310.override (oldAttrs: {
    self = final.python310;
    packageOverrides = final.lib.composeManyExtensions [
      (oldAttrs.packageOverrides or (final: prev: {}))
      pythonOverrides
    ];
  });

  python3 = final.python310;
  python = final.python3;
  aider = final.python.pkgs.callPackage ../../packages/aider {};

  # Fixes
  cryptsetup = prev.cryptsetup.overrideAttrs (oldAttrs: { doCheck = false; });
}

