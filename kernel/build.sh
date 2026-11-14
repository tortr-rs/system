#!/bin/sh
# builds linux 6.18 on this machine and packs the result in one tarball you can hand over.
#   ./build.sh            the running kernel's config as the start (safe, big)
#   ./build.sh small      only what this machine uses right now (small, make sure everything you own is plugged in)
# needs: a C compiler, make, flex, bison, bc, perl, openssl headers or libelf are NOT needed (we switch those parts off), curl, tar, xz
set -e
ver=6.18.63
sum=81764a545072d160748beff4d9de2e7d95aa9f16e8261110288f067a2cc61d71
jobs=$(nproc 2>/dev/null || echo 4)
work=${WORK:-$HOME/chamesle-kernel}
mkdir -p "$work" && cd "$work"
if [ ! -f linux-$ver.tar.xz ]; then
	curl -fL -o linux-$ver.tar.xz https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-$ver.tar.xz
fi
[ "$(sha256sum linux-$ver.tar.xz | cut -d' ' -f1)" = $sum ] || { echo "the tarball does not match its checksum, delete it and run again"; exit 1; }
[ -d linux-$ver ] || tar -xf linux-$ver.tar.xz
cd linux-$ver
if [ -r /proc/config.gz ]; then zcat /proc/config.gz > .config
elif [ -r /boot/config-$(uname -r) ]; then cp /boot/config-$(uname -r) .config
else make defconfig; fi
if [ "$1" = small ]; then lsmod > "$work/lsmod.txt"; make LSMOD="$work/lsmod.txt" localmodconfig; fi
scripts/config -d MODULE_SIG -d MODULE_SIG_ALL -d SYSTEM_TRUSTED_KEYRING -d SYSTEM_REVOCATION_KEYS -d DEBUG_INFO_BTF -d DEBUG_INFO_BTF_MODULES \
	-d UNWINDER_ORC -e UNWINDER_FRAME_POINTER -d WERROR \
	-e DEVTMPFS -e DEVTMPFS_MOUNT -e EFI_STUB -e BLK_DEV_INITRD -e FW_LOADER -e FW_LOADER_COMPRESS -e FW_LOADER_COMPRESS_ZSTD \
	-e EXT4_FS -e VFAT_FS -e ISO9660_FS -e SQUASHFS -e SQUASHFS_ZSTD -e OVERLAY_FS -e TMPFS -e PROC_FS -e SYSFS \
	--set-str LOCALVERSION "-chamesle" --set-str SYSTEM_TRUSTED_KEYS "" --set-str SYSTEM_REVOCATION_KEYS ""
make olddefconfig
make -j"$jobs" bzImage modules
rm -rf "$work/out" && mkdir -p "$work/out/boot"
cp arch/x86/boot/bzImage "$work/out/boot/vmlinuz-$ver-chamesle"
cp System.map "$work/out/boot/System.map-$ver-chamesle"
cp .config "$work/out/boot/config-$ver-chamesle"
make INSTALL_MOD_PATH="$work/out" INSTALL_MOD_STRIP=1 modules_install
rm -f "$work"/out/lib/modules/*/build
cd "$work"
tar -C out -cf - . | xz -T0 > chamesle-kernel-$ver.tar.xz
sha256sum chamesle-kernel-$ver.tar.xz | tee chamesle-kernel-$ver.sha256
echo "done: $work/chamesle-kernel-$ver.tar.xz"
