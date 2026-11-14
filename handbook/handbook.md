# The Chamesle handbook

Chamesle is a Linux system you build from source and keep small. The kernel is the only thing in it that comes
from outside the Unix family: the C library is musl, the shell is ksh, the packages come from NetBSD's pkgsrc
and the package manager is `mag`.

## What is in it

| part | what it is |
|---|---|
| kernel | Linux 6.18 LTS, the Alpine linux-lts build (chapter 3) |
| musl | the C library |
| rifle | the coreutils, one C file |
| mag | the package manager, reads pkgsrc packages as they are |
| init | a shell script, `/sbin/init` (files/sbin/init), runs under mksh |
| mksh | the shell: login shell and `/bin/sh` (the MirBSD Korn shell) |
| vim | the editor, installed on the ISO |
| limine | the boot loader |

## 1. Getting a root file system

`tools/chamesle-bootstrap` is to Chamesle what debootstrap is to Debian. It makes the directories and the files in
`/etc`, then builds and installs the base packages into the directory you give it with `mag`:

    MAG_REPO=$HOME/src/mag/repo:/usr/pkgsrc chamesle-bootstrap /mnt/root

Building everything from source takes a while (LLVM is the long one). Packages are not built twice: the sources
are kept in `var/cache/mag` inside the target.

`-s "shells/mksh editors/vim"` installs your own list, `-n name` sets the host name.

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

## 3. The kernel

Nobody here builds a kernel. `sys-kernel/linux` is the kernel and its modules from Alpine's linux-lts package
(6.18 LTS, built with the config of a distribution kernel, so it runs on nearly any machine). mag fetches it from
Alpine's mirror, checks the checksum and puts `vmlinuz`, `config`, `System.map` and the modules into `/boot` and
`/lib/modules`. Alpine drops a package from its mirror when a newer one comes out, so a new kernel is a new `version`
and `sha256` in `repo/sys-kernel/linux`. The firmware is `sys-kernel/linux-firmware`.

## 4. The ISO

The ISO is a live system to install from, nothing more. There is no installer: Chamesle is put on a disk by hand
(chapter 5). It boots on BIOS and UEFI machines with limine, from a CD or a stick, and has mksh, vim, mag,
`chamesle-bootstrap`, the disk tools (sfdisk, mkfs.ext4, mkfs.fat) and this handbook in `/usr/share/doc/chamesle/`.

    iso/mkiso -r $HOME/src/mag/repo:/usr/pkgsrc

What it does, in order: `chamesle-bootstrap` builds a root from `iso/profile/packages`, the files of
`iso/profile/overlay`, the handbook, `mag` and `chamesle-bootstrap` are copied over it, `mkinitramfs`
makes the initrd (a few static tools, the modules in `iso/profile/modules` with what they depend on, `iso/init`),
the root becomes a zstd squashfs, and `xorriso` writes the ISO with limine's BIOS and UEFI boot images.
`-R dir` uses a root you already have instead of building one (it is copied, not changed).

At boot `init` looks for the medium that has `LiveOS/rootfs.sfs`, mounts it read-only, puts a tmpfs overlay over it,
and switches into the result. The medium and the squashfs stay mounted under `/run/live/`.

Try an ISO without a machine:

    qemu-system-x86_64 -cpu max -m 1G -cdrom chamesle.iso -boot d
    qemu-system-x86_64 -cpu max -m 1G -bios /usr/share/qemu/edk2-x86_64-code.fd -cdrom chamesle.iso   # uefi

mkiso needs `mksquashfs` (filesystems/squashfs), `xorriso` (sysutils/libisoburn), `zstd`, `bsdcpio`, `limine` and `mag`
on the machine that builds. `LIMINE` says where limine's files are (default /usr/share/limine), `MAG` where mag is.

## 5. Installing by hand

Boot the ISO, log in as root, bring the network up (`dhcpcd`) and do this. `sda` is the disk, change it.

1. Partition: a GPT with a 1M BIOS boot partition, a 512M EFI partition and the rest for `/`.

        sfdisk /dev/sda <<P
        label: gpt
        size=1M, type=21686148-6449-6E6F-744E-656564454649
        size=512M, type=U
        type=L
        P
        mkfs.fat -F32 /dev/sda2
        mkfs.ext4 /dev/sda3

2. Mount them. The EFI partition is `/boot`.

        mount /dev/sda3 /mnt
        mkdir /mnt/boot
        mount /dev/sda2 /mnt/boot

3. Get a pkgsrc tree and mag's own recipes somewhere on the live system and point mag at them,
   `export MAG_REPO=/path/to/repo:/path/to/pkgsrc`.

4. Make the root: `chamesle-bootstrap -n yourhostname /mnt`. It builds the base set from source, kernel included,
   and takes a while. Add what you want after that with `MAG_ROOT=/mnt mag install ...`.

5. Set the password, fstab and the boot entry by hand. `blkid` gives the UUIDs.

        echo 'root:x:0:0:root:/root:/usr/bin/mksh' > /mnt/etc/passwd   # then put a hash in the second field
        vim /mnt/etc/fstab
        cp /mnt/usr/share/limine/BOOTX64.EFI /mnt/boot/EFI/BOOT/
        vim /mnt/boot/limine.conf

   limine.conf:

        timeout: 3
        /Chamesle
            protocol: linux
            path: boot():/vmlinuz-6.18.63-0-lts
            cmdline: root=UUID=THE-ROOT-UUID rw

6. Install limine for BIOS and unmount: `limine bios-install /dev/sda`, `umount -R /mnt`, reboot.

An initramfs is not needed: the Alpine kernel has the common storage and ext4 drivers as modules, so for a root on
anything but a plain disk, build your own and put it in limine.conf as `module_path`. (This chapter has not been run
start to finish on real hardware yet.)

## 6. Files

    /etc/profile       PATH, EDITOR=vim
    /etc/ksh.kshrc     prompt and aliases of every ksh
    /etc/fstab, hostname, passwd, group, shells
    /var/lib/mag       what is installed, per package
    /var/cache/mag     downloaded sources
