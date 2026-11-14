# The Chamesle Handbook

1. About Chamesle
2. Preparing
3. Installing by hand
4. Using mag
5. rifle
6. The base system
7. The kernel and firmware
8. The live ISO
9. Maintaining
10. File reference


## 1. About Chamesle

### 1.1 What it is

Chamesle is a Linux distribution you build from source and put on a disk yourself. There is no installer: you
install the root file system, write the configuration and the boot entry by hand. `chamesle-disk` partitions and formats the
disk for you if you want, and this handbook goes through every other step.

The parts:

| part   | what it is |
|--------|------------|
| kernel | a prebuilt Linux 6.18 LTS kernel with its modules |
| musl   | the C library |
| rifle  | the coreutils, all in one C file; `cat`, `ls`, `cp` and the rest are links to one program |
| mag    | the package manager; it reads NetBSD pkgsrc packages as they are, and recipes of its own |
| mksh   | the shell, login shell and `/bin/sh` |
| init   | `/sbin/init`, a shell script that runs under mksh, in the style of FreeBSD's: `/etc/rc`, `/etc/init.conf`, services |
| limine | the boot loader, BIOS and UEFI |

There is nothing from GNU in the system. Two exceptions are on the machine that builds: the kernel's own build tools,
and `gmake`, which musl's Makefile needs.

The package repository is NetBSD's pkgsrc, read directly by `mag` without `bmake`. Chamesle adds hand-written recipes
only for what pkgsrc does not have: musl, the kernel, its headers and firmware, limine, eudev, kmod, util-linux, iw,
libnl, iproute2, usbutils, netbsd-curses, libtool and ZFS. Everything is built on the machine that installs it, so the first
install takes a while (LLVM is the longest).

### 1.2 The layout of the system

    /bin /sbin /lib     /lib holds the musl loader and the firmware
    /usr/bin /usr/sbin  programs, /usr/lib libraries, /usr/share data, /usr/include headers
    /usr/local/bin      yours, first in PATH
    /boot               kernel, config, System.map, limine.conf (on the EFI partition)
    /etc                configuration
    /lib/modules        kernel modules, one directory per kernel version
    /lib/firmware       firmware for the hardware, zstd compressed
    /var/lib/mag        which package owns which file
    /var/cache/mag      downloaded sources
    /run /tmp           tmpfs, made new at every boot

The PATH of a login shell is `/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`. Packages install into `/usr`.

### 1.3 Where the sources are

| directory | what is in it |
|-----------|---------------|
| `system/` | `tools/` (`chamesle-bootstrap`, `chamesle-chroot`, `chamesle-disk`), `files/` (init, rc and the services), `iso/`, this handbook |
| `mag/`    | `mag.c`, `build.sh`, `tests/run.sh`, `repo/` with the hand recipes and `PROVIDES` |
| `rifle/`  | `rifle.c`, `build.sh`, `tests/run.sh` |
| pkgsrc    | NetBSD's package tree, which you fetch yourself (chapter 2) |

The commands in this book assume the three source trees are in `$HOME/src/system`, `$HOME/src/mag` and
`$HOME/src/rifle`. Change the paths if yours are elsewhere.


## 2. Preparing

### 2.1 What the build host needs

Chamesle is built from a running Linux machine: any distribution, or the live ISO of chapter 8. The host needs:

* `clang` and `lld`: `mag` and `rifle` are built with them, and so is everything in the new system
* `gmake`, for musl
* `ftp` (tnftp), which mag uses for downloads (`MAG_FETCH`)
* `tar` and a POSIX `sh`
* `sfdisk`, `mkfs.ext4` and `mkfs.fat` to prepare the disk
* `blkid` to read UUIDs

Plan for about 20 GB of free disk space for the sources and build directories of a first install, and a network
connection.

### 2.2 Building mag and rifle

Both are a single C file with no libc under it:

    cd $HOME/src/mag && ./build.sh
    cd $HOME/src/rifle && ./build.sh

`mag/build.sh` leaves `./mag`. `rifle/build.sh` leaves `./rifle` and a `bin/` directory with a link for every tool.
Put `mag` in your PATH:

    install -m755 $HOME/src/mag/mag /usr/local/bin/mag

### 2.3 Getting the pkgsrc tree

Let mag fetch a pkgsrc tree from NetBSD and unpack it into `/usr/pkgsrc`:

    mag sync

`sync` downloads `https://ftp.netbsd.org/pub/pkgsrc/current/pkgsrc.tar.xz` and replaces the tree with it, so it is also how
the tree is brought up to date. `MAG_SYNC_URL` names another file, and under `MAG_ROOT` the tree goes into `$MAG_ROOT/usr/pkgsrc`.
By hand it is the same thing:

    cd /usr
    ftp -o pkgsrc.tar.xz https://ftp.netbsd.org/pub/pkgsrc/current/pkgsrc.tar.xz
    tar -xf pkgsrc.tar.xz

pkgsrc has a directory per category (`shells`, `editors`, `www`, ...) and a directory per package inside it
(`shells/mksh`). `mag` reads the package's `Makefile`, `distinfo` and `patches/` itself.

### 2.4 MAG_REPO

`MAG_REPO` is a list of repositories separated by colons. Chamesle's own recipes come first, so they win over pkgsrc
when both have a package of the same name:

    export MAG_REPO=$HOME/src/mag/repo:/usr/pkgsrc

If `MAG_REPO` is not set, mag looks in `/usr/share/mag/repo` (Chamesle's own recipes, which the live ISO and every
bootstrapped root carry) and then in `/usr/pkgsrc`, where `mag sync` puts the tree. `MAG_ROOT` says where to install; it is the new root
during an installation (chapter 3) and unset on a running system.

A file called `PROVIDES` in a repo tells mag how our recipes meet pkgsrc's. Its lines are:

    pkgsrc/package  our/package      our package stands in for the pkgsrc one
    pkgsrc/package  -                nothing is needed, the dependency is dropped
    needs pkgsrc/package  dep        a dependency the pkgsrc Makefile forgets

For example `converters/libiconv -` (musl has iconv) and `needs editors/vim dev-libs/netbsd-curses`.

### 2.5 mag.conf

`$MAG_ROOT/etc/mag.conf` holds the build settings. It uses the syntax of pkgsrc's `mk.conf`: plain `VAR=value` lines.
`chamesle-bootstrap` writes a first one for the new system. For the host you build from, make one yourself:

    JOBS=8
    CFLAGS=-O2 -std=gnu17

* `JOBS` is `$JOBS` in the build steps, the number to give `make -j`. Without it mag uses 4
* `CFLAGS`, `CXXFLAGS`, `CPPFLAGS` and `LDFLAGS` are set for every build
* `PKG_DEFAULT_OPTIONS` and `PKG_OPTIONS.name` set pkgsrc options (section 4.6)
* `CONFIGURE_ARGS.name` adds arguments to the `configure` of one pkgsrc package, such as `CONFIGURE_ARGS.libtirpc=--disable-gssapi`

The environment wins over the file: `MAG_JOBS`, `CFLAGS` and the others, when set, are used as they are.

`-std=gnu17` matters. clang defaults to C23 now, and a lot of older source does not compile under it (section 9.3).


## 3. Installing by hand

Follow the BIOS or the UEFI variant where they differ. The disk here is `/dev/sda`; change it to yours. Everything below
is run as root on the machine you install from, usually the live ISO, and it erases the disk.

There are two ways through 3.1 and 3.2: `chamesle-disk` does the partitioning and the file systems and leaves the
root on ZFS, or you do both yourself. From 3.3 on the steps are the same, and they are yours: `chamesle-disk` is only a helper.

### 3.1 chamesle-disk

    chamesle-disk /dev/sda

It lists the disk and asks you to type its name before it touches anything. Then it starts `cfdisk` so you lay out the
partitions. Three of them work for BIOS and UEFI both:

| partition | size | type | use |
|-----------|------|------|-----|
| 1 | 1M | BIOS boot | limine's BIOS code, not used on UEFI |
| 2 | 512M | EFI System | `/boot`, FAT32 |
| 3 | the rest | Linux filesystem | `/`, ZFS |

Write the table and quit cfdisk. chamesle-disk lists the partitions and asks which one is the boot partition and which is
the root. Then it does, in this order:

    mkfs.fat -F32 BOOT
    zpool create -f -o ashift=12 -O compression=zstd -O acltype=posixacl -O xattr=sa -O mountpoint=none -R /mnt rpool ROOT
    zfs create -o mountpoint=/ -o canmount=noauto rpool/root
    zfs create -o mountpoint=/home rpool/home
    zfs create -o mountpoint=/var rpool/var
    zpool set bootfs=rpool/root rpool

and mounts `rpool/root`, `rpool/home` and `rpool/var` under `/mnt` and the boot partition on `/mnt/boot`. It also writes
`/mnt/etc/fstab` with the boot partition by UUID and the `proc`, `sysfs` and `tmpfs` lines (an existing one is left alone). It writes nothing else: no
`limine.conf`, no host name, no password. Those are 3.7 and 3.8.

ZFS mounts its own datasets, so the fstab does not list them. limine cannot read ZFS: the kernel, the initrd and
`limine.conf` live on the FAT partition, which is `/boot`, and the initramfs imports the pool (3.8).

### 3.2 Partitioning and file systems by hand

For a root on ext4. The layout is the one in 3.1, `sda1` to `sda3`:

    sfdisk /dev/sda <<P
    label: gpt
    size=1M, type=21686148-6449-6E6F-744E-656564454649
    size=512M, type=U
    type=L
    P

On an NVMe disk the partitions are `/dev/nvme0n1p1` and so on. Replace `sda1`, `sda2` and `sda3` throughout.

    mkfs.fat -F32 /dev/sda2
    mkfs.ext4 /dev/sda3
    mount /dev/sda3 /mnt
    mkdir /mnt/boot
    mount /dev/sda2 /mnt/boot

The FAT partition is `/boot`. The kernel and `limine.conf` end up there, where limine looks for them on both BIOS and
UEFI. The root can be ZFS by hand as well: the `zpool` and `zfs` lines of 3.1 are all there is to it.

### 3.3 Copying the live system

The live ISO has no compiler, so on a machine booted from it the system is not built, it is copied. The read-only root of
the ISO is mounted on `/run/live/rootfs` and the ISO itself on `/run/live/medium`:

    tar -C /run/live/rootfs --exclude ./etc/fstab -cf - . | tar -C /mnt -xpf -
    [ -e /mnt/etc/fstab ] || cp /run/live/rootfs/etc/fstab /mnt/etc/fstab
    cp /run/live/medium/boot/initrd /mnt/boot/initrd

That is the whole base system, kernel, modules and ZFS included, as it was when the ISO was made. The copy keeps the
fstab chamesle-disk wrote. The firmware for wifi and some network cards is not on the ISO. Add it with mag once the new system runs (section 4), or build everything instead (3.4), which needs a
machine with a compiler.

Work inside the new root with `chamesle-chroot`:

    chamesle-chroot /mnt
    chamesle-chroot /mnt passwd root

It mounts `proc`, `sys`, `dev`, `dev/pts` and a tmpfs on `run` under the directory, copies `/etc/resolv.conf` into it, runs
`chroot` with an empty environment (`HOME=/root`, `TERM`, `PATH`) and takes the mounts away again when the command ends. Without a command it
starts `/usr/bin/mksh -l`.

Then go on with 3.6 (fstab) and the rest. rifle (3.5) is on the ISO already, skip it. The kernel is in `/mnt/boot` already.

### 3.4 Building the system from source, instead

Point mag at the repositories (section 2.4) and run chamesle-bootstrap:

    export MAG_REPO=$HOME/src/mag/repo:/usr/pkgsrc
    $HOME/src/system/tools/chamesle-bootstrap -n yourhostname /mnt

Its usage:

    chamesle-bootstrap [-r REPOS] [-s PACKAGES] [-n HOSTNAME] TARGET

* `-r` sets the repositories, instead of `MAG_REPO`
* `-s` is the list of packages to install instead of the base set
* `-n` is the host name, `chamesle` if not given

It makes the directories (`bin boot dev etc/skel home lib lib/firmware mnt proc root run sbin srv sys tmp usr/bin
usr/lib usr/sbin usr/share usr/local/bin var/cache var/lib var/log var/tmp`, with `tmp` and `var/tmp` mode 1777 and
`root` mode 700), installs everything in `files/` (init, rc, the services, `init.conf`), writes the first `/etc` files (`passwd`,
`group`, `shells`, `fstab`, `profile`, `os-release`, `mag.conf`), and builds the base set into the target with `mag`:

    sys-libs/musl devel/gmake archivers/libarchive app-arch/bsdtar archivers/pigz shells/mksh sys-apps/util-linux
    sys-apps/kmod sys-apps/eudev net/dhcpcd net/tnftp sysutils/e2fsprogs sysutils/dosfstools sys-boot/limine
    sys-kernel/linux sys-kernel/linux-firmware sys-firmware/sof-firmware sys-firmware/wireless-regdb editors/vim
    sys-fs/zfs sys-kernel/zfs-module lang/clang devel/lld lang/compiler-rt lang/libunwind

`lang/clang` (with `lang/llvm` under it), `devel/lld`, `lang/compiler-rt` and `lang/libunwind` are the compiler of the new
system: it builds what `mag install` asks for after `mag sync`, so no other machine is needed. They are the longest part of the bootstrap.
It also copies the recipes of the first repo that has a `PROVIDES` file into `/usr/share/mag/repo`, installs `chamesle-chroot` and
`chamesle-disk`, and runs `depmod`.

The sources go in `/mnt/var/cache/mag` and are not fetched twice. An existing file in `/etc` is never overwritten, so
the script can be run again after a failure. A build that fails stops and names the directory it left behind.

Once musl is in the new root, every later package is built with clang aimed at it, with the loader and library
paths pointing into `/mnt`. That lets the programs run on the host while they are built. They need their real paths
before you boot the new system:

    MAG_ROOT=/mnt mag relocate

Run `mag relocate` again after every `MAG_ROOT=/mnt mag install` that adds programs (section 9.4).

### 3.5 rifle

The base set has no coreutils: they come from rifle. Install it into the new root:

    install -m755 $HOME/src/rifle/rifle /mnt/usr/bin/rifle
    $HOME/src/rifle/rifle --install /mnt/usr/bin

`rifle --install DIR` makes a link for each of its tools in `DIR`. rifle is built static, so it runs from the host as
it is.

Add the packages you want now, or after the first boot:

    MAG_ROOT=/mnt mag install editors/vim
    MAG_ROOT=/mnt mag relocate

### 3.6 fstab

If you used chamesle-disk the file is written. Look at it: the boot partition by UUID on `/boot`, then `proc`, `sysfs`
and `tmpfs`, and nothing for the ZFS datasets, because ZFS mounts them itself.

By hand, `blkid` prints the UUIDs:

    blkid /dev/sda2 /dev/sda3

Open `/mnt/etc/fstab` and add the root and boot lines under the `proc`, `sysfs` and `tmpfs` lines already there:

    UUID=ROOT-UUID  /      ext4  defaults  0 1
    UUID=BOOT-UUID  /boot  vfat  defaults  0 2

A root on ZFS gets only the boot line. Check that the UUID is the one `blkid` shows for the boot partition.

### 3.7 Host name, users, password

The host name is already in `/mnt/etc/init.conf` from `-n`. The root account is in `/mnt/etc/passwd` with an `x` in the
password field, and there is no shadow file, so the hash goes into that field. Make one on any machine that has
openssl, SHA-512:

    openssl passwd -6

Put the output in the second field of the root line:

    root:$6$salt$hash:0:0:root:/root:/usr/bin/mksh

musl's `crypt` reads `$6$` hashes. An empty field means no password at all.

The groups are `root`, `wheel` (10) and `users` (100). More accounts are lines in `passwd` and `group` and a home
directory you make (section 6.5).

### 3.8 The kernel and the boot entry

The kernel package put these in `/mnt/boot` (the version number is whatever the recipe carries):

    ls /mnt/boot
    config-6.18.63-0-lts   System.map-6.18.63-0-lts   vmlinuz-6.18.63-0-lts

Write `/mnt/boot/limine.conf` with the file name you see and the UUID of the root partition:

    timeout: 3

    /Chamesle
        protocol: linux
        path: boot():/vmlinuz-6.18.63-0-lts
        module_path: boot():/initrd
        cmdline: root=UUID=ROOT-UUID rw console=tty0

For a root on ZFS the command line names the dataset, there is no UUID:

        cmdline: root=ZFS=rpool/root rw console=tty0

`boot()` is the partition `limine.conf` is on, which is `/boot`; with ZFS it is the FAT partition, since limine cannot read
ZFS. The kernel has ext4 and the disk drivers as modules, so
the system needs the initramfs. The one from the ISO (`/mnt/boot/initrd`, copied in 3.3) finds the root by `root=UUID=` or
`root=ZFS=` and loads the modules in `iso/profile/modules`. Section 7.5 says how to make your own.

limine's files are in `/mnt/usr/share/limine`.

#### BIOS

    cp /mnt/usr/share/limine/limine-bios.sys /mnt/boot/
    limine bios-install /dev/sda

`limine bios-install` writes the loader to the start of the disk and into the BIOS boot partition. `limine-bios.sys` on
the FAT partition is the part it loads.

#### UEFI

    mkdir -p /mnt/boot/EFI/BOOT
    cp /mnt/usr/share/limine/BOOTX64.EFI /mnt/boot/EFI/BOOT/

The firmware starts `EFI/BOOT/BOOTX64.EFI` of the EFI System partition by itself.

Do both and the disk boots either way.

### 3.9 First boot

    umount -R /mnt
    zpool export rpool
    reboot

Leave out `zpool export` if the root is not on ZFS.

Take out the installation medium. limine shows the entry for three seconds and boots the kernel. `init` runs `/etc/rc`, which mounts the
file systems and starts the services of `init.conf`, and puts a login on the ttys. Log in as root.

Then:

1. Bring the network up (section 6.7).
2. `mag sync` fetches the pkgsrc tree (section 2.3). Mag's own recipes are in `/usr/share/mag/repo` already and the
   default `MAG_REPO` covers both, so `mag install name` works from then on, and the compiler is in the base set.
3. `mag list` shows what the bootstrap put on the machine.


## 4. Using mag

### 4.1 The commands

    Usage: mag [-nfk] COMMAND [PACKAGE]...

    install PKG...    fetch, build and install, dependencies first
    remove PKG...     take a package off
    upgrade           reinstall what the repos have a newer version of
    autoremove        remove what was only installed as a dependency and is not needed now
    list              what is installed
    info PKG          what a recipe says, and whether it is installed
    search WORD       recipes whose name or desc has WORD
    files PKG         the files a package put on the system
    owns PATH         which package a file came from
    deps PKG          its dependencies, rdeps PKG for what needs it
    fetch PKG...      only download and check the sources
    build PKG         build into a stage directory, install nothing
    sync              download the pkgsrc tree to /usr/pkgsrc
    hash FILE...      sha256 of files, for writing recipes

    -n  only say what would happen    -f  go on when files clash or something needs the package
    -k  keep the build directory

`add` is `install` and `del` is `remove`. `mag relocate` is the one command not in the usage text: it puts the real
loader and library paths into what was built in a `MAG_ROOT` (section 4.4). `mag --version` and `mag --help` do what
they say.

### 4.2 Installing and removing

    mag install shells/mksh
    mag install editors/vim net/tnftp
    mag -n install net/tnftp           what would be built, nothing is done
    mag remove vim

Packages are named as in the repo, `category/name`. `install` takes the dependencies first, downloads the source, checks
its sha256 against the recipe or the pkgsrc `distinfo`, builds into a staging directory, and then installs.

What `mag` guarantees when it installs:

* every file is checked against what other packages own before anything is touched; a clash stops it (`-f` goes on)
* files are put in place with a rename, so a running program is never half written
* a file under `/etc` that is already there stays, and the package's version is written next to it as `.new`
* each package keeps its file list in `var/lib/mag`, which is all `remove`, `files`, `owns` and `autoremove` use

`remove` stops when another package needs the one you remove; `-f` goes on. `autoremove` takes off the packages that
were installed only as dependencies and that nothing needs any more.

### 4.3 Finding things

    mag search editor              names and descriptions
    mag info net/tnftp              the recipe, its version, whether it is installed, its options
    mag deps net/tnftp              what it needs
    mag rdeps sys-libs/musl        what needs it
    mag files vim                  what an installed package put on the disk
    mag owns /usr/bin/vim          which package a file belongs to
    mag list                       everything installed

### 4.4 Installing somewhere else

`MAG_ROOT=/mnt mag install ...` installs and records in `/mnt` instead of `/`. This is how a new system is built
(chapter 3), and how the root of an ISO is built (chapter 8). The `etc/mag.conf` inside that root is the one used.

Once the root has musl, mag aims clang at it so that what is built can run on the host (section 9.4). `mag relocate`
puts the real paths back:

    MAG_ROOT=/mnt mag relocate

### 4.5 Other variables

| variable | meaning | default |
|----------|---------|---------|
| `MAG_ROOT`   | where to install | `/` |
| `MAG_REPO`   | repositories, split by colons | `/usr/share/mag/repo:/usr/pkgsrc` |
| `MAG_SYNC_URL` | the file `mag sync` fetches | NetBSD's `pkgsrc.tar.xz` |
| `MAG_FETCH`  | the download command, given a file and a URL | `ftp -o` |
| `MAG_PREFIX` | `$PREFIX` in the steps | `/usr` |
| `MAG_JOBS`   | `$JOBS` in the steps | `JOBS` of mag.conf, else 4 |
| `MAG_SH`     | the shell the steps run under | `/bin/sh` |

mag does not speak https itself; `MAG_FETCH` does, so `ftp` has to be on the machine.

### 4.6 pkgsrc options

Many pkgsrc packages have options (`PKG_OPTIONS`). mag works them out the way pkgsrc does: the package's suggested
options, then `PKG_DEFAULT_OPTIONS`, then `PKG_OPTIONS.name`, each word adding an option, or taking it off when it has a
minus. Put them in `/etc/mag.conf`:

    PKG_DEFAULT_OPTIONS=-http2 idn
    PKG_OPTIONS.vim=python

`mag info net/tnftp` shows the options a package ends up with, and its dependencies change with them. The recipes of
Chamesle's own repo have no options; they see `JOBS` and the flags only.

### 4.7 Writing a recipe

If pkgsrc does not have what you want, write a recipe. It is a file called `category/name` in a repository that comes
before pkgsrc in `MAG_REPO`. It can also be a directory with a file called `recipe` in it, when there are patches or
other files to carry: `$RECIPE_DIR` is that directory (`repo/dev-build/libtool` is one).

    desc: nl80211 wireless configuration tool
    version: 6.17
    url: https://cdn.kernel.org/pub/software/network/iw/iw-${version}.tar.xz
    sha256: 7d182e498289ab39b257da6780d562e415377107f50358ee5b55b8cfe40b1e33
    deps: net-libs/libnl devel/pkgconf
    steps:
    	make -j$JOBS
    	make PREFIX=$PREFIX DESTDIR=$DESTDIR install

The fields:

* `desc` is the line `mag search` matches and shows
* `version` is also `${version}` inside `url`
* `url` is the source archive; it is unpacked with its first directory stripped
* `sha256` is the checksum of that archive; `mag hash file.tar.xz` prints it
* `deps` are other packages, split by spaces, built first
* `steps:` is a block of lines that start with a tab, run as a plain `sh -e` script in the unpacked source

The steps see `$DESTDIR` (everything has to be installed there, never into the real root), `$PREFIX` (`/usr`), `$JOBS`,
`$NAME`, `$VERSION`, `$SRC` and `$RECIPE_DIR`. The package is made from what ends up in `$DESTDIR`.

Try it without installing:

    mag build net-wireless/iw          builds, says where the files are
    mag -k build net-wireless/iw       keeps the build directory too

and when it is right:

    mag install net-wireless/iw


## 5. rifle

### 5.1 What it is

rifle is the coreutils of Chamesle in one C file, `rifle.c`, on `c.h`, a one-file libc. It has no GNU code in it and no
libc under it. It sorts and compares by bytes, always; there are no locales.

There is one program. `cat`, `ls`, `cp` and the other commands are links to it, and it runs whichever name it was
called by. You type `cat`, not `rifle cat`.

### 5.2 The tools

    [ arch base32 base64 basename cat chgrp chmod chown chroot cksum comm cp cut date dd df dirname du echo env
    expand expr factor false fold groups head hostid hostname id install join link ln logname ls md5sum mkdir
    mkfifo mknod mktemp mv nice nl nohup nproc od paste printenv printf pwd readlink realpath rm rmdir seq
    sha1sum sha224sum sha256sum sha384sum sha512sum shuf sleep sort split stat sum sync tac tail tee test
    timeout touch tr true truncate tsort tty uname unexpand uniq unlink wc whoami yes

By what they do:

| group | tools |
|-------|-------|
| files and directories | `cp mv rm ln link unlink mkdir rmdir mkfifo mknod mktemp touch install truncate dd sync` |
| permissions and owners | `chmod chown chgrp` |
| looking at files | `ls stat du df cat tac head tail od nl wc cksum sum` |
| text | `cut paste join comm sort uniq tr fold expand unexpand split shuf tsort tee` |
| checksums and encodings | `md5sum sha1sum sha224sum sha256sum sha384sum sha512sum base32 base64` |
| names and paths | `basename dirname pwd readlink realpath` |
| scripts and processes | `echo printf printenv env test [ expr seq true false yes sleep nice nohup timeout chroot` |
| system and users | `arch uname hostname hostid id groups whoami logname date nproc tty` |
| numbers | `factor` (up to 64 bits) |

Not there yet: `stty`, `who` and friends, `fmt`, `pr`, `csplit`, `numfmt`, `shred`, `stdbuf`, `ptx`, `pathchk`,
`dircolors`.

### 5.3 Building

    cd $HOME/src/rifle
    ./build.sh

builds `rifle` with clang and lld (`CC` overrides `cc`) and makes the links in `bin/`. To put the links anywhere:

    rifle --install /usr/bin
    rifle --list                   the names it knows

### 5.4 Tests

    tests/run.sh                   all the cases
    tests/run.sh sort              the cases that have `sort` in them

Each case in `tests/cases` runs once under GNU coreutils and once under rifle, and what they print and how they exit
are compared. The machine that runs the tests therefore has GNU coreutils for the comparison; the installed system does
not. `./build.sh` has to have run first. A case that starts with `@ro` runs with the whole file system read-only under
`bwrap`, and is skipped when `bwrap` is missing.

mag has a test of its own: `mag/tests/run.sh` builds a fake repo with local tarballs and goes through install, upgrade
and remove in a scratch root. It needs ftp, tar and the rifle tools in PATH.


## 6. The base system

### 6.1 init

`/sbin/init` is a mksh script, and it works the way FreeBSD's init does: the kernel starts it as process 1, it runs
`/etc/rc`, then it keeps a getty on every tty and waits for a signal. The files are in `files/` in the sources and
`chamesle-bootstrap` copies them into the root. Step by step:

1. `PATH` is set to `/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin`. `proc`, `sysfs` and `devtmpfs`
   are mounted if they are not yet, and what init prints goes to `/dev/console`.
2. If `single` is on the kernel command line, init runs `sulogin` first.
3. `/etc/rc autoboot` runs (6.2). If it fails, init runs `sulogin` and goes on when you leave it.
4. For every name in `ttys` of `init.conf` that has a node in `/dev`, init starts a loop that runs the getty command
   again whenever it exits. A getty that dies within five seconds is run again after a pause of five.
5. init waits. A signal ends the wait:

| signal | what it does |
|--------|--------------|
| `INT`, `TERM` | reboot |
| `USR1` | halt: stop everything and stay stopped |
| `USR2` | power off |

6. Then it runs `/etc/rc.shutdown`, sends `TERM` to every process, `KILL` two seconds later, runs `sync`, `umount -a -r`
   and does the last step through `/proc/sysrq-trigger` (`b` or `o`). That needs `CONFIG_MAGIC_SYSRQ` in the kernel;
   the base set has no `reboot` program of its own that calls the kernel.

### 6.2 rc, init.conf and the services

`/etc/rc` mounts the system. In order: `/` is remounted read-write; with `autoboot`, `fsck -A -R -p` checks the
other file systems; `devpts` and `/dev/shm` are mounted; a tmpfs goes on `/run` (not on the live ISO, where
`/run/live` is already there); `mount -a` mounts `/etc/fstab`; `swapon -a`; `/tmp` is emptied if it is not a mount and
set to mode 1777; the host name is set; `dmesg` is saved in `/var/log/dmesg.boot`. Then every service in
`boot-services` is started, in the order it is written.

`/etc/init.conf` is the one configuration file. One setting per line, `key = value`, `#` starts a comment, blank
lines are ignored, spaces around `=` are free. A list is in braces and may go over several lines:

    hostname = chamesle

    # started in this order at boot, stopped in reverse at shutdown
    #boot-services = {NetworkManager,LightDM,dbus}
    boot-services = {udev,modules,network}

    modules = {}
    ttys = {tty1,ttyS0}
    getty = agetty --noclear $tty linux
    getty-ttyS0 = agetty -L $tty 115200 vt100

| key | meaning |
|-----|---------|
| `hostname` | the host name |
| `boot-services` | the services started at boot, in order; shutdown stops them in reverse |
| `modules` | kernel modules the `modules` service loads with `modprobe` |
| `ttys` | the ttys that get a getty |
| `getty` | the getty command; `$tty` is the tty name |
| `getty-NAME` | the getty command for that tty alone |

The parser is `conf` in `/etc/init.sh`; `conf KEY` prints the value, with a list separated by spaces. A change to
`ttys` or `getty` takes effect at the next boot.

A service is an executable file in `/etc/rc.d` (or `/usr/local/etc/rc.d`, for the ones you add) that takes
`start`, `stop`, `restart` or `status`. The base set has three: `udev` (starts `udevd`, replays the devices and waits
for them), `modules` and `network` (`dhcpcd`). A name in `boot-services` without a script is skipped with one line
saying so.

`service` is the way to run them:

    service -l                 every service
    service -e                 the services of boot-services, as paths
    service network restart
    service udev status

To add a service, write the script, make it executable, and put its name in `boot-services`. With
`/etc/rc.subr` it is short. Set `procname` to the name the process shows in `/proc/PID/comm`, write
`svc_start`, and finish with `run "$1"`; `stop` then kills that process, `status` looks for it and `start` refuses to
start it twice. Override `svc_stop` and `svc_status` if the defaults do not fit:

    #!/bin/sh
    . /etc/rc.subr
    procname=chronyd
    svc_start() { chronyd; }
    run "$1"

### 6.3 Shutting down

`reboot`, `halt` and `poweroff` send `INT`, `USR1` and `USR2` to init. `shutdown -r`, `-h` or `-p` does the same, at
once (`now`) or after `+minutes`, with an optional message sent through `wall`:

    shutdown -r now
    shutdown -p +10 back in ten minutes

### 6.4 The files in /etc

| file | what it holds |
|------|---------------|
| `passwd`, `group` | accounts and groups; no shadow file, the hash is in `passwd` |
| `shells` | `/bin/sh`, `/usr/bin/mksh`, `/usr/bin/ksh` |
| `init.conf` | host name, boot services, modules, ttys (6.2) |
| `fstab` | `proc`, `sysfs`, `tmpfs` on `/tmp`, plus the lines you add |
| `profile` | `PATH`, `EDITOR=vim`, `PAGER=less`, `umask 022` |
| `os-release` | `NAME=Chamesle`, `ID=chamesle` |
| `mag.conf` | `JOBS` and `CFLAGS` for mag |
| `skel/` | empty directory for the files new homes start from |

The login shell is mksh and `/etc/profile` is read by login shells. For a prompt and aliases make `~/.mkshrc` and set
`ENV=$HOME/.mkshrc` in `/etc/profile`.

### 6.5 Users

There is no `useradd`. To add `alice`:

    echo 'alice:HASH:1000:1000:alice:/home/alice:/usr/bin/mksh' >> /etc/passwd
    echo 'alice:x:1000:' >> /etc/group
    mkdir /home/alice
    chown 1000:1000 /home/alice

`HASH` comes from `openssl passwd -6` on a machine that has it. To put alice in `wheel`, add her name to the last field
of the `wheel:x:10:` line.

### 6.6 udev and modules

eudev is the udev. `udevd` gives devices their nodes in `/dev` and loads the modules the hardware needs. eudev is built
without the hardware database (`--disable-hwdb`).

kmod provides `modprobe`, `insmod`, `rmmod`, `lsmod`, `modinfo` and `depmod`. A kernel's modules are in
`/lib/modules/VERSION`. To load one by hand: `modprobe name`. To load one at every boot, put its name in `modules` of `/etc/init.conf`. To keep one from loading, put `blacklist name` in a file in `/etc/modprobe.d/`.

### 6.7 Networking

`dhcpcd` is the DHCP client and is in the base set. For a wired interface:

    dhcpcd eth0

`dhcpcd` without arguments takes every interface. It is the `network` service, in `boot-services` by default, so it is up at boot. `/sys/class/net/` lists the interfaces. For `ip`, install iproute2 from Chamesle's repo:

    mag install net-misc/iproute2

A static address:

    ip addr add 192.168.1.10/24 dev eth0
    ip link set eth0 up
    ip route add default via 192.168.1.1
    echo 'nameserver 192.168.1.1' > /etc/resolv.conf

### 6.8 Wireless

`iw` talks to the kernel's nl80211. It is in Chamesle's repo, with libnl:

    mag install net-wireless/iw
    iw dev                                       the wireless interfaces
    ip link set wlan0 up
    iw dev wlan0 scan | grep SSID

`sys-firmware/wireless-regdb` (in the base set) has the regulatory database, and the card's firmware is in
`/lib/firmware` from `sys-kernel/linux-firmware`. If `dmesg` says a firmware file failed to load, check that it is
there.

For an open network `iw dev wlan0 connect NAME` is enough. For WPA the connection needs `wpa_supplicant`; if your pkgsrc
tree has it (`mag search wpa`), install it, give it a configuration file with the `ssid` and the `psk`, and run it on the
interface. Then `dhcpcd wlan0`.

### 6.9 Mounting and disks

    mount /dev/sdb1 /mnt/usb
    mount -t vfat -o ro /dev/sdb1 /mnt/usb
    umount /mnt/usb

`mount`, `umount`, `lsblk`, `blkid`, `sfdisk`, `fdisk` and `cfdisk` are util-linux's, `zpool` and `zfs` are OpenZFS's, `mkfs.ext4` and `fsck.ext4` are
e2fsprogs', `mkfs.fat` is dosfstools'.

On a ZFS root, `/etc/rc` runs `zfs mount -a` right after `mount -a`, which mounts `rpool/home` and `rpool/var`; the root itself was
mounted by the initramfs.


## 7. The kernel and firmware

### 7.1 The kernel package

Nobody builds a kernel in Chamesle. `sys-kernel/linux` is a prebuilt Linux 6.18 LTS kernel with its modules, taken from a
binary mirror, with a generic configuration that runs on most machines. The recipe unpacks the package and installs

    /boot/vmlinuz-VERSION
    /boot/config-VERSION
    /boot/System.map-VERSION
    /lib/modules/VERSION/

`VERSION` is the one the package carries, such as `6.18.63-0-lts`. `sys-kernel/linux-headers` has the headers the libc
and util-linux build against.

### 7.2 Updating

The mirror drops a package when a newer one comes out, so a new kernel is a new `version` and `sha256` in the recipe.
Edit `repo/sys-kernel/linux`:

    version: 6.18.64
    sha256: the new one

Download the file the `url` names with the new version filled in, and take the checksum:

    ftp -o FILE URL
    mag hash FILE

Then:

    mag install sys-kernel/linux

and add an entry in `/boot/limine.conf` for the new `vmlinuz-VERSION`. Keep the old one until the new one has booted:

    /Chamesle
        protocol: linux
        path: boot():/vmlinuz-NEW
        cmdline: root=UUID=ROOT-UUID rw

    /Chamesle (old)
        protocol: linux
        path: boot():/vmlinuz-OLD
        cmdline: root=UUID=ROOT-UUID rw

After a reboot, `uname -r` says what runs.

### 7.3 Modules

Modules are `.ko` files in `/lib/modules/VERSION`. `lsmod` shows what is loaded, `modprobe name` loads a module with what
it needs, `modinfo name` describes it. udev loads the ones the hardware asks for. Modules belong to one kernel build:
after installing a new kernel, reboot before loading any.

### 7.4 Firmware

    mag install sys-kernel/linux-firmware

puts the firmware for wifi, graphics, ethernet and the rest, compressed with zstd, into `/lib/firmware`.
`sys-firmware/sof-firmware` has the sound firmware of newer Intel machines. Both are in the base set. A new firmware
release is a new `version` and `sha256` in `repo/sys-kernel/linux-firmware`, the same way as the kernel's.

### 7.5 An initramfs

A root on ext4 on a common disk (SATA, NVMe, virtio, USB storage) needs none. A root on ZFS needs one: the pool has to be
imported before the root can be mounted. A root that needs a module to be reached, or
RAID, LVM or an encrypted disk, does.

`iso/mkinitramfs` makes one, and the live ISO uses it:

    mkinitramfs [-m modules-file] ROOTFS KVER OUT

`ROOTFS` is the root whose `/lib/modules` and programs are used, `KVER` the name of the kernel's directory in
`/lib/modules`, `OUT` the file to write. It puts in a few tools (`sh mount umount switch_root insmod mkdir sleep blkid`, and `zpool` when the root has it,
with the libraries they need), the modules named in the modules file together with what they depend on, and `iso/init`.
The names after a `[zfs]` line of the modules file go into a second list, which `iso/init` loads only for `root=ZFS=`.
The result is a zstd compressed cpio.

    $HOME/src/system/iso/mkinitramfs -m modules /mnt 6.18.63-0-lts /mnt/boot/initrd

`iso/init` mounts `proc`, `sysfs` and `devtmpfs`, loads the modules, reads `root=` from the command line (`root=UUID=...`
or a device), waits up to 15 seconds for the device, mounts it read-only at `/mnt/root`, and runs
`switch_root /mnt/root /sbin/init`. With `root=ZFS=rpool/root` it loads the zfs modules, runs `zpool import -N -d /dev rpool`
(until it works, 15 seconds at most) and mounts the dataset with `mount -o zfsutil -t zfs`. If anything fails it prints why and drops into a shell.

Name the initrd in `limine.conf`:

    /Chamesle
        protocol: linux
        path: boot():/vmlinuz-6.18.63-0-lts
        module_path: boot():/initrd
        cmdline: root=UUID=ROOT-UUID rw

On ZFS the command line is `root=ZFS=rpool/root rw`. The ZFS module is `sys-kernel/zfs-module`, for the kernel of
`sys-kernel/linux`: when one is updated the other has to be too, and `depmod` has to run after installing it.


## 8. The live ISO

### 8.1 What it is

The ISO is a live system to work from. It boots on BIOS and UEFI machines with limine, from a disc or a stick, and has
mksh, vim, mag with Chamesle's recipes (`mag search` and `mag info` work before `mag sync`), `chamesle-bootstrap`,
`chamesle-chroot`, `chamesle-disk`, the disk tools (`cfdisk`, `sfdisk`, `mkfs.ext4`, `mkfs.fat`, `zpool`, `zfs`) and this handbook in
`/usr/share/doc/chamesle/handbook.md`. It is where you do chapter 3 on a machine that has nothing on it.

### 8.2 Building

The machine that builds needs `mksquashfs` (filesystems/squashfs), `xorriso` (sysutils/libisoburn), `zstd`, `bsdcpio`,
`limine` and `mag`, plus what chamesle-bootstrap needs.

    $HOME/src/system/iso/mkiso -r $HOME/src/mag/repo:/usr/pkgsrc

The usage:

    chamesle-chroot DIR [COMMAND...]
    chamesle-disk DISK
    mkiso [-p profile] [-r repos] [-R rootfs] [-w workdir] [-o out.iso]

* `-p` is the profile directory (default `iso/profile`)
* `-r` is `MAG_REPO`
* `-R` uses a root you have already built, copied and not changed, instead of building one
* `-w` is the work directory (default `./work`)
* `-o` is the file to write (default `chamesle.iso`)

Environment: `LIMINE` is where limine's files are (default `/usr/share/limine`), `MKISOFS` is the command that makes the
ISO (default `xorriso -as mkisofs`), `MAG` is the mag to put into the image, `MAGREPO` the repo whose recipes it carries
in `/usr/share/mag/repo` (default: the `repo` next to a mag checkout, else the first `MAG_REPO` entry with a `PROVIDES` file).

In order:

1. `chamesle-bootstrap` builds a root from `profile/packages`, with the host name `chamesle-live`.
2. `profile/overlay` is copied over it.
3. `chamesle-bootstrap`, `chamesle-chroot`, `chamesle-disk`, the handbook, `mag` and its recipes are put into it.
4. The kernel from `boot/vmlinuz-*` is copied to the ISO, and `depmod` runs on the root.
5. `mkinitramfs` makes `boot/initrd` from `profile/modules`.
6. The root is written as a zstd squashfs, `LiveOS/rootfs.sfs`.
7. limine's boot files are copied and `profile/limine.conf` becomes `boot/limine/limine.conf`.
8. `xorriso` writes the ISO with the BIOS and UEFI boot images and `limine bios-install` makes it bootable on BIOS.

A root built that way still has its build-time loader paths (section 4.4). To relocate it, and to put rifle in it, build
the root yourself and hand it over:

    MAG_REPO=$HOME/src/mag/repo:/usr/pkgsrc $HOME/src/system/tools/chamesle-bootstrap \
        -s "$(grep -v '^#' $HOME/src/system/iso/profile/packages | tr '\n' ' ')" -n chamesle-live /srv/rootfs
    MAG_ROOT=/srv/rootfs mag relocate
    install -m755 $HOME/src/rifle/rifle /srv/rootfs/usr/bin/rifle
    $HOME/src/rifle/rifle --install /srv/rootfs/usr/bin
    $HOME/src/system/iso/mkiso -R /srv/rootfs -o chamesle.iso

### 8.3 The profile

    iso/profile/packages        packages of the live root, one per line, # for comments
    iso/profile/modules         modules the initramfs loads to find the medium
    iso/profile/limine.conf     boot menu
    iso/profile/overlay/        files copied over the root: etc/motd

`packages` is the base set of chapter 3. `modules` lists `squashfs overlay loop isofs sr_mod cdrom sd_mod usb_storage uas
xhci_pci ehci_pci ahci ata_piix ata_generic pata_acpi virtio_blk nvme virtio_pci virtio_scsi ext4 vfat nls_cp437
nls_iso8859_1`, one per line, then a `[zfs]` line and `zfs`, which only a root on ZFS loads. The boot entry:

    timeout: 3

    /Chamesle live
        protocol: linux
        path: boot():/boot/vmlinuz
        module_path: boot():/boot/initrd
        cmdline: quiet

### 8.4 How it boots

`iso/init` looks through `/dev/sr*`, `/dev/sd*`, `/dev/nvme*n*p*`, `/dev/vd*` and `/dev/mmcblk*` until it finds one that
mounts and has `LiveOS/rootfs.sfs`. It mounts that squashfs read-only, puts a tmpfs overlay over it, moves the medium and
the squashfs to `/run/live/medium` and `/run/live/rootfs`, and runs `switch_root` into the result. Whatever you change
in the live system is gone at shutdown.

### 8.5 Trying it in qemu

BIOS:

    qemu-system-x86_64 -cpu max -m 1G -cdrom chamesle.iso -boot d

UEFI, with the firmware of your qemu (`edk2-x86_64-code.fd`; the path differs between systems):

    qemu-system-x86_64 -cpu max -m 1G -bios /usr/share/qemu/edk2-x86_64-code.fd -cdrom chamesle.iso

Add `-enable-kvm` for speed. To go through all of chapter 3 in a virtual machine, give it a disk:

    qemu-img create -f qcow2 disk.qcow2 20G
    qemu-system-x86_64 -cpu max -m 2G -enable-kvm -cdrom chamesle.iso -drive file=disk.qcow2 -boot d -nic user

To write the ISO to a stick: `dd if=chamesle.iso of=/dev/sdX bs=4M conv=fsync`.


## 9. Maintaining

### 9.1 Updating packages

    mag -n upgrade
    mag upgrade

The first says what would be rebuilt, the second reinstalls whatever the repos have a newer version of. pkgsrc itself is
updated with `mag sync` (section 2.3). One package: `mag install name`. When you work with
`MAG_ROOT` set, run `mag relocate` afterwards.

### 9.2 Cleaning up

    mag autoremove                  dependencies nothing needs any more
    rm -rf /var/cache/mag/*         downloaded sources; they are fetched again when needed

### 9.3 C23 and CFLAGS

clang compiles C as C23 by default. Older programs written for C89 or C99 stop with errors about `bool`, `true` or
`false` used as names, or about functions declared as `int f()` and called with arguments. `CFLAGS=-O2 -std=gnu17` in
`mag.conf` makes the compiler use C17 for every build. It is in the file chamesle-bootstrap writes; if you wrote your
own `mag.conf` without it, add it.

To see the error of a failed build, run `mag -k install name`: the build directory is kept, and the error is above the
line that says `the steps failed, left in ...`.

### 9.4 The root's compiler and mag relocate

When `MAG_ROOT` has musl in it (`usr/lib/crt1.o` and `usr/lib/libc.so`), mag makes a `cc` script in the build directory
and puts it first in `PATH`, with `gcc`, `clang` and `c99` as links to it. It runs the clang of the host with
`--target=x86_64-linux-musl`, `--sysroot` and `-isystem` pointed at the root, lld, compiler-rt, and the loader and
library paths set to the ones in the root, so that what was built runs on the host. `-lgcc`, `-lgcc_s` and `-lgcc_eh`
are dropped from the command line because compiler-rt replaces them.

A program built that way names `/mnt/usr/lib/libc.so` as its loader and `/mnt/usr/lib` as its library path. On the real
system neither exists, and running the program says "not found" although the file is there. `mag relocate` goes
through `usr`, `bin`, `sbin` and `lib` in the root and puts back `/lib/ld-musl-x86_64.so.1` and `/usr/lib`. Run it before
the first boot and after every install into a `MAG_ROOT`.

If there is no `clang` in `PATH` outside the root, mag stops with "no clang in PATH: it is the compiler for a musl root".

### 9.5 libtool

pkgsrc packages that use libtool expect a `libtool` script. `dev-build/libtool` is a small one of Chamesle's that
compiles, links and installs shared and static libraries; kmod, for example, is built with `LIBTOOL=libtool`. If a
package fails at a libtool step, read `repo/dev-build/libtool/libtool`, and for a package that insists on its own
libtool pass `LIBTOOL=libtool` to its `make`.

### 9.6 Failures you will see

| what you see | why, and what to do |
|--------------|---------------------|
| `no recipe for NAME` | the name is in no repo of `MAG_REPO`; try `mag search`, and check the pkgsrc path is in `MAG_REPO` |
| a checksum mismatch | the download is not the one the recipe names; for the kernel see section 7.2 |
| `no clang in PATH` | the build host has no clang outside the new root; install one |
| a program says `not found` though the file is there | its loader path is the one of the build: `MAG_ROOT=... mag relocate` |
| files clash, or a package cannot be removed | another package owns the file or needs the package; read what mag says, `-f` goes on |
| errors on `bool`, `true`, `false` or on old declarations | C23; `CFLAGS=-O2 -std=gnu17` (section 9.3) |
| musl's build fails | `gmake` is missing on the host |
| "root device not found" at boot | the kernel cannot see the disk or the file system: it needs a module, use an initramfs (section 7.5) |
| the machine boots to a limine prompt | `limine.conf` is not found, or its `path:` does not name a file in `/boot`; check with `ls /boot` |
| a BIOS machine does not boot | `limine bios-install /dev/sda` was not run, or `limine-bios.sys` is not in `/boot` |
| a UEFI machine does not boot | `EFI/BOOT/BOOTX64.EFI` is not on the EFI partition, or the partition is not of type EFI System |
| a login without a password | the password field of `passwd` is empty |
| no devices in `/dev` | udev did not start; check that `udevd` is installed with `mag list` |

### 9.7 Keeping a build

    mag -k install name

keeps the build directory. `mag fetch name` downloads and checks the sources without building, and `mag build name` builds
into a staging directory and prints where the files are.


## 10. File reference

### 10.1 On an installed system

| path | what |
|------|------|
| `/sbin/init`, `/etc/rc`, `/etc/rc.shutdown` | init, the boot script, the shutdown script, all run by mksh |
| `/etc/init.conf` | host name, boot services, modules, ttys |
| `/etc/rc.d/`, `/usr/local/etc/rc.d/` | the service scripts |
| `/etc/services`, `/etc/hosts` | port names and the local host name, the libc reads them |
| `/etc/profile` | `PATH`, `EDITOR`, `PAGER`, `umask` |
| `/etc/passwd`, `/etc/group`, `/etc/shells` | accounts, groups, login shells |
| `/etc/fstab` | file systems |
| `/etc/os-release` | `NAME=Chamesle`, `ID=chamesle` |
| `/etc/mag.conf` | mag's build settings: `JOBS`, `CFLAGS`, `PKG_DEFAULT_OPTIONS`, `PKG_OPTIONS.name` |
| `/boot/limine.conf` | the boot entries |
| `/boot/limine-bios.sys` | limine's BIOS stage |
| `/boot/EFI/BOOT/BOOTX64.EFI` | limine for UEFI |
| `/boot/vmlinuz-V`, `config-V`, `System.map-V` | the kernel |
| `/lib/modules/V/` | its modules |
| `/lib/firmware/` | firmware |
| `/var/lib/mag/` | the file list of each installed package |
| `/var/cache/mag/` | downloaded sources |
| `/usr/share/limine/` | limine's boot files, for installing it |
| `/usr/share/doc/chamesle/handbook.md` | this book, on the live ISO |
| `/usr/share/mag/repo/` | Chamesle's recipes |
| `/usr/pkgsrc/` | the pkgsrc tree, from `mag sync` |

### 10.2 In the sources

| path | what |
|------|------|
| `system/tools/chamesle-bootstrap` | makes a root file system and builds the base set into it |
| `system/tools/chamesle-chroot` | chroot with the pseudo file systems mounted |
| `system/tools/chamesle-disk` | cfdisk, vfat boot partition, ZFS root, mounted on `/mnt` |
| `system/files/` | init, rc, `service`, `init.conf` and the service scripts that go into every root |
| `system/iso/mkiso` | builds the live ISO |
| `system/iso/mkinitramfs` | builds an initramfs |
| `system/iso/init` | the first process in the initramfs |
| `system/iso/profile/packages` | what is in the live root |
| `system/iso/profile/modules` | what the initramfs loads |
| `system/iso/profile/limine.conf` | the live boot menu |
| `system/iso/profile/overlay/` | files copied over the live root |
| `system/handbook/handbook.md` | this book |
| `mag/mag.c`, `mag/build.sh`, `mag/c.h` | the package manager and its libc |
| `mag/tests/run.sh` | tests on a fake repo: install, upgrade, remove in a scratch root |
| `mag/repo/PROVIDES` | pkgsrc packages replaced or skipped, and dependencies added |
| `mag/repo/sys-libs/musl` | the libc |
| `mag/repo/sys-kernel/{linux,linux-headers,linux-firmware,zfs-module}` | kernel, headers, firmware, the ZFS module |
| `mag/repo/sys-fs/zfs` | ZFS userland: `zpool`, `zfs` |
| `mag/repo/sys-boot/limine` | the boot loader |
| `mag/repo/sys-apps/{eudev,kmod,util-linux,usbutils}` | udev, module tools, the basics, usb tools |
| `mag/repo/net-libs/libnl`, `net-wireless/iw`, `net-misc/iproute2` | network tools |
| `mag/repo/sys-firmware/{sof-firmware,wireless-regdb}` | firmware extras |
| `mag/repo/dev-libs/netbsd-curses`, `dev-build/libtool` | curses and libtool |
| `rifle/rifle.c`, `rifle/c.h`, `rifle/build.sh` | the coreutils |
| `rifle/tests/run.sh`, `rifle/tests/cases` | the comparison tests |

### 10.3 Commands in short

    chamesle-bootstrap [-r REPOS] [-s PACKAGES] [-n HOSTNAME] TARGET
    mkiso [-p profile] [-r repos] [-R rootfs] [-w workdir] [-o out.iso]
    mkinitramfs [-m modules] ROOTFS KVER OUT
    mag [-nfk] install|remove|upgrade|autoremove|list|info|search|files|owns|deps|rdeps|fetch|build|sync|relocate|hash
    rifle --install DIR | --list
    limine bios-install DEVICE
