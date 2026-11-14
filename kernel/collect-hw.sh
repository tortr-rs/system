#!/bin/sh
# run this on the MSI, from any distro that boots there. it writes hw.txt: what the machine has, so the kernel can be
# configured for it. nothing private in it (no serials, no ip addresses)
out=${1:-hw.txt}
{
	echo "## cpu"; grep -m1 'model name' /proc/cpuinfo; grep -c '^processor' /proc/cpuinfo
	echo "## dmi"; for f in sys_vendor product_name board_name bios_version; do printf '%s: ' $f; cat /sys/class/dmi/id/$f 2>/dev/null; done
	echo "## memory"; grep MemTotal /proc/meminfo
	echo "## pci"; lspci -nnk 2>/dev/null
	echo "## usb"; lsusb 2>/dev/null
	echo "## modules"; lsmod | awk 'NR>1{print $1}' | sort
	echo "## block"; lsblk -o NAME,SIZE,TYPE,FSTYPE,MODEL 2>/dev/null
	echo "## efi"; [ -d /sys/firmware/efi ] && echo uefi || echo bios
	echo "## kernel"; uname -r
	echo "## wifi"; ls /sys/class/net
	echo "## firmware asked for"; dmesg 2>/dev/null | grep -i 'firmware' | sed 's/^\[[^]]*\] //' | sort -u | head -40
} > "$out"
echo "wrote $out"
