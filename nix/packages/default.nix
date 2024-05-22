{
  flake,
  lib,
  legacyPackages,
  system,
}: {
  default = flake.packages.${system}.aider;
  inherit (legacyPackages)
    aider;
}
