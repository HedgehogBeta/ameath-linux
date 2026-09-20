# Ameath Linux

<p align="center">
  <img src="ameath_linux/assets/gifs/ameath.gif" alt="Ameath desktop pet" width="360">
</p>

<p align="center">
  Ameath 桌面宠物的非官方 Linux 移植版。
</p>

> 本项目基于 [lzy-buaa-jdi/ameath](https://gitee.com/lzy-buaa-jdi/ameath) v1.1.9 开发。上游项目面向 Windows；本仓库重写了窗口、托盘、自启和进程控制等平台相关实现，并保留上游的角色素材、语音和音乐。本项目与上游作者没有官方关联。

## 功能

- 游荡、鼠标跟随、近距离好奇和随机休息状态机
- 惯性移动、边缘平滑反弹和左右移动动画
- 移动、待机、拖拽、暂停和窗口贴靠动画
- 0.1x–2.0x 缩放、10%–100% 透明度、1–80 个桌宠实例
- 鼠标穿透、始终置顶、全屏时隐藏和桌面底层模式
- 多屏联动或指定屏幕，支持 6 种启动位置
- 右键快捷菜单、系统托盘和 XDG 开机自启
- 拖拽随机语音和内置音乐播放器
- 单实例控制：重复启动用于唤回，`--quit` 用于退出
- 个性化、音乐、更新和关于设置页

## 平台支持

X11 下功能最完整，包括活动窗口检测、全屏检测和暂停贴靠。

Wayland 不允许普通应用全局读取其他窗口，因此窗口贴靠和全屏检测会自动降级。置顶、置底和鼠标穿透取决于桌面组合器对 Qt 窗口标志的支持。

## 安装

### Debian / Ubuntu 发行包

从 GitHub Releases 下载 `.deb` 后安装：

```bash
sudo apt install ./ameath-linux_1.1.9.3_all.deb
ameath-linux
```

### 从源码运行

需要 Python 3.10+、PyQt5 和 GStreamer。Ubuntu/Debian 可安装：

```bash
sudo apt install python3-pyqt5 python3-gi gir1.2-gstreamer-1.0 gstreamer1.0-plugins-good x11-utils
```

然后运行：

```bash
git clone https://github.com/HedgehogBeta/ameath-linux.git
cd ameath-linux
./run.sh
```

或安装到当前用户：

```bash
./install.sh
ameath-linux
```

## 使用

- 右键桌宠或托盘图标可打开快捷菜单。
- 桌宠隐藏后，再次启动程序或再次点击应用图标即可唤回。
- 命令行退出：`ameath-linux --quit`。
- 开启鼠标穿透后，请通过托盘、重复启动或 `--quit` 管理实例。

## 本地数据

| 用途 | 默认位置 |
| --- | --- |
| 配置 | `~/.config/ameath-linux/config.json` |
| 开机自启 | `~/.config/autostart/ameath-linux.desktop` |
| 用户歌曲 | `~/ameath_songs/` |
| 单实例锁 | `$XDG_RUNTIME_DIR/ameath-linux-<uid>.lock` |

项目不会上传这些本地数据。

## 开发与打包

```bash
python3 -m pytest
./scripts/package_release.sh
```

打包脚本会生成 Python wheel、源码包、便携版压缩包、Debian 包和 `SHA256SUMS`。GitHub Actions 会在推送 `v*` 标签时重建并发布同样的产物。

## 上游、素材与授权

- 上游项目：[lzy-buaa-jdi/ameath](https://gitee.com/lzy-buaa-jdi/ameath)
- 上游作者：sinlatansen / -fugu-
- GIF 素材：上游 README 鸣谢 Bilibili 创作者 [@_BLZ_](https://b23.tv/LOWldqI)
- 代码与随上游分发的素材遵循 [MIT License](LICENSE)

详细来源记录见 [SOURCE-LICENSE](SOURCE-LICENSE)。
