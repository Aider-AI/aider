{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-23.11";
  };

  outputs = {
    self,
    nixpkgs,
    ...
  }: let
    inherit (nixpkgs) lib;

    system = lib.genAttrs lib.platforms.all (system: system);

    developerSystems = [system.x86_64-linux];

    allSystems = lib.platforms.all;

    legacyPackages = lib.genAttrs developerSystems (
      system:
        import nixpkgs {
          inherit system;
          overlays = [
            self.overlays.default
          ];
        }
    );
  in {
    devShells = lib.genAttrs developerSystems (system: {
      default = legacyPackages.${system}.callPackage ./nix/dev-shells/default {};
    });

    formatter = lib.genAttrs developerSystems (system: legacyPackages.${system}.alejandra);

    overlays = {
      default = import ./nix/overlays/default { flake = self; };
    };

    packages = lib.genAttrs allSystems (
      system:
        import ./nix/packages {
          flake = self;
          legacyPackages = legacyPackages.${system};
          inherit lib system;
        }
    );
  };
}
