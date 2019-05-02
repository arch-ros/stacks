from oyster.pacman.pkgbuild import PkgBuild

pkg = PkgBuild('/home/oyster/packages/archlinux/systemd/repos/core-x86_64/PKGBUILD')
print(list(map(lambda p: str(p), pkg.packages)))
# Get the package dependencies
pkg = PkgBuild('/home/oyster/packages/archlinux/man-db/repos/core-x86_64/PKGBUILD')
mandb_pkg = pkg.packages[0]
pkg = PkgBuild('/home/oyster/packages/archlinux/linux/repos/core-x86_64/PKGBUILD')
print(list(map(lambda p: str(p), pkg.packages)))
