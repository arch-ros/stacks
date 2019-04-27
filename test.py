from oyster.pacman.pkgbuild import PkgBuild

pkg = PkgBuild('/home/oyster/packages/archlinux/systemd/repos/core-x86_64/PKGBUILD')
print(list(map(lambda p: str(p), pkg.packages)))
pkg = PkgBuild('/home/oyster/packages/archlinux/man-db/repos/core-x86_64/PKGBUILD')
print(list(map(lambda p: str(p), pkg.packages)))
pkg = PkgBuild('/home/oyster/packages/archlinux/linux/repos/core-x86_64/PKGBUILD')
print(list(map(lambda p: str(p), pkg.packages)))
