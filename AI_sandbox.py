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
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="AI 影子沙箱执行环境")
    parser.add_argument("-c", "--command", type=str, help="直接执行单条 Linux 指令")
    parser.add_argument("-f", "--file", type=str, help="执行指定的本地脚本文件")
    parser.add_argument("--keep", action="store_true", help="执行结束后保留沙箱不销毁")
    parser.add_argument("--cleanup", action="store_true", help="强制注销并清理现有的沙箱")
    args = parser.parse_args()

    if args.cleanup:
        destroy_sandbox()
        exit(0)

    try:
        # 1. 注册沙箱
        # 注意：如果沙箱已存在，wsl --import 会失败。这里默认按"用完即焚"流程走。
        if not setup_sandbox():
            print("\n[❌] 沙箱注册失败，程序退出。")
            exit(1)
        
        # 2. 执行指令
        if args.command:
            stdout_data, stderr_data = execute_in_sandbox(args.command)
            if stdout_data: print(stdout_data, end="")
            if stderr_data: print(stderr_data, file=sys.stderr, end="")
        elif args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                script = f.read()
            stdout_data, stderr_data = execute_in_sandbox(script)
            if stdout_data: print(stdout_data, end="")
            if stderr_data: print(stderr_data, file=sys.stderr, end="")
        else:
            # 交互式 REPL 模式
            print("\n[🤖] AI 虚拟环境已就绪 (交互模式)。")
            print("当前在隔离的沙箱环境中，文件系统修改会保留，直至沙箱销毁。")
            print("输入指令执行，或输入 'exit'、'quit' 退出。输入 'multiline' 开启多行输入。")
            while True:
                try:
                    cmd = input("AI-Env > ")
                    if cmd.strip().lower() in ['exit', 'quit']:
                        break
                    elif cmd.strip().lower() == 'multiline':
                        print("进入多行输入模式，输入 'END' 结束并执行：")
                        lines = []
                        while True:
                            line = input()
                            if line.strip() == 'END':
                                break
                            lines.append(line)
                        cmd = "\n".join(lines)
                    
                    if not cmd.strip():
                        continue
                    
                    stdout_data, stderr_data = execute_in_sandbox(cmd)
                    if stdout_data:
                        print(stdout_data, end="")
                    if stderr_data:
                        print(f"Error:\n{stderr_data}", file=sys.stderr, end="")
                        
                except (EOFError, KeyboardInterrupt):
                    break

    except Exception as e:
        print(f"\n[❌] 发生致命错误: {str(e)}")
        print("[!] 触发紧急清理机制...")
    finally:
        # 3. 强制抹除痕迹
        if not args.keep:
            destroy_sandbox()
            print("\n[✅] 影子沙箱已销毁，闭环完成！")
        else:
            print("\n[!] 沙箱未销毁 (--keep)，可通过运行 'python black.py --cleanup' 手动清理。")
