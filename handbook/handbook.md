# The Chamesle handbook

Chamesle is a Linux system you build from source and keep small. The kernel is the only thing in it that comes
from outside the Unix family: the C library is musl, the shell is ksh, the packages come from NetBSD's pkgsrc
and the package manager is `mag`.

## What is in it

| part | what it is |
|---|---|
| kernel | Linux 6.18, built by you (chapter 3) |
| musl | the C library |
| rifle | the coreutils, one C file |
| mag | the package manager, reads pkgsrc packages as they are |
| dinit | init and service manager |
| oksh | the login shell (the OpenBSD ksh), `/bin/sh` is dash |
| vim | the editor, installed on the ISO |
| limine | the boot loader |

## 1. Getting a root file system

`tools/chamesle-bootstrap` is to Chamesle what debootstrap is to Debian. It makes the directories and the files in
`/etc`, then builds and installs the base packages into the directory you give it with `mag`:

    MAG_REPO=$HOME/src/mag/repo:/usr/pkgsrc chamesle-bootstrap /mnt/root

Building everything from source takes a while (LLVM is the long one). Packages are not built twice: the sources
are kept in `var/cache/mag` inside the target.

`-s "shells/oksh editors/vim"` installs your own list, `-n name` sets the host name, `-k kernel.tar.xz` unpacks a
kernel from chapter 3 into the target.

## 2. mag

    mag install editors/vim     fetch, check the checksum, build, install, dependencies first
    mag remove vim
    mag upgrade                 rebuild what has a newer version
    mag search word | info pkg | files pkg | owns /path | deps pkg | list

`MAG_REPO` is a list of repos split by colons. Two kinds of package live in them and can be mixed:

* our own recipes, `category/name`, a file with `url`, `sha256`, `deps` and plain sh `steps`
* NetBSD pkgsrc packages, a directory with a `Makefile`, a `distinfo` and `patches/`, read without `bmake`

A file called `PROVIDES` in a repo says which of our packages stands in for a pkgsrc one (so a pkgsrc package gets
our zlib and not a second one) and which dependencies a pkgsrc Makefile forgets (`needs`). Everything lands in
`$MAG_ROOT`, nothing is ever installed over a file another package owns, and `/etc` files you changed stay.

### /etc/mag.conf

pkgsrc's `mk.conf` syntax, plain `VAR=value` lines, read from `$MAG_ROOT/etc/mag.conf`:

    JOBS=8                          # $JOBS in the steps, make -j
    CFLAGS=-O2 -pipe                # also CXXFLAGS, CPPFLAGS, LDFLAGS, for every build
    PKG_DEFAULT_OPTIONS=-http2 idn  # options for every pkgsrc package that has them, a minus turns one off
    PKG_OPTIONS.vim=python          # the options of one package

`mag info www/curl` shows the options a package ends up with and its dependencies change with them. Packages of
our own repo have no options, they only see `JOBS` and the flags. Environment wins over the file
(`MAG_JOBS`, `CFLAGS`).

## 3. Building the kernel on the MSI

The MSI is the machine the kernel has to boot on, so it is the one that knows what hardware there is. Any
Linux that already runs on it will do for the building.

Step one. Tell us what is in the machine:

    sh kernel/collect-hw.sh        # writes hw.txt: cpu, pci, usb, loaded modules, UEFI or BIOS. no serial numbers, no addresses

Step two. Build:

    sh kernel/build.sh             # config of the running kernel as the start, safe and big
    sh kernel/build.sh small       # only what the machine uses right now (plug in everything you own first)

It downloads linux-6.18.63 from kernel.org, checks the checksum, builds `bzImage` and the modules and packs them into
`~/chamesle-kernel/chamesle-kernel-6.18.63.tar.xz`. It needs gcc or clang, make, flex, bison, bc, perl, curl, xz.
On a recent MSI with many cores it takes a quarter of an hour, with `small` less.

Step three. Get the files to the computer that builds Chamesle. Any of these:

* **a USB stick:** copy `chamesle-kernel-6.18.63.tar.xz`, `chamesle-kernel-6.18.63.sha256` and `hw.txt` onto it
* **over the network with nc:** on the receiving computer `nc -l 9000 > kernel.tar.xz`, on the MSI
  `nc ADDRESS 9000 < chamesle-kernel-6.18.63.tar.xz` (address is what `ip -4 addr` shows on the receiving one)
* **the MSI serves, the other fetches:** on the MSI `cd ~/chamesle-kernel && python3 -m http.server 8000`, on the
  other `curl -O http://MSI-ADDRESS:8000/chamesle-kernel-6.18.63.tar.xz`
* **scp** works when sshd runs on the receiving side

Check it on arrival: `sha256sum -c chamesle-kernel-6.18.63.sha256`.

## 4. The ISO

The ISO is an installer: it boots a small live system, and `chamesle-install` puts that on a disk. It boots on BIOS
and UEFI machines with limine.

    iso/mkiso -k chamesle-kernel-6.18.63.tar.xz -r $HOME/src/mag/repo:/usr/pkgsrc

What it does, in order: `chamesle-bootstrap` builds a root from `iso/profile/packages`, the files of
`iso/profile/overlay` are copied over it, the kernel tarball from chapter 3 is unpacked into it, `mkinitramfs`
makes the initrd (a few static tools, the modules in `iso/profile/modules` with what they depend on, `iso/init`),
the root becomes a zstd squashfs, and `xorriso` writes the ISO with limine's BIOS and UEFI boot images.
`-R dir` uses a root you already have instead of building one (it is copied, not changed).

At boot `init` looks for the medium that has `LiveOS/rootfs.sfs`, mounts it read-only, puts a tmpfs overlay over it,
and switches into the result. The medium and the squashfs stay mounted under `/run/live/`, which is where the
installer copies from. An installed system boots with `root=UUID=...` on the same initrd.

`chamesle-install` asks for the disk, a host name and a root password, then makes a GPT with a 1M BIOS boot
partition, a 512M EFI partition (also `/boot`) and the rest as ext4, copies the system, writes fstab and
limine.conf and installs limine for both BIOS and UEFI.

Try an ISO without a machine:

    qemu-system-x86_64 -cpu max -m 1G -cdrom chamesle.iso -boot d
    qemu-system-x86_64 -cpu max -m 1G -bios /usr/share/qemu/edk2-x86_64-code.fd -cdrom chamesle.iso   # uefi

mkiso needs `mksquashfs`, `xorriso` (or any mkisofs: set `MKISOFS`), `zstd`, `bsdcpio` and `limine` on the machine
that builds. `LIMINE` says where limine's files are (default /usr/share/limine).

## 5. Files

    /etc/profile       PATH, EDITOR=vim
    /etc/ksh.kshrc     prompt and aliases of every ksh
    /etc/dinit.d/      services
    /etc/fstab, hostname, passwd, group, shells
    /var/lib/mag       what is installed, per package
    /var/cache/mag     downloaded sources
