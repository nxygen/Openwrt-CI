#!/bin/bash

# 确保 PKG_PATH 准确
PKG_PATH="$GITHUB_WORKSPACE/openwrt/package"
cd $PKG_PATH

# # 修改argon主题
# if [ -d "luci-theme-argon" ]; then
#     echo " "
#     cd ./luci-theme-argon/
#     sed -i '/font-weight:/ {/!important/! s/\(font-weight:\s*\)[^;]*;/\1normal;/}' $(find . -type f -iname "*.css")
#     sed -i "s/primary '.*'/primary '#31a1a1'/; s/'0.2'/'0.5'/; s/'none'/'bing'/" ./luci-app-argon-config/root/etc/config/argon
#     cd $PKG_PATH && echo "theme-argon has been fixed!"
# fi

# 修复Coremark编译
CM_FILE=$(find ../feeds/packages/ -maxdepth 3 -type f -wholename "*/coremark/Makefile")
if [ -f "$CM_FILE" ]; then
    sed -i 's/mkdir/mkdir -p/g' $CM_FILE
    echo "coremark has been fixed!"
fi

# 修改aurora式样
if [ -d "luci-app-aurora-config" ]; then
    echo " "
    cd ./luci-app-aurora-config/
    sed -i "s/nav_submenu_type '.*'/nav_submenu_type 'boxed-dropdown'/g" $(find ./root/ -type f -name "*aurora")
    cd $PKG_PATH && echo "theme-aurora has been fixed!"
fi

# 修复Rust编译
RUST_FILE=$(find ../feeds/packages/ -maxdepth 3 -type f -wholename "*/rust/Makefile")
if [ -f "$RUST_FILE" ]; then
    echo " "
    sed -i 's/ci-llvm=true/ci-llvm=false/g' $RUST_FILE
    echo "rust has been fixed!"
fi

# 修复 Tailscale 冲突
TS_FILE=$(find ../feeds/packages/ -maxdepth 4 -type f -wholename "*/tailscale/Makefile")
if [ -f "$TS_FILE" ]; then
    echo " "
    sed -i '/define Package\/tailscale\/conffiles/,/endef/d' "$TS_FILE"
    sed -i '/\/etc\/init.d\/tailscale/d' "$TS_FILE"
    sed -i '/\/etc\/config\/tailscale/d' "$TS_FILE"
    sed -i 's/\$(INSTALL_DIR) \$(1)\/usr\/sbin \$(1)\/etc\/init.d \$(1)\/etc\/config/\$(INSTALL_DIR) \$(1)\/usr\/sbin/g' "$TS_FILE"
    echo "tailscale has been fixed!"
fi

# 配置TurboACC
if [ -d "$GITHUB_WORKSPACE/openwrt" ]; then
    echo " "
    # CURRENT_PLATFORM="${WRT_CONFIG:-Unknown}"
    # SFE_PARAM=""
    # [[ ! "$CURRENT_PLATFORM" =~ (IPQ|Mt798|MTK|Qualcomm|Ramips) ]] && SFE_PARAM="--no-sfe"

    cd "$GITHUB_WORKSPACE/openwrt"
    # curl -sSL https://raw.githubusercontent.com/chenmozhijin/turboacc/luci/add_turboacc.sh -o add_turboacc.sh
    curl -sSL https://raw.githubusercontent.com/mufeng05/turboacc/main/add_turboacc.sh -o add_turboacc.sh
    [ -f "add_turboacc.sh" ] && bash add_turboacc.sh $SFE_PARAM
    rm -f add_turboacc.sh
    cd $PKG_PATH && echo "turboacc has been fixed!"
fi