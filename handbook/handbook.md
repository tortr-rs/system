# The Chamesle Handbook

1. About Chamesle
2. Preparing
3. Installing by hand
4. mag
5. rifle
6. The base system
7. The kernel and firmware
8. The live ISO
9. Maintaining
10. File reference


## 1. About Chamesle

### 1.1 What it is

Chamesle is a small Linux distribution on musl that you put on a disk yourself, from the ISO. There is no installer and
nothing is compiled: `chamesle-bootstrap` puts the base into an empty root with the package manager, and you write the
fstab, the password and the boot entry by hand. This handbook goes through every step.

The parts:

| part   | what it is |
|--------|------------|
| kernel | a prebuilt Linux 6.18 LTS kernel with its modules |
| musl   | the C library |
| mag    | the package manager, binary packages only, in one C file |
| rifle  | the coreutils, all in one C file; `cat`, `ls`, `cp` and the rest are links to one program |
| mksh   | the login shell; `/bin/sh` is busybox's ash |
| init   | Winchester, `/sbin/init`, a shell script that runs under mksh, in the style of FreeBSD's: `/etc/rc`, `/etc/init.conf`, services |
| limine | the boot loader, BIOS and UEFI |

Chamesle is made to be the most UNIX distribution possible, and to run on almost anything: the same base goes on a new
laptop and on a Pentium 4 with 256 MB of memory. It is a system for the tty first. Anything else is a `mag install` away.

### 1.2 Where the packages come from

mag reads two kinds of repository, both signed:

* Chamesle's own, at `https://chamesle.org/repo`: `chamesle-base` (Winchester, `/etc/rc`, the services, the tools of this
  book and the keys), `mag` and `rifle`
* a large musl repository with everything else: the kernel, the firmware, the libraries, editors, compilers, X, about
  28,000 packages for x86_64

Both are in `/etc/mag/repos`. A package is checked against the keys in `/etc/mag/keys` before anything of it is unpacked.

### 1.3 The layout of the system

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

### 1.4 Where the sources are

| directory | what is in it |
|-----------|---------------|
| `system/` | `tools/` (`chamesle-bootstrap`, `chamesle-chroot`, `chamesle-disk`, and `mkapk`, `mkrepo`, `mkpkgs` for the repo), `files/` (init, rc and the services), `pkg/`, `keys/`, `iso/`, this handbook |
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


## 3. Installing by hand

Follow the BIOS or the UEFI variant where they differ. The disk here is `/dev/sda`; change it to yours. Everything below
is run as root on the live system, and it erases the disk.

There are two ways through 3.1 and 3.2: `chamesle-disk` does the partitioning and the file systems and leaves the
root on ZFS, or you do both yourself with the root on ext4. From 3.3 on the steps are the same, and they are yours:
`chamesle-disk` is only a helper.

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

What `chamesle-base` brings: Winchester and the files of chapter 6, mag, rifle, mksh, busybox for the tools rifle does not
have, `agetty`, eudev, kmod, dhcpcd, e2fsprogs and curl.

### 3.4 Working inside the new root

    chamesle-chroot /mnt
    chamesle-chroot /mnt passwd root

It mounts `proc`, `sys`, `dev`, `dev/pts` and a tmpfs on `run` under the directory, copies `/etc/resolv.conf` into it, runs
`chroot` with an empty environment (`HOME=/root`, `TERM`, `PATH`) and takes the mounts away again when the command ends.
Without a command it starts `/bin/mksh -l`. Inside, `mag install name` works as on the finished system.

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

The host name is in `/mnt/etc/init.conf`, from `-n`. Set the root password:

    chamesle-chroot /mnt passwd root

The hash goes into `/etc/shadow`. The login shell of root is mksh.

### 3.7 The boot entry

    ls /mnt/boot
    System.map-6.18.64-0-lts  config-6.18.64-0-lts  initramfs-lts  vmlinuz-lts

The names stay the same when the kernel is updated, so `limine.conf` is written once. `/mnt/boot/limine.conf`, with
the UUID of the root partition:

    timeout: 3

    /Chamesle
        protocol: linux
        path: boot():/vmlinuz-lts
        module_path: boot():/initramfs-lts
        cmdline: root=UUID=ROOT-UUID modules=sd-mod,usb-storage,ext4 rootfstype=ext4 quiet

`boot()` is the partition `limine.conf` is on, which is `/boot`. The initramfs finds the root, loads the modules on the
command line and starts `/sbin/init`. Take `quiet` out to see the kernel's messages. For a serial console add
`console=ttyS0,115200`.

A root on ZFS names the dataset; the initramfs needs the zfs module, which is section 7.5:

        cmdline: root=ZFS=rpool/root rootfstype=zfs quiet

Install limine. `limine` is a package; install it into the new root, or use the one of the live system:

    chamesle-chroot /mnt mag install limine

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

### 3.8 First boot

    umount -R /mnt
    zpool export rpool
    reboot

Leave out `zpool export` if the root is not on ZFS.

Take out the installation medium. limine shows the entry for three seconds and boots the kernel. `init` runs `/etc/rc`, which mounts the
file systems and starts the services of `init.conf`, and puts a login on the ttys. Log in as root. `dhcpcd` brings up a
cable at boot; for wireless see section 6.8.

### 3.9 What to install next

    mag install vim htop tmux
    mag search irc

Chapter 4 has the rest.

### 3.10 32-bit machines

On a 32-bit PC (Pentium 4, Athlon XP and the like) boot the ISO on another machine, or install from any Linux there
(2.2), and give the architecture:

    chamesle-bootstrap -a x86 /mnt

The x86 repository has the same packages, built for i686 with SSE2. `-a x86` is written to `/mnt/etc/mag/arch`, and mag
keeps to it from then on. `rifle` is only built for x86_64, so on x86 busybox gives the coreutils. limine boots 32-bit
BIOS machines as well; the entry is the same.


## 4. mag

mag is the package manager. It installs binary packages from the repositories in `/etc/mag/repos`, checks every index
and every package against `/etc/mag/keys`, and keeps what it installed in `/var/lib/mag`. It is one C file and runs
nothing but the download command.

### 4.1 The commands

    mag update                 get the index of every repo
    mag install PKG...         install, with what they need
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
    https://dl-cdn.alpinelinux.org/alpine/v3.24/main
    https://dl-cdn.alpinelinux.org/alpine/v3.24/community

Each line is the URL above the directory of the architecture: mag adds `/x86_64/APKINDEX.tar.gz`. A repository you
add needs its key in `/etc/mag/keys`. `mag update` after any change.

### 4.5 Making a package

`tools/mkapk` packs a directory, signs it and leaves its index entry; `tools/mkrepo` signs the index of a directory of
them:

    mkapk -k KEY -n hello -v 1.0 -a x86_64 -d "says hello" -D "musl" -o repo/x86_64 ./root
    mkrepo repo/x86_64 KEY

Put the public half of KEY in `/etc/mag/keys` and the repo's URL in `/etc/mag/repos`. `tools/mkpkgs` is how Chamesle's
own repo is made.


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

The init is called Winchester. `/sbin/init` is a mksh script, and it works the way FreeBSD's init does: the kernel starts it as process 1, it runs
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
    boot-services = {udev,modules,network}

    modules = {}
    ttys = {tty1,tty2,tty3,tty4,tty5,tty6,ttyS0}
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
`start`, `stop`, `restart` or `status`. The base set has `udev` (starts `udevd`, replays the devices and waits
for them), `modules`, `network` (`dhcpcd`), and `dbus`, `iwd` and `NetworkManager` for when those packages are installed. A name in `boot-services` without a script is skipped with one line
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
| `passwd`, `shadow`, `group` | accounts, password hashes, groups |
| `shells` | the login shells; `/bin/mksh` is one |
| `init.conf` | host name, boot services, modules, ttys (6.2) |
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

`adduser` makes the account, the group and the home, and asks for the password; `passwd alice` changes it.
`deluser alice` takes the account away. For `doas` or `sudo`, `mag install` them and give `wheel` the right in their file.

### 6.6 udev and modules

eudev is the udev. `udevd` gives devices their nodes in `/dev` and loads the modules the hardware needs.

kmod provides `modprobe`, `insmod`, `rmmod`, `lsmod`, `modinfo` and `depmod`. A kernel's modules are in
`/lib/modules/VERSION`. To load one by hand: `modprobe name`. To load one at every boot, put its name in `modules` of `/etc/init.conf`. To keep one from loading, put `blacklist name` in a file in `/etc/modprobe.d/`.

### 6.7 Networking

`dhcpcd` is the DHCP client and is in the base set. It is the `network` service, in `boot-services` by default, and takes
every interface, so a cable is up at boot. `ip` lists them:

    ip addr
    ip link set eth0 up

A static address:

    ip addr add 192.168.1.10/24 dev eth0
    ip route add default via 192.168.1.1
    echo 'nameserver 192.168.1.1' > /etc/resolv.conf

and take `network` out of `boot-services`.

### 6.8 Wireless

The card needs its firmware (7.4). Then iwd:

    mag install iwd dbus

and put `dbus` and `iwd` in `boot-services` before `network`:

    boot-services = {udev,modules,dbus,iwd,network}

`service dbus start`, `service iwd start` to have them now. `iwctl` connects, the same as on the ISO (2.3), and remembers
the network. dhcpcd gives it an address.

`wpa_supplicant` works too, for those who know it: `mag install wpa_supplicant`.

### 6.9 Mounting and disks

    mount /dev/sdb1 /mnt/usb
    mount -t vfat -o ro /dev/sdb1 /mnt/usb
    umount /mnt/usb

`mount` and `umount` are busybox's; `lsblk`, `blkid`, `sfdisk` and `cfdisk` are packages of their own, `mkfs.ext4` and
`fsck.ext4` are e2fsprogs', `mkfs.fat` is dosfstools', `zpool` and `zfs` are `zfs`.

On a ZFS root, `/etc/rc` runs `zfs mount -a` right after `mount -a`, which mounts `rpool/home` and `rpool/var`; the root itself was
mounted by the initramfs.


## 7. The kernel and firmware

### 7.1 The kernel package

Nobody builds a kernel in Chamesle. `linux-lts` is a Linux 6.18 LTS kernel with a generic configuration that runs on
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

* mag, the keys and the repos, and `chamesle-bootstrap`, `chamesle-chroot`, `chamesle-disk`
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
| no devices in `/dev` | udev did not start; check `udev` is in `boot-services` |


## 10. File reference

### 10.1 On an installed system

| path | what |
|------|------|
| `/sbin/init`, `/etc/rc`, `/etc/rc.shutdown` | init, the boot script, the shutdown script, all run by mksh |
| `/etc/init.conf` | host name, boot services, modules, ttys |
| `/etc/rc.d/`, `/usr/local/etc/rc.d/` | the service scripts |
| `/etc/profile` | `PATH`, `umask` |
| `/etc/passwd`, `/etc/shadow`, `/etc/group`, `/etc/shells` | accounts, passwords, groups, login shells |
| `/etc/fstab` | file systems |
| `/etc/os-release` | `NAME=Chamesle`, `ID=chamesle` |
| `/etc/mag/` | `repos`, `keys/`, `arch` |
| `/etc/mkinitfs/mkinitfs.conf` | what goes into the initramfs |
| `/boot/limine.conf` | the boot entries |
| `/boot/limine-bios.sys` | limine's BIOS stage |
| `/boot/EFI/BOOT/BOOTX64.EFI` | limine for UEFI |
| `/boot/vmlinuz-lts`, `initramfs-lts` | the kernel and its initramfs |
| `/lib/modules/V/` | its modules |
| `/lib/firmware/` | firmware |
| `/var/lib/mag/` | what is installed, and its files |
| `/var/cache/mag/` | indexes and downloaded packages |
| `/usr/share/limine/` | limine's boot files, for installing it |
| `/usr/share/doc/chamesle/handbook.md` | this book |

### 10.2 In the sources

| path | what |
|------|------|
| `system/tools/chamesle-bootstrap` | puts the base into a root with mag |
| `system/tools/chamesle-chroot` | chroot with the pseudo file systems mounted |
| `system/tools/chamesle-disk` | cfdisk, vfat boot partition, ZFS root, mounted on `/mnt` |
| `system/tools/mkapk`, `mkrepo`, `mkpkgs` | packages, signed indexes, Chamesle's own repo |
| `system/files/` | init, rc, `service`, `init.conf` and the service scripts, in `chamesle-base` |
| `system/pkg/chamesle-base/` | its scripts, `repos`, `os-release`, `issue` |
| `system/keys/` | the public keys the repos are signed with |
| `system/iso/mkiso`, `mkinitramfs`, `init` | the live ISO, its initramfs and the first process in it |
| `system/iso/profile/` | `packages`, `modules`, `limine.conf` and the `overlay/` of the live root |
| `system/handbook/handbook.md` | this book |
| `mag/mag.c`, `mag/c.h`, `mag/build.sh` | the package manager |
| `rifle/rifle.c`, `rifle/c.h`, `rifle/build.sh` | the coreutils |
| `rifle/tests/run.sh`, `rifle/tests/cases` | the comparison tests |

### 10.3 Commands in short

    chamesle-bootstrap [-a ARCH] [-n HOSTNAME] [-k KERNEL] [-f FIRMWARE] TARGET [PACKAGE]...
    chamesle-chroot DIR [COMMAND...]
    chamesle-disk DISK
    mag [-nf] update|install|remove|upgrade|autoremove|list|info|search|files|owns|deps|rdeps|fetch
    rifle --install DIR | --list
    limine bios-install DEVICE
