# The Chamesle Handbook

1. About Chamesle
2. Preparing
3. Installing
4. mag
5. rifle
6. The base system
7. The kernel and firmware
8. The live ISO
9. Maintaining
10. File reference


## 1. About Chamesle

### 1.1 What it is

Chamesle is a small Linux distribution on musl, installed from the ISO. Nothing is compiled: `chamesle-bootstrap` puts
the base into an empty root with the package manager. `chamesle-install` does the whole install from a few questions,
or you do it by hand, writing the fstab, the password and the boot entry yourself. This handbook goes through every step.

The parts:

| part   | what it is |
|--------|------------|
| kernel | a prebuilt Linux LTS kernel with its modules |
| musl   | the C library |
| mag    | the package manager, binary packages only, in one C file |
| rifle  | the coreutils, all in one C file; `cat`, `ls`, `cp` and the rest are links to one program |
| mksh   | the login shell; `/bin/sh` is busybox's ash |
| init   | OpenRC, the services come with their packages |
| limine | the boot loader, BIOS and UEFI |

Chamesle is made to be the most UNIX distribution possible, and to run on almost anything: the same base goes on a new
laptop and on a Pentium 4 with 256 MB of memory. It is a system for the tty first. Anything else is a `mag install` away.

### 1.2 Where the packages come from

mag reads two kinds of repository, both signed:

* Chamesle's own, at `https://chamesle.org/repo`: `chamesle-base` (the files in `/etc`, the tools of this
  book and the keys), `mag` and `rifle`
* a large musl repository with everything else: the kernel, the firmware, the libraries, editors, compilers, X, about
  28,000 packages for x86_64

Both are in `/etc/mag/repos`. A package is checked against the keys in `/etc/mag/keys` before anything of it is unpacked.

### 1.3 The glibc Chamesle

There is a second Chamesle on glibc, for what musl cannot run: NVIDIA's driver, Steam, programs that only come built for
glibc. It is the same idea on other packages. mag, rifle, the tools and OpenRC are the same; the packages are Artix's
and Arch's, about 25,000, and anything else comes from the AUR, built here. `chamesle-install` asks which one you want,
`chamesle-bootstrap -l glibc` makes it by hand (3.12).

| part   | musl Chamesle | glibc Chamesle |
|--------|---------------|----------------|
| kernel | Linux LTS | Linux, latest (`linux-lts` and `linux-zen` are there too) |
| initramfs | mkinitfs | mkinitcpio |
| file systems | ZFS, btrfs, ext4 | btrfs, ext4 |
| login shell | mksh | bash |
| packages | ~28,000 | ~25,000, and the AUR |

On glibc, coreutils owns `/usr/bin/ls` and the rest, so rifle's links are in `/usr/lib/rifle/bin`, which a login shell
puts first in PATH (`/etc/profile.d/rifle.sh`).

### 1.4 The layout of the system

    /bin /sbin /lib     /lib holds the musl loader and the firmware
    /usr/bin /usr/sbin  programs, /usr/lib libraries, /usr/share data
    /usr/local/bin      yours, first in PATH
    /boot               kernel, initramfs, limine.conf (on the EFI partition)
    /etc                configuration; /etc/mag is mag's
    /lib/modules        kernel modules, one directory per kernel version
    /lib/firmware       firmware for the hardware
    /var/lib/mag        which package owns which file
    /var/cache/mag      downloaded indexes and packages
    /run /tmp           tmpfs, made new at every boot

### 1.5 Where the sources are

| directory | what is in it |
|-----------|---------------|
| `system/` | `tools/` (`chamesle-bootstrap`, `chamesle-disk`, `chamesle-boot`, and `mkapk`, `mkrepo`, `mkpkgs` for the repo), `files/` (init, rc and the services), `pkg/`, `keys/`, `iso/`, this handbook |
| `mag/`    | `mag.c`, `c.h`, `build.sh` |
| `rifle/`  | `rifle.c`, `build.sh`, `tests/run.sh` |

They are on github.com/tortr-rs.


## 2. Preparing

### 2.1 What you need

* the ISO, from chamesle.org, written to a stick or a disc (chapter 8). It has everything chapter 3 uses
* a network connection: the packages come from the repositories
* about 1 GB of disk for a base system with a kernel, more for what you add
* 256 MB of memory is enough to install and to run

The CPU can be x86_64, or a 32-bit x86 one from the Pentium 4 on (section 3.10).

### 2.2 From another Linux

The ISO is the easy way, but any Linux machine can install Chamesle. It needs `mag`, the keys and the repos:

    curl -LO https://chamesle.org/repo/x86_64/mag-0.3.apk
    tar -xzf mag-0.3.apk usr/bin/mag
    mkdir -p /etc/mag
    cp -R keys /etc/mag/keys
    cp pkg/chamesle-base/repos /etc/mag/repos
    install -m755 usr/bin/mag /usr/local/bin/mag

`keys/` and `pkg/chamesle-base/repos` are in `system/` of the sources. The `tar` line warns about the signature and
control parts it does not know; the program comes out all the same. mag is static, so it runs on any distribution.
From there chapter 3 is the same, without the live system.

### 2.3 Getting on the network

On the live system a cable works by itself: `dhcpcd` runs at boot. Check it with

    ip addr
    ping -c 3 chamesle.org

For wireless, `iwctl` (iwd runs at boot on the ISO):

    iwctl device list
    iwctl station wlan0 scan
    iwctl station wlan0 get-networks
    iwctl station wlan0 connect NAME

It asks for the passphrase. dhcpcd gives the interface an address once it is connected.


## 3. Installing

The live system has `chamesle-install`, which asks for the disk, the file system (ZFS, btrfs or ext4), the bootloader
(limine or GRUB), the firmware (what the machine has is ticked), wifi, the host name, the root password and a user, and
then does this chapter on the whole disk. The log is `/var/log/chamesle-install.log`, and a copy is kept on the new
system. The rest of the chapter is the same install by hand, for another layout or to know what it did.

Follow the BIOS or the UEFI variant where they differ. The disk here is `/dev/sda`; change it to yours. Everything below
is run as root on the live system, and it erases the disk.

There are two ways through 3.1 and 3.2: `chamesle-disk` does the partitioning and the file systems, or you do both
yourself. From 3.3 on the steps are the same, and they are yours:
`chamesle-disk` is only a helper.

### 3.1 chamesle-disk

    chamesle-disk /dev/sda
    chamesle-disk -t btrfs /dev/sda
    chamesle-disk -t ext4 -y /dev/sda

`-t` is the file system of the root: `zfs` (the default), `btrfs` or `ext4`. btrfs gets the subvolumes `@` for `/`
and `@home` for `/home`, mounted with `compress=zstd`. `-y` asks nothing and lays out the whole disk as in the table
below.

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
    zfs mount rpool/root
    zfs create -o mountpoint=/home rpool/home
    zfs create -o mountpoint=/var rpool/var
    zpool set bootfs=rpool/root rpool

and mounts `rpool/root`, `rpool/home` and `rpool/var` under `/mnt` and the boot partition on `/mnt/boot`. It also writes
`/mnt/etc/fstab` with the boot partition by UUID and the `proc`, `sysfs` and `tmpfs` lines. It writes nothing else.

ZFS mounts its own datasets, so the fstab does not list them. limine cannot read ZFS: the kernel, the initramfs and
`limine.conf` live on the FAT partition, which is `/boot`.

ZFS on a machine with little memory is slow; on the 256 MB machine use ext4 (3.2).

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
UEFI.

### 3.3 chamesle-bootstrap

    chamesle-bootstrap /mnt

That is the whole base. It copies `/etc/mag/repos` and `/etc/mag/keys` of the live system into `/mnt`, runs
`mag update` there, and installs `chamesle-base`, the kernel (`linux-lts`) and its firmware with everything they need. The
kernel package writes `vmlinuz-lts` and `initramfs-lts` into `/mnt/boot`. It takes as long as the download, a few minutes.

    chamesle-bootstrap [-a ARCH] [-n HOSTNAME] [-k KERNEL] [-f FIRMWARE] TARGET [PACKAGE]...

| option | what |
|--------|------|
| `-n` | the host name, `chamesle` if not given |
| `-f` | the firmware package. The default, `linux-firmware-none`, has no firmware; take the one your hardware needs (7.4) |
| `-k` | the kernel package, `linux-lts` if not given |
| `-a` | the architecture, the machine's own if not given (3.10) |

Packages after the target go in too. A ThinkPad with Intel wireless and graphics, with an editor:

    chamesle-bootstrap -n t480 -f linux-firmware-intel /mnt vim

What `chamesle-base` brings: OpenRC and the files of chapter 6, mag, rifle, mksh, busybox for the tools rifle does not
have, bash, `agetty`, eudev, kmod, dhcpcd, e2fsprogs, curl and `arch-chroot`.

### 3.4 Working inside the new root

    arch-chroot /mnt
    arch-chroot /mnt passwd root

`arch-chroot` is Arch's, the same script. It mounts `proc`, `sys`, `dev`, `dev/pts`, `dev/shm`, `run` and `tmp` under
the directory, puts the live system's `/etc/resolv.conf` in it, and takes the mounts away again when the command ends.
Without a command it starts bash. Inside, `mag install name` works as on the finished system.

### 3.5 fstab

If you used chamesle-disk the file is written. Look at it: the boot partition by UUID on `/boot`, then `proc`, `sysfs`
and `tmpfs`, and nothing for the ZFS datasets, because ZFS mounts them itself.

By hand, `blkid` prints the UUIDs:

    blkid /dev/sda2 /dev/sda3

Write `/mnt/etc/fstab`:

    UUID=ROOT-UUID  /      ext4   defaults        0 1
    UUID=BOOT-UUID  /boot  vfat   defaults        0 2
    proc            /proc  proc   defaults        0 0
    sysfs           /sys   sysfs  defaults        0 0
    tmpfs           /tmp   tmpfs  nosuid,nodev    0 0

A root on ZFS gets no root line.

### 3.6 Host name and password

The host name is in `/mnt/etc/hostname`, from `-n`. Set the root password:

    arch-chroot /mnt passwd root

The hash goes into `/etc/shadow`. The login shell of root is mksh.

### 3.7 The boot entry

    chamesle-boot /mnt
    chamesle-boot -b grub /mnt

`-b grub` installs GRUB instead of limine, for UEFI and for BIOS, and writes `/boot/grub/grub.cfg` the same way.

It looks at what is mounted on `/mnt` and `/mnt/boot` and

* installs `limine` into the new root, so its boot files and its `limine` are the same version
* for a root on ZFS, installs `zfs` and `zfs-lts`, adds `zfs` to the initramfs (7.5) and `zfs-import` and
  `zfs-mount` to the sysinit runlevel; for btrfs, installs `btrfs-progs`, adds `btrfs` to the initramfs and puts the
  subvolume on the kernel command line
* writes `/mnt/boot/limine.conf` with an entry for every kernel in `/mnt/boot`, the root by UUID, or by dataset on ZFS
* copies `BOOTX64.EFI` to `EFI/BOOT/` on the boot partition, for UEFI
* runs `limine bios-install` on the disk, for BIOS; on a GPT disk only when it has a BIOS boot partition, else it says
  the disk boots by UEFI only

An old `limine.conf` is kept as `limine.conf.old`. If `/boot` is not FAT, limine cannot read it; chamesle-boot then
writes nothing and prints an entry for the GRUB of the system already on the machine (3.11).

What it does by hand follows; skip to 3.8 if it said nothing went wrong.

    ls /mnt/boot
    System.map-7.3.5-0-lts  config-7.3.5-0-lts  initramfs-lts  vmlinuz-lts

The names stay the same when the kernel is updated, so `limine.conf` is written once. `/mnt/boot/limine.conf`, with
the UUID of the root partition:

    timeout: 3

    /Chamesle
        protocol: linux
        path: boot():/vmlinuz-lts
        module_path: boot():/initramfs-lts
        cmdline: root=UUID=ROOT-UUID modules=sd-mod,usb-storage,nvme,ext4 rootfstype=ext4 quiet

`boot()` is the partition `limine.conf` is on, which is `/boot`. The initramfs finds the root, loads the modules on the
command line and starts `/sbin/init`. Take `quiet` out to see the kernel's messages. For a serial console add
`console=ttyS0,115200`.

A root on ZFS names the dataset; the initramfs needs the zfs module, which is section 7.5:

        cmdline: root=ZFS=rpool/root rootfstype=zfs quiet

Install limine into the new root, and use its files, not the ones of the live system; the two can differ in version, and
limine's BIOS stage only works with a `limine-bios.sys` of its own version:

    arch-chroot /mnt mag install limine

#### BIOS

    cp /mnt/usr/share/limine/limine-bios.sys /mnt/boot/
    arch-chroot /mnt limine bios-install /dev/sda

`limine bios-install` writes the loader to the start of the disk and into the BIOS boot partition, which a GPT disk
needs (3.1). `limine-bios.sys` on the FAT partition is the part it loads.

#### UEFI

    mkdir -p /mnt/boot/EFI/BOOT
    cp /mnt/usr/share/limine/BOOTX64.EFI /mnt/boot/EFI/BOOT/

The firmware starts `EFI/BOOT/BOOTX64.EFI` of the EFI System partition by itself.

Do both and the disk boots either way.

### 3.8 First boot

    umount -R /mnt
    zpool export rpool
    reboot

Leave out `zpool export` if the root is not on ZFS.

Take out the installation medium. limine shows the entry for three seconds and boots the kernel. OpenRC mounts the
file systems, starts the services of the runlevels and puts a login on the ttys. Log in as root. `dhcpcd` brings up a
cable at boot; for wireless see section 6.8.

### 3.9 What to install next

    mag install vim htop tmux
    mag search irc

Chapter 4 has the rest, chapter 10 a graphical desktop.

### 3.10 32-bit machines

On a 32-bit PC (Pentium 4, Athlon XP and the like) boot the ISO on another machine, or install from any Linux there
(2.2), and give the architecture:

    chamesle-bootstrap -a x86 /mnt

The x86 repository has the same packages, built for i686 with SSE2. `-a x86` is written to `/mnt/etc/mag/arch`, and mag
keeps to it from then on. `rifle` is only built for x86_64, so on x86 busybox gives the coreutils. limine boots 32-bit
BIOS machines as well; the entry is the same.


### 3.11 Next to another system

To keep a Linux that is already on the disk, Chamesle goes on a partition of its own and the other system's GRUB boots
both. The other system is not changed, except for one GRUB entry. Make a backup first; shrinking a file system that is
in use is not possible, so it is done from the ISO.

Say the disk has an EFI partition `nvme0n1p1` and the other system's ext4 root `nvme0n1p2`, 238G with 100G free.
Shrink it to 170G and make the file system fit its partition again:

    e2fsck -f /dev/nvme0n1p2
    resize2fs /dev/nvme0n1p2 170G
    cfdisk /dev/nvme0n1

In cfdisk resize `nvme0n1p2` to 171G (a little more than the file system, never less), make `nvme0n1p3` in the free
space, write and quit. Then

    resize2fs /dev/nvme0n1p2
    mkfs.ext4 /dev/nvme0n1p3
    mount /dev/nvme0n1p3 /mnt

Leave the EFI partition alone and do not mount anything on `/mnt/boot`: the kernel stays in `/boot` on the ext4 root,
where GRUB reads it. Go on with 3.3 to 3.6. `chamesle-boot /mnt` then prints a GRUB entry; boot the other system, put
the entry at the end of its `/etc/grub.d/40_custom` and run `grub-mkconfig -o /boot/grub/grub.cfg`.

To use the same home in both, mount the other root in Chamesle and bind its `/home`, in `/etc/fstab`:

    UUID=OTHER-ROOT-UUID /old ext4 defaults 0 2
    /old/home /home none bind 0 0

and make your user with the same name, user number and group number as there (`id` on the other system says them):

    mkdir /old
    addgroup -g 1000 alice
    adduser -H -u 1000 -G alice alice

`-H` makes no home, since the other system's is used: the files, the dotfiles and the settings of the programs are the
same in both systems.

### 3.12 The glibc Chamesle

The install is the same, with `-l glibc` for chamesle-bootstrap. ZFS is not there: neither Artix nor Arch carries it, so
the root is btrfs or ext4.

    chamesle-disk -t btrfs -y /dev/sda
    chamesle-bootstrap -l glibc -n box -f "linux-firmware-intel linux-firmware-realtek" /mnt networkmanager networkmanager-openrc

The repos and keyrings come from `/usr/share/chamesle/glibc` on the live system. `-k` is the kernel (`linux`, or
`linux-lts`, `linux-zen`); `-f` the firmware, split by vendor as in Arch (`linux-firmware-amdgpu`, `-nvidia`,
`-atheros`, `-broadcom`, `-mediatek`, or `linux-firmware` for all of it). For an NVIDIA card, add `nvidia-open
nvidia-utils`. Users are made with `useradd`, services have their names from Artix (`NetworkManager`, `iwd`):

    echo root:PASSWORD | arch-chroot /mnt chpasswd
    arch-chroot /mnt useradd -m -G wheel,video,input,audio alice
    arch-chroot /mnt passwd alice
    arch-chroot /mnt rc-update del dhcpcd default
    arch-chroot /mnt rc-update add NetworkManager default
    chamesle-boot /mnt

chamesle-boot sees the glibc system and writes the entries for mkinitcpio's `initramfs-linux.img`.


## 4. mag

mag is the package manager. It installs binary packages from the repositories in `/etc/mag/repos`, checks every index
and every package against `/etc/mag/keys`, and keeps what it installed in `/var/lib/mag`. It is one C file and runs
nothing but the download command, and bash when it builds from a source tree (4.6, 4.7).

### 4.1 The commands

    mag update                 get the index of every repo
    mag install PKG...         install, with what they need
    mag build PKG...           build them from a source tree: CRUX, Void or Exherbo (4.6, 4.7)
    mag remove PKG...          take packages off
    mag upgrade                install what the repos have a newer version of
    mag autoremove             remove what was only a dependency and is not needed now
    mag list                   what is installed
    mag info PKG               version, size, description, and whether it is installed
    mag search WORD            names and descriptions
    mag files PKG              the files a package put on the system
    mag owns PATH              which package a file came from
    mag deps PKG               what it needs; rdeps PKG for what needs it
    mag fetch PKG...           only download them

`-n` says what would happen and does nothing, `-f` goes on when files clash or something still needs a package.
`MAG_ROOT=/mnt mag ...` works on another root, which is what chamesle-bootstrap does.

### 4.2 Installing and removing

    mag install vim
    mag -n install xorg-server      what would come with it
    mag remove vim

Before it unpacks anything, mag checks each file against what other packages own and stops if two packages want the same
file. A file under `/etc` that you changed stays, and the new one is written next to it as `NAME.new`. Packages carry
scripts that run after they are installed, and triggers that run when a directory they watch changes, like the one
that makes the initramfs when a kernel is installed.

A name can also be what a package provides: `mag install cmd:htop` installs the package that has the command.

### 4.3 Where it keeps things

| what | where |
|------|-------|
| the repositories | `/etc/mag/repos`, one URL a line |
| the keys | `/etc/mag/keys` |
| the architecture | `/etc/mag/arch` |
| installed packages | `/var/lib/mag/NAME/`: `version`, `files`, `deps`, `explicit` and the scripts |
| indexes and downloads | `/var/cache/mag` |

### 4.4 Repositories

    https://chamesle.org/repo
    https://dl-cdn.alpinelinux.org/alpine/edge/main
    https://dl-cdn.alpinelinux.org/alpine/edge/community

Each line is the URL above the directory of the architecture: mag adds `/x86_64/APKINDEX.tar.gz`. A repository you
add needs its key in `/etc/mag/keys`. `mag update` after any change.

### 4.5 Making a package

`tools/mkapk` packs a directory, signs it and leaves its index entry; `tools/mkrepo` signs the index of a directory of
them:

    mkapk -k KEY -n hello -v 1.0 -a x86_64 -d "says hello" -D "musl" -o repo/x86_64 ./root
    mkrepo repo/x86_64 KEY

Put the public half of KEY in `/etc/mag/keys` and the repo's URL in `/etc/mag/repos`. `tools/mkpkgs` is how Chamesle's
own repo is made.

### 4.6 CRUX ports

mag also builds from CRUX's port trees. A line that starts with `crux` is a tree of ports, and its key goes next to the
others:

    echo 'crux https://crux.nu/ports/crux-3.8/opt' >> /etc/mag/repos
    curl -o /etc/mag/keys/opt.pub https://crux.nu/ports/crux-3.8/core/ports/opt.pub
    mag update
    mag build foo

`mag update` gets only the ports that changed, as httpup does, into `/var/cache/mag`. Every port's `.signature` is
checked with the key, then its sources against the signature, and its `build()` runs with bash. `core`, `xorg` and
`contrib` work the same way, with `core.pub`, `xorg.pub` and `contrib.pub`.

A package the binary repos have wins over a port of the same name: `mag install` takes a port only when nothing has it
built, `mag build` always takes the port. A port brings build-base, pkgconf and bash with it, and the `-dev` package of
every dependency that comes built. The flags go in `/etc/mag/build.conf`, otherwise it is `-O2 -pipe` and one job per
core:

    CFLAGS="-O2 -pipe -march=native"
    MAKEFLAGS="-j4"

What a port installs is a package like any other: `mag files`, `mag remove` and `mag upgrade` work on it.

### 4.7 Void and Exherbo

mag builds Void's templates and Exherbo's exheres too, from their git trees:

    echo 'void https://github.com/void-linux/void-packages' >> /etc/mag/repos
    echo 'exherbo https://gitlab.exherbo.org/exherbo/arbor' >> /etc/mag/repos
    mag update
    mag build tmux

`mag update` gets the whole tree as one tarball, about 9 MB for Void and 2 MB for arbor, and indexes it. Neither tree
is signed: what you get is what GitHub or Exherbo's GitLab sent over https. A Void template has the sha256 of each of
its sources, and mag checks them. An exheres has none, so its sources are as good as the connection they came over.

A Void template runs with the helpers in the tree's `common/`, the way xbps-src runs it: the build style
(`gnu-configure`, `cmake`, `meson` and the others), `vinstall`, `vmove` and the rest, and Void's patches. What Void
splits into subpackages stays in one package here: `mag build libzstd` builds zstd. A `-devel` it needs is the `-dev`
of the binary repos.

An exheres runs on a small exheres-0 of mag's own, with the exlibs of the tree. Options are what Exherbo's profile turns
on, without systemd and pam. Exherbo puts programs in `/usr/x86_64-...-musl/bin`; mag builds them there and moves them
to `/usr` afterwards. Arbor is Exherbo's main tree, about 1000 packages; the others are on the same GitLab and work the
same way.

When two trees have a package, `mag build` takes the newer version. A package the binary repos split differently,
like xz with its `xz-libs`, clashes with what is installed, and mag stops; `-f` writes over it.

### 4.8 pacman repos and the AUR

The glibc Chamesle (1.3) runs on pacman repos, which mag reads natively. Its `/etc/mag/repos`:

    https://chamesle.org/repo/glibc
    pacman https://mirrors.dotsrc.org/artix-linux/repos/system/os
    pacman https://mirrors.dotsrc.org/artix-linux/repos/world/os
    pacman https://mirrors.dotsrc.org/artix-linux/repos/galaxy/os
    pacman https://mirrors.dotsrc.org/artix-linux/repos/lib32/os
    pacman https://geo.mirror.pkgbuild.com/extra/os
    pacman https://geo.mirror.pkgbuild.com/multilib/os
    aur https://aur.archlinux.org

A `pacman` line is the URL above the architecture's directory; the database is named after the last part before `os`
(`system.db`). As in pacman, a package that two repos have comes from the first one, so Artix's OpenRC builds win over
Arch's systemd ones. Any other mirror of the same repos works the same.

Packages are checked against their sha256 in the database and their OpenPGP signature, with the keyrings of
`artix-keyring` and `archlinux-keyring` in `/usr/share/pacman/keyrings` (RSA and ed25519, without the revoked keys),
and any `*.gpg` in `/etc/mag/keys`. A package's `.INSTALL` runs as its scripts, and after every run mag runs the hooks
in `/usr/share/libalpm/hooks` and `/etc/pacman.d/hooks`, the way pacman does: they make the initramfs, the system
users, the linker cache and the other caches. mag decompresses zstd itself.

The `aur` line makes the AUR one more repo. `mag update` gets the metadata of every AUR package (15 MB), and
`mag install` builds what is not in the binary repos:

    mag install spotify

mag installs `base-devel`, `git` and what the PKGBUILD needs to build, gets the snapshot into
`/var/cache/mag/aur/NAME`, and runs makepkg there as nobody; the package it makes is installed like any other. Keys
the PKGBUILD lists in `validpgpkeys` are fetched from keyserver.ubuntu.com for the build. A PKGBUILD is written by
whoever uploaded it and nobody else read it: look at it first (`/var/cache/mag/aur/NAME/PKGBUILD` stays after the build)
if you do not trust the package.


## 5. rifle

### 5.1 What it is

rifle is the coreutils of Chamesle on x86_64 in one C file, `rifle.c`, on `c.h`, a one-file libc. It has no GNU code in it and no
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

The `rifle` package has it built. From the sources:

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


## 6. The base system

### 6.1 init

The init is OpenRC. `/sbin/init` is busybox init, which reads `/etc/inittab`: it runs `openrc sysinit`, `openrc boot`
and `openrc default` in turn, then puts a login on `tty1` to `tty6`. OpenRC starts the services of each runlevel, each
after what it needs, and stops them in order when the machine goes down.

A runlevel is a directory in `/etc/runlevels` with links to the services in `/etc/init.d`. A fresh install has:

| runlevel | services |
|---|---|
| sysinit | `devfs`, `dmesg`, `udev`, `udev-trigger`, `udev-settle` |
| boot | `modules`, `hwclock`, `sysctl`, `hostname`, `bootmisc`, `syslog`, `seedrng`, `swap` |
| default | `udev-postmount`, `dhcpcd` |
| shutdown | `killprocs`, `mount-ro`, `savecache` |

`fsck`, `root` and `localmount` come in because the boot ones need them: the file systems are checked, `/` is remounted
read-write and `/etc/fstab` is mounted. On ZFS, `zfs-import` and `zfs-mount` are in sysinit too.

### 6.2 Services

Every package with a daemon has its service next to it, in a package called after it with `-openrc` on the end. mag
installs that one by itself once OpenRC and the daemon are both there, so `mag install lightdm` brings `lightdm-openrc`
too. Then:

    rc-update add lightdm            start it at every boot
    rc-update del dhcpcd             not at boot any more
    rc-service iwd start
    rc-service iwd stop
    rc-service dhcpcd restart
    rc-status                        what runs, by runlevel
    rc-update                        what starts at boot, and in which runlevel

`rc-update add` puts a service in the default runlevel unless you name another. `service NAME start` works too. The
service files are in `/etc/init.d` and their settings in `/etc/conf.d/NAME`. `openrc-run(8)` has the rest.

Chamesle before base r20 ran dinit, and before r18 Winchester. The upgrade to r20 moves you over by itself: what was
enabled there (`/etc/dinit.d/boot.d`, or `boot-services` of `/etc/init.conf`) is added to the default runlevel. dinit
is still process 1 until the next boot, so reboot that once with `dinit-reboot`.

### 6.3 Shutting down

`reboot`, `halt` and `poweroff` ask init to stop. `openrc shutdown` stops the services, the ones others need last,
sends `TERM` and then `KILL` to what is left, turns swap off and remounts the file systems read-only.

### 6.4 The files in /etc

| file | what it holds |
|------|---------------|
| `passwd`, `shadow`, `group` | accounts, password hashes, groups |
| `shells` | the login shells; `/bin/mksh` is one |
| `hostname` | the host name |
| `init.d/`, `runlevels/` | the services, and the ones started at boot (6.2) |
| `modules` | kernel modules loaded at boot, one a line |
| `fstab` | the file systems (3.5) |
| `profile` | `PATH`, `PAGER`, `umask 022`, and `/etc/profile.d/*.sh` |
| `os-release` | `NAME=Chamesle`, `ID=chamesle` |
| `mag/` | the repos, the keys and the architecture (4.3) |
| `skel/` | the files new homes start from |

The login shell is mksh and `/etc/profile` is read by login shells. For a prompt and aliases make `~/.mkshrc` and set
`ENV=$HOME/.mkshrc` in `/etc/profile`.

### 6.5 Users

    adduser alice
    adduser alice wheel
    adduser alice video
    adduser alice input

`adduser` makes the account, the group and the home, and asks for the password; `passwd alice` changes it.
`deluser alice` takes the account away.

`wheel` may use `doas`, which is in the base with `permit persist :wheel` in `/etc/doas.d/wheel.conf`. `video` opens
`/dev/dri`, the graphics, and `input` the keyboard and mouse under `/dev/input`. There is no logind to hand them out, so
whoever runs X or a Wayland compositor needs both, or Xorg stops with `open /dev/dri/card0: Permission denied` and
`no screens found`. Groups count from the next login.

### 6.6 udev and modules

eudev is the udev. `udevd` gives devices their nodes in `/dev` and loads the modules the hardware needs.

kmod provides `modprobe`, `insmod`, `rmmod`, `lsmod`, `modinfo` and `depmod`. A kernel's modules are in
`/lib/modules/VERSION`. To load one by hand: `modprobe name`. To load one at every boot, put its name on a line of `/etc/modules`. The base loads the input and network drivers of `/usr/lib/modules-load.d/chamesle.conf` too. To keep one from loading, put `blacklist name` in a file in `/etc/modprobe.d/`.

### 6.7 Networking

`dhcpcd` is the DHCP client and is in the base set. It is the `dhcpcd` service, enabled by default, and takes
every interface, so a cable is up at boot. `ip` lists them:

    ip addr
    ip link set eth0 up

A static address:

    ip addr add 192.168.1.10/24 dev eth0
    ip route add default via 192.168.1.1
    echo 'nameserver 192.168.1.1' > /etc/resolv.conf

and `rc-update del dhcpcd`.

### 6.8 Wireless

The card needs its firmware (7.4). Then iwd:

    mag install iwd dbus

and add it, which starts dbus with it:

    rc-update add iwd
    rc-service iwd start

`iwctl` connects, the same as on the ISO (2.3), and remembers
the network. dhcpcd gives it an address.

`wpa_supplicant` works too, for those who know it: `mag install wpa_supplicant`.

### 6.9 Mounting and disks

    mount /dev/sdb1 /mnt/usb
    mount -t vfat -o ro /dev/sdb1 /mnt/usb
    umount /mnt/usb

`mount` and `umount` are busybox's; `lsblk`, `blkid`, `sfdisk` and `cfdisk` are packages of their own, `mkfs.ext4` and
`fsck.ext4` are e2fsprogs', `mkfs.fat` is dosfstools', `zpool` and `zfs` are `zfs`.

On a ZFS root, the boot runs `zfs mount -a` right after `mount -a`, which mounts `rpool/home` and `rpool/var`; the root itself was
mounted by the initramfs.

### 6.10 Kernel settings

The boot loads every `/etc/sysctl.d/*.conf` and `/etc/sysctl.conf` at boot. The base ships
`/etc/sysctl.d/10-chamesle.conf`: kernel addresses and `dmesg` are for root only (`doas dmesg`), a process may
`ptrace` only its own children, users get no BPF, links and files in sticky directories like `/tmp` are protected,
setuid programs leave no core dumps, and the network takes no redirects or source routes and filters spoofed
addresses. To change one, put it in a file of your own that sorts later, `/etc/sysctl.d/90-local.conf`:

    kernel.dmesg_restrict = 0

`sysctl -a` lists them all, `sysctl -w name=value` changes one until the next boot.


## 7. The kernel and firmware

### 7.1 The kernel package

Nobody builds a kernel in Chamesle. `linux-lts` is the newest Linux LTS kernel with a generic configuration that runs on
most machines, and it installs

    /boot/vmlinuz-lts
    /boot/config-VERSION
    /boot/System.map-VERSION
    /lib/modules/VERSION/

`linux-virt` is a smaller one for virtual machines. Give it to chamesle-bootstrap with `-k`, and name its files in
`limine.conf` (`vmlinuz-virt`, `initramfs-virt`).

### 7.2 Updating

    mag update
    mag upgrade

A new `linux-lts` replaces `vmlinuz-lts` and makes `initramfs-lts` again, so `limine.conf` needs no change. Reboot to
run it; `uname -r` says what runs. Keep the ISO at hand in case a new kernel does not boot.

### 7.3 Modules

Modules are files in `/lib/modules/VERSION`. `lsmod` shows what is loaded, `modprobe name` loads a module with what
it needs, `modinfo name` describes it. udev loads the ones the hardware asks for. Modules belong to one kernel build:
after an upgrade of the kernel, reboot before loading any.

### 7.4 Firmware

The firmware is split by vendor, so a machine takes only what it uses:

| package | for |
|---------|-----|
| `linux-firmware-intel` | Intel wireless (iwlwifi), Bluetooth and the rest of the intel folder |
| `linux-firmware-i915` | Intel graphics |
| `linux-firmware-amdgpu`, `linux-firmware-radeon` | AMD graphics |
| `linux-firmware-rtlwifi`, `linux-firmware-rtw88`, `linux-firmware-rtw89`, `linux-firmware-rtl_nic` | Realtek wireless and ethernet |
| `linux-firmware-ath10k`, `linux-firmware-ath11k`, `linux-firmware-ath9k_htc` | Qualcomm Atheros wireless |
| `linux-firmware-brcm` | Broadcom wireless |
| `linux-firmware` | all of them, over 500 MB |
| `linux-firmware-none` | none |

`mag search linux-firmware` lists them. If `dmesg` says a firmware file failed to load, `mag owns` is no help yet, since
it is not installed; the name of the file says the vendor.

### 7.5 The initramfs

The kernel package makes `/boot/initramfs-lts` with `mkinitfs` whenever the kernel is installed or updated. What goes into
it is set in `/etc/mkinitfs/mkinitfs.conf`:

    features="ata base cdrom ext4 keymap kms mmc nvme raid scsi usb virtio"

For a root on ZFS add `zfs` to the list, install `zfs` and `zfs-lts`, and make it again:

    mag install zfs zfs-lts
    mkinitfs $(ls /lib/modules)

The initramfs reads `root=`, `rootfstype=` and `modules=` from the command line, mounts the root and starts `/sbin/init`.
If it cannot, it says why and gives a shell.

The live ISO has its own initramfs, made by `iso/mkinitramfs`, which mounts the squashfs (chapter 8).


## 8. The live ISO

### 8.1 What it is

The ISO is a live system to work from. It boots on BIOS and UEFI machines with limine, from a disc or a stick, logs in as
root on every tty and has

* mag, the keys and the repos, and `chamesle-bootstrap`, `chamesle-disk`, `chamesle-boot`, `arch-chroot`
* the disk tools: `cfdisk`, `sfdisk`, `lsblk`, `blkid`, `mkfs.ext4`, `mkfs.fat`, `zpool`, `zfs`, `limine`
* the network: `dhcpcd`, `iwd` with `iwctl`, `wpa_supplicant`, `curl`
* the Intel wireless firmware, vim, less, and this handbook in `/usr/share/doc/chamesle/handbook.md`

It is where you do chapter 3. `chamesle.iso` is for x86_64, `chamesle-x86.iso` for 32-bit machines (BIOS only).

### 8.2 How it boots

`iso/init` looks through `/dev/sr*`, `/dev/sd*`, `/dev/nvme*n*p*`, `/dev/vd*` and `/dev/mmcblk*` until it finds one that
mounts and has `LiveOS/rootfs.sfs`. It mounts that squashfs read-only, puts a tmpfs overlay over it, moves the medium and
the squashfs to `/run/live/medium` and `/run/live/rootfs`, and runs `switch_root` into the result. Whatever you change
in the live system is gone at shutdown.

### 8.3 Making it

    iso/mkiso -o chamesle.iso
    iso/mkiso -a x86 -o chamesle-x86.iso

as root, with mag in PATH, and `xorriso`, `mksquashfs`, `zstd` and `bsdcpio` on the host. mkiso installs
`chamesle-base`, the kernel and what `iso/profile/packages` names into `work/rootfs` with mag, copies
`iso/profile/overlay` over it, makes the initramfs and the squashfs and puts them on the ISO with limine.

### 8.4 Trying it in qemu

BIOS:

    qemu-system-x86_64 -m 1G -cdrom chamesle.iso -boot d

UEFI, with the firmware of your qemu (`edk2-x86_64-code.fd`; the path differs between systems):

    qemu-system-x86_64 -m 1G -bios /usr/share/qemu/edk2-x86_64-code.fd -cdrom chamesle.iso

Add `-enable-kvm` for speed. To go through all of chapter 3 in a virtual machine, give it a disk:

    qemu-img create -f qcow2 disk.qcow2 8G
    qemu-system-x86_64 -m 1G -enable-kvm -cdrom chamesle.iso -drive file=disk.qcow2 -boot d -nic user

A machine like an old Pentium 4 with 256 MB: `-cpu pentium3,+sse2 -m 256` and the x86 ISO.

To write the ISO to a stick: `dd if=chamesle.iso of=/dev/sdX bs=4M conv=fsync`.


## 9. Maintaining

### 9.1 Updating

    mag update
    mag -n upgrade
    mag upgrade

The first gets the indexes, the second says what would change, the third does it.

### 9.2 Cleaning up

    mag autoremove                 dependencies nothing needs any more
    rm -rf /var/cache/mag/pkg      downloaded packages; they are fetched again when needed

### 9.3 Configuration files

A changed file under `/etc` is never written over. When a package brings a new one, it lands next to yours as
`NAME.new`. Look for them after an upgrade and merge by hand:

    find /etc -name '*.new'

### 9.4 Failures you will see

| what you see | why, and what to do |
|--------------|---------------------|
| `no package NAME` | not in any repo; `mag search`, and `mag update` |
| a signature or hash that does not match | the download or the index is not what the repo signed; `mag update` and try again, check `/etc/mag/keys` |
| `NAME wants FILE, which OTHER has` | two packages want the same file; `-f` writes over it if you are sure |
| "root device not found" at boot | the initramfs cannot see the disk or the file system: check `root=` and `modules=` in `limine.conf` |
| the machine boots to a limine prompt | `limine.conf` is not found, or its `path:` does not name a file in `/boot`; check with `ls /boot` |
| a BIOS machine does not boot | `limine bios-install /dev/sda` was not run, or `limine-bios.sys` is not in `/boot` |
| a UEFI machine does not boot | `EFI/BOOT/BOOTX64.EFI` is not on the EFI partition, or the partition is not of type EFI System |
| no wireless interface | the firmware is missing (7.4); `dmesg` names the file |
| no devices in `/dev` | udev did not start; `rc-service udev status` |


## 10. X and a window manager

### 10.1 What to install

    mag install xorg-server xinit xf86-input-libinput mesa-dri-gallium font-dejavu windowmaker st

| package | for |
|---------|-----|
| `xorg-server` | X itself, with the `modesetting` driver, which drives Intel, AMD, NVIDIA and virtual graphics through the kernel |
| `xinit` | `startx` |
| `xf86-input-libinput` | keyboard, mouse and touchpad |
| `mesa-dri-gallium` | OpenGL |
| `font-dejavu` | a font; X programs show empty boxes without one |
| `windowmaker` | the window manager, and `WPrefs` for its settings |
| `st` | a terminal; `xterm` is another |

Any other window manager or desktop in the repos goes the same way; only the line in `~/.xinitrc` changes.

### 10.2 Firmware for the graphics

The kernel's graphics drivers load firmware for most cards. Install the one for yours and reboot:

| graphics | firmware | Vulkan |
|----------|----------|--------|
| Intel, up to 14th generation | `linux-firmware-i915` | `mesa-vulkan-intel` |
| Intel Arc, Lunar Lake and newer | `linux-firmware-xe` | `mesa-vulkan-intel` |
| AMD | `linux-firmware-amdgpu`, `linux-firmware-radeon` for older cards | `mesa-vulkan-ati` |
| NVIDIA | `linux-firmware-nvidia` | `mesa-vulkan-nouveau` |

NVIDIA's own driver is built for glibc and is not in the repos. The open one, nouveau, runs every card; from the GTX 16
and RTX 20 on, the card's own firmware sets the clocks and it is fast, with Vulkan from NVK in
`mesa-vulkan-nouveau`. On older NVIDIA cards it stays slow. `lspci` says which graphics a machine has.

### 10.3 Groups

There is no logind to hand the screen and the input devices to whoever logs in. X opens them as the user, so the user
needs the `video` and `input` groups (6.5):

    adduser alice video
    adduser alice input

Log out and in again after.

### 10.4 startx

`startx` runs `~/.xinitrc`, as the user, from a text login:

    echo 'exec wmaker' > ~/.xinitrc
    startx

X runs until `wmaker` ends: Exit in its menu. To start X at every login on tty1, at the end of `~/.profile`:

    [ "$(tty)" = /dev/tty1 ] && exec startx

Lines in `.xinitrc` before the `exec` run first, which is the place for the keyboard layout and the screen size:

    setxkbmap fr
    xrandr --output eDP-1 --mode 1920x1080
    exec wmaker

`mag install setxkbmap xrandr` for those; `xrandr` alone lists the outputs and their modes.

### 10.5 Window Maker

The first start makes `~/GNUstep` with Window Maker's settings. The right button on the desktop opens the menu, with
programs, workspaces and Exit. The dock is in the top right corner and the clip, which switches workspaces, in the top
left. Drag a program's icon to the dock to keep it there. `WPrefs` changes the rest: focus, themes, keys. The menu is
`~/GNUstep/Defaults/WMRootMenu`.

### 10.6 Firefox

    mag install firefox

`firefox-esr` is the long-term one. Firefox and many other programs want a D-Bus session; with `dbus` and `dbus-x11`
installed and `dbus` enabled (6.2), start the window manager inside one:

    exec dbus-launch --exit-with-session wmaker

### 10.7 When it fails

X writes `~/.local/share/xorg/Xorg.0.log`; `grep EE` in it shows the errors.

| what you see | why, and what to do |
|--------------|---------------------|
| `open /dev/dri/card0: Permission denied`, then `no screens found` | the user is not in `video` (10.3) |
| `no screens found` with no permission error | no graphics driver came up; check `ls /dev/dri`, and the firmware (10.2) |
| no keyboard or mouse in X | `xf86-input-libinput` is not installed, or the user is not in `input` |
| X starts and ends at once | `~/.xinitrc` is missing, or names a program that is not installed |
| boxes in place of letters | no font, `font-dejavu` |


## 11. File reference

### 11.1 On an installed system

| path | what |
|------|------|
| `/sbin/init`, `/etc/inittab` | busybox init, which runs OpenRC |
| `/etc/init.d/`, `/etc/runlevels/` | the services, and the ones started at boot |
| `/usr/lib/chamesle/` | the boot scripts the services run |
| `/etc/hostname`, `/etc/modules` | host name, modules loaded at boot |
| `/etc/profile` | `PATH`, `umask` |
| `/etc/passwd`, `/etc/shadow`, `/etc/group`, `/etc/shells` | accounts, passwords, groups, login shells |
| `/etc/fstab` | file systems |
| `/etc/sysctl.d/` | kernel settings loaded at boot (6.10) |
| `/etc/os-release` | `NAME=Chamesle`, `ID=chamesle` |
| `/etc/mag/` | `repos`, `keys/`, `arch`, `build.conf` |
| `/etc/mkinitfs/mkinitfs.conf` | what goes into the initramfs |
| `/boot/limine.conf` | the boot entries |
| `/boot/limine-bios.sys` | limine's BIOS stage |
| `/boot/EFI/BOOT/BOOTX64.EFI` | limine for UEFI |
| `/boot/vmlinuz-lts`, `initramfs-lts` | the kernel and its initramfs |
| `/lib/modules/V/` | its modules |
| `/lib/firmware/` | firmware |
| `/var/lib/mag/` | what is installed, and its files |
| `/var/cache/mag/` | indexes, downloaded packages and port trees |
| `/usr/share/limine/` | limine's boot files, for installing it |
| `/usr/share/doc/chamesle/handbook.md` | this book |

### 11.2 In the sources

| path | what |
|------|------|
| `system/tools/chamesle-bootstrap` | puts the base into a root with mag |
| `system/tools/chamesle-boot` | limine.conf and limine for the system in a directory |
| `system/tools/chamesle-disk` | cfdisk, vfat boot partition, ZFS root, mounted on `/mnt` |
| `system/tools/mkapk`, `mkrepo`, `mkpkgs` | packages, signed indexes, Chamesle's own repo |
| `system/files/` | the files in `/etc` and the tools, in `chamesle-base` |
| `system/pkg/chamesle-base/` | its scripts, `repos`, `os-release`, `issue` |
| `system/keys/` | the public keys the repos are signed with |
| `system/iso/mkiso`, `mkinitramfs`, `init` | the live ISO, its initramfs and the first process in it |
| `system/iso/profile/` | `packages`, `modules`, `limine.conf` and the `overlay/` of the live root |
| `system/handbook/handbook.md` | this book |
| `mag/mag.c`, `mag/c.h`, `mag/build.sh` | the package manager |
| `rifle/rifle.c`, `rifle/c.h`, `rifle/build.sh` | the coreutils |
| `rifle/tests/run.sh`, `rifle/tests/cases` | the comparison tests |

### 11.3 Commands in short

    chamesle-bootstrap [-a ARCH] [-n HOSTNAME] [-k KERNEL] [-f FIRMWARE] TARGET [PACKAGE]...
    arch-chroot DIR [COMMAND...]
    chamesle-disk DISK
    chamesle-boot [DIR]
    mag [-nf] update|install|build|remove|upgrade|autoremove|list|info|search|files|owns|deps|rdeps|fetch
    rifle --install DIR | --list
    limine bios-install DEVICE
