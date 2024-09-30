{
  description = "aider - AI pair programming in your terminal";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication defaultPoetryOverrides;

        customOverrides = defaultPoetryOverrides.extend (self: super: {
          # Add overrides if needed for specific packages
        });

        aider = mkPoetryApplication {
          projectDir = ./.;
          overrides = [ customOverrides ];
          preferWheels = true;
        };

      in {
        packages.default = aider;

        devShells.default = pkgs.mkShell {
          inputsFrom = [ aider ];
          packages = [ pkgs.poetry ];
        };
      }
    );
}
