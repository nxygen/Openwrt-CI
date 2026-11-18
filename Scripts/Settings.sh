#!/bin/bash

#修改默认主题
sed -i "s/luci-theme-bootstrap/luci-theme-$WRT_THEME/g" $(find ./feeds/luci/collections/ -type f -name "Makefile")
#修改openwrt.lan关联IP
sed -i "s/192\.168\.[0-9]*\.[0-9]*/$WRT_IP/g" $(find ./feeds/luci/modules/luci-mod-system/ -type f -name "flash.js")
#添加编译日期标识
sed -i "s/(\(luciversion || ''\))/(\1) + (' \/ CitrusCandy-$WRT_DATE')/g" $(find ./feeds/luci/modules/luci-mod-status/ -type f -name "10_system.js")

CFG_FILE="./package/base-files/files/bin/config_generate"
#修改默认IP地址
sed -i "s/192\.168\.[0-9]*\.[0-9]*/$WRT_IP/g" $CFG_FILE
#修改默认主机名
sed -i "s/hostname='.*'/hostname='$WRT_NAME'/g" $CFG_FILE

#配置文件修改
echo "CONFIG_PACKAGE_luci-theme-$WRT_THEME=y" >> ./.config
echo "CONFIG_PACKAGE_luci-app-$WRT_THEME-config=y" >> ./.config

#手动调整的插件
if [ -n "$WRT_PACKAGE" ]; then
	echo -e "$WRT_PACKAGE" >> ./.config
fi

# 代理插件互斥；手动附加配置也不能覆盖此选择。
case "${WRT_PROXY:-nikki}" in
	nikki|openclash|momo) ;;
	*) echo "Unsupported proxy: $WRT_PROXY" >&2; exit 1 ;;
esac
sed -i '/^CONFIG_PACKAGE_luci-app-\(nikki\|openclash\|momo\)=/d; /^# CONFIG_PACKAGE_luci-app-\(nikki\|openclash\|momo\) is not set$/d' ./.config
for proxy in nikki openclash momo; do
	if [ "$proxy" = "${WRT_PROXY:-nikki}" ]; then
		echo "CONFIG_PACKAGE_luci-app-$proxy=y" >> ./.config
	else
		echo "# CONFIG_PACKAGE_luci-app-$proxy is not set" >> ./.config
	fi
done

# #编译器优化
# if [[ $WRT_TARGET != *"X86"* ]]; then
# 	echo "CONFIG_TARGET_OPTIONS=y" >> ./.config
# 	echo "CONFIG_TARGET_OPTIMIZATION=\"-O2 -pipe -march=armv8-a+crypto+crc -mcpu=cortex-a53+crypto+crc -mtune=cortex-a53\"" >> ./.config
# fi
