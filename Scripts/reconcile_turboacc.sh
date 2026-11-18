#!/bin/bash
# Preserve ImmortalWrt's FullCone support when TurboACC adds its own patches.
set -euo pipefail

root=${1:?OpenWrt source directory is required}
native_patches=(
    package/network/utils/nftables/patches/002-nftables-add-fullcone-expression-support.patch
    package/libs/libnftnl/patches/001-libnftnl-add-fullcone-expression-support.patch
    package/network/config/firewall4/patches/001-firewall4-add-support-for-fullcone-nat.patch
)
duplicate=package/network/utils/nftables/patches/100-nftables-add-fullcone-expression-support.patch

# A changed upstream layout needs review instead of silently dropping patches.
for path in "${native_patches[@]}"; do
    if ! git -C "$root" cat-file -e "HEAD:$path" 2>/dev/null; then
        echo "ImmortalWrt FullCone patch not found in release: $path" >&2
        exit 1
    fi
done
if git -C "$root" cat-file -e "HEAD:$duplicate" 2>/dev/null; then
    echo "Duplicate patch name belongs to the release; refusing to remove it: $duplicate" >&2
    exit 1
fi

for path in "${native_patches[@]}"; do
    git -C "$root" show "HEAD:$path" > "$root/$path"
done
rm -f -- "$root/$duplicate"
echo "Preserved ImmortalWrt FullCone patches and removed TurboACC's duplicate nftables patch."
