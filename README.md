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
| `black.py` | 主程序：创建沙箱 → 执行命令 → 销毁沙箱 |
| `install-debian.ps1` | 自动下载并安装 Debian WSL 发行版 |
| `build-full-image.ps1` | 构建预配置的完整 Ubuntu 镜像（含常用工具） |

## 使用流程

1. **准备镜像**：运行 `install-debian.ps1` 下载官方 Debian 镜像
2. **配置路径**：更新 `black.py` 中的 `ROOTFS_TAR_GZ` 路径
3. **执行测试**：运行 `python black.py`
4. **自动清理**：程序执行完毕后自动销毁沙箱

## 测试样例

默认测试脚本包含：
- 系统信息收集（发行版、内核、CPU、内存）
- 网络接口检测
- 网页爬取测试（百度首页）
- HTTP 响应头分析
- 外部 API 调用测试

## 注意事项

- 确保以管理员权限运行 PowerShell 脚本
- 首次运行可能需要较长时间下载镜像
- 沙箱销毁后所有数据将被永久删除

## 许可证

MIT License
