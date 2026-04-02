{
  description = "A minimal Python Qt (PySide6) development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, utils }:
    utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            (pkgs.python3.withPackages (ps: with ps; [
              pyside6
              requests
              lxml
            ]))
          ];

          # Necessary for the Qt GUI to find graphics drivers/libraries on NixOS/Linux
          shellHook = ''
            export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [ pkgs.libGL pkgs.stdenv.cc.cc.lib ]}:$LD_LIBRARY_PATH
            echo "Python Qt environment loaded."
          '';
        };
      });
}
