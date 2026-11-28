{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = with pkgs; [ libGL libx11 expat zlib ];

  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.libGL pkgs.libx11 pkgs.stdenv.cc.cc.lib pkgs.expat pkgs.zlib
  ];

  shellHook = ''
    viewer() { uv run python -m ocp_viewer; }
    watcher()  { uv run python watch.py kijuma/main.py; }
  '';
}
