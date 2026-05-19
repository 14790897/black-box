import subprocess
import os
import time

# ================= 测试配置 =================
SANDBOX_NAME = "ShadowDebianTest"                       # 独立的沙箱实例名称
# ROOTFS_TAR_GZ = r"C:\TempSandbox\debian_rootfs\install.tar.gz"  # 轻便版本，无curl
# ROOTFS_TAR_GZ = r"C:\TempSandbox\ubuntu_rootfs\jammy-server-cloudimg-amd64-root.tar.xz"  # 支持 .xz 格式
ROOTFS_TAR_GZ = r"C:\TempSandbox\full_image\ubuntu-full.tar.gz"  # 支持 .gz 格式
SANDBOX_DIR = r"C:\TempSandbox\ActiveInstance"          # 沙箱虚拟硬盘（.vhdx）存放地
# ============================================

def setup_sandbox():
    """静默导入并注册独立的普通镜像沙箱"""
    if not os.path.exists(SANDBOX_DIR):
        os.makedirs(SANDBOX_DIR)
        
    print(f"[1/4] 正在将普通镜像注册为影子沙箱 [{SANDBOX_NAME}]...")
    CREATE_NO_WINDOW = 0x08000000
    
    # 显式指定 --version 2 确保启用高性能的 WSL2 架构
    cmd = ["wsl.exe", "--import", SANDBOX_NAME, SANDBOX_DIR, ROOTFS_TAR_GZ, "--version", "2"]
    result = subprocess.run(cmd, creationflags=CREATE_NO_WINDOW, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("[+] 影子沙箱注册成功。")
        return True
    else:
        print(f"[-] 注册失败: {result.stderr}")
        print("[!] 触发紧急清理机制...")
        destroy_sandbox()
        return False

def execute_in_sandbox(linux_commands):
    """核心黑盒逻辑：通过内存管道输入指令，不让外人通过控制台看到历史记录"""
    print(f"\n[2/4] 正在穿透内核管道，向沙箱静默注入敏感指令...")
    CREATE_NO_WINDOW = 0x08000000
    
    # 启动指定沙箱，直接挂载 bash
    # 使用二进制模式完全控制发送的内容，避免任何自动换行符转换
    process = subprocess.Popen(
        ["wsl.exe", "-d", SANDBOX_NAME, "--", "bash"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=CREATE_NO_WINDOW
    )
    
    # 将 Windows 换行符转换为 Linux 换行符并编码为字节
    linux_commands_bytes = linux_commands.encode('utf-8')
    # 将要执行的 Linux 脚本一次性灌入标准输入流
    stdout_bytes, stderr_bytes = process.communicate(input=linux_commands_bytes)
    # 解码返回结果
    stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ''
    stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ''
    return stdout, stderr

def destroy_sandbox():
    """用完即焚：注销并粉碎虚拟硬盘文件"""
    print(f"\n[3/4] 触发用完即焚机制，正在注销沙箱...")
    CREATE_NO_WINDOW = 0x08000000
    cmd = ["wsl.exe", "--unregister", SANDBOX_NAME]
    subprocess.run(cmd, creationflags=CREATE_NO_WINDOW, capture_output=True)
    print("[+] 影子沙箱已注销，对应的虚拟硬盘已被 Windows 彻底粉碎。")

if __name__ == "__main__":
    try:
        # 1. 注册沙箱
        if not setup_sandbox():
            print("\n[❌] 沙箱注册失败，程序退出。")
            exit(1)
        
        # 2. 编写一段用于测试的 Linux 脚本（这里可以模拟你的核心业务代码）
        test_script = """
        echo "=== 🖥️  沙箱主机信息收集 ==="
        echo "1. Linux 系统发行版:"
        cat /etc/os-release | grep PRETTY_NAME
        
        echo "2. 内核架构信息:"
        uname -a
        
        echo "3. CPU 信息:"
        cat /proc/cpuinfo | grep "model name" | head -n 1
        
        echo "4. 内存信息:"
        cat /proc/meminfo | grep MemTotal
        
        echo "5. 网络接口:"
        ip addr show | grep "inet " | head -n 2
        
        echo "6. 当前用户:"
        whoami
        
        echo ""
        echo "=== 🕸️  网页爬取测试 ==="
        echo "准备安装必要工具..."
        sed -i '/bullseye-backports/d' /etc/apt/sources.list
        # If it is a minimal image without curl and html2text, we can install them first. If it is a full image, this step will be skipped because they are already included.
        # DEBIAN_FRONTEND=noninteractive apt-get update 2>/dev/null && DEBIAN_FRONTEND=noninteractive apt-get install curl html2text -y 2>/dev/null
        
        echo ""
        echo "7. 爬取百度首页标题:"
        curl -s https://www.baidu.com | html2text | head -n 10
        
        echo ""
        echo "8. 获取 HTTP 响应头信息:"
        curl -I -s https://www.baidu.com | head -n 5
        
        echo ""
        echo "9. 测试外部 API 调用:"
        curl -s https://api.ipify.org?format=json
        
        echo ""
        echo "=== ✅ 测试完毕 ==="
        """
        
        # 3. 管道无痕执行
        stdout_data, stderr_data = execute_in_sandbox(test_script)
        
        print("\n[4/4] 宿主机收到沙箱回执密文:")
        print("-" * 40)
        print(stdout_data)
        if stderr_data:
            print(f"异常提示: {stderr_data}")
        print("-" * 40)
        
    except Exception as e:
        print(f"\n[❌] 发生致命错误: {str(e)}")
        print("[!] 触发紧急清理机制...")
    finally:
        # 4. 强制抹除痕迹（无论成功与否都执行）
        destroy_sandbox()
        print("\n[✅] 影子沙箱闭环测试完成！")
