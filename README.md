# Black Box - WSL 影子沙箱测试工具

基于 Windows Subsystem for Linux (WSL) 的隔离式测试环境，提供"用完即焚"的安全执行能力。

## 功能特性

- 🔒 **隔离执行**：在独立的 WSL 沙箱中运行敏感指令
- 🔥 **用完即焚**：执行完成后自动销毁沙箱，不留痕迹
- 🤫 **静默模式**：通过内存管道注入指令，无控制台历史记录
- 🚀 **高性能**：使用 WSL2 架构，支持完整 Linux 环境

## 快速开始

### 前提条件

1. 已安装 Windows Subsystem for Linux
2. 已启用 WSL2 模式
3. 已下载 Debian rootfs 镜像

### 配置

编辑 `black.py` 中的配置项：

```python
SANDBOX_NAME = "ShadowDebianTest"           # 沙箱实例名称
ROOTFS_TAR_GZ = r"C:\TempSandbox\debian_rootfs\install.tar.gz"  # rootfs 路径
SANDBOX_DIR = r"C:\TempSandbox\ActiveInstance"  # 虚拟硬盘存放目录
```

### 运行

```bash
python black.py
```

## 脚本说明

| 文件 | 用途 |
|------|------|
| `black.py` / `aisandbox.py` | 主程序 (WSL 版)：创建沙箱 → 执行命令 → 销毁沙箱 |
| `hyperv_sandbox.py` | 主程序 (Hyper-V 版)：基于差异磁盘创建 Hyper-V 沙箱 → 通过 PowerShell Direct 注入执行 → 销毁沙箱 |
| `install-debian.ps1` | 自动下载并安装 Debian WSL 发行版 |
| `build-full-image.ps1` | 构建预配置的完整 Ubuntu 镜像（含常用工具） |

## Hyper-V 版本 (Windows)

新增了针对 Hyper-V 环境的 `hyperv_sandbox.py`，主要用于运行 Windows 或支持 PowerShell Direct 的 Linux 镜像。它使用**差异磁盘 (Differencing Disk)** 技术，可以实现秒级创建虚拟机，用完即焚。

### Hyper-V 配置
编辑 `hyperv_sandbox.py` 中的配置：
```python
BASE_VHDX = r"C:\TempSandbox\base_image\windows_base.vhdx" # 你的基础 VHDX 镜像
VM_USER = "Administrator" # 虚拟机内的用户名
VM_PASS = "123456"        # 虚拟机内的密码
```
*注：Hyper-V 版必须使用**管理员权限**的终端运行。*

## 使用流程

1. **准备镜像**：运行 `install-debian.ps1` 下载官方 Debian 镜像
2. **配置路径**：更新 `black.py` 中的 `ROOTFS_TAR_GZ` 路径
3. **执行测试**：运行 `python black.py` 进入交互式环境，或使用命令行参数执行。

### 命令行参数
你可以通过传参灵活控制沙箱行为：
- `python black.py`：进入交互式 REPL，直接输入 Linux 指令（输入 `multiline` 可执行多行，`exit` 退出）。
- `python black.py -c "<指令>"`：执行单条指令并自动销毁沙箱。
- `python black.py -f <文件路径>`：执行本地脚本文件并自动销毁。
- `python black.py --keep`：执行完毕后保留沙箱，不自动销毁。
- `python black.py --cleanup`：强制清理现存的沙箱。

## 测试样例

通过交互式模式：
```bash
$ python black.py

[🤖] AI 虚拟环境已就绪 (交互模式)。
当前在隔离的沙箱环境中，文件系统修改会保留，直至沙箱销毁。
输入指令执行，或输入 'exit'、'quit' 退出。输入 'multiline' 开启多行输入。
AI-Env > uname -a
Linux WIN-PC 5.15.133.1-microsoft-standard-WSL2 #1 SMP Thu Aug 24 16:11:16 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux
AI-Env > exit

[3/4] 触发用完即焚机制，正在注销沙箱...
[+] 影子沙箱已注销，对应的虚拟硬盘已被 Windows 彻底粉碎。
```

或者单条指令执行：
```bash
python black.py -c "cat /etc/os-release"
```

## 注意事项

- 确保以管理员权限运行 PowerShell 脚本
- 首次运行可能需要较长时间下载镜像
- 沙箱销毁后所有数据将被永久删除

## 许可证

MIT License
