import subprocess
import os
import sys
import argparse
import time

# ================= 测试配置 =================
SANDBOX_NAME = "ShadowHyperVTest"                        # 独立的沙箱实例名称
BASE_VHDX = r"C:\ProgramData\Microsoft\Windows\Virtual Hard Disks\Ubuntu 22.04 LTS.vhdx" # 基础镜像 VHDX 路径
SANDBOX_DIR = r"C:\TempSandbox\ActiveInstance"           # 运行时的差异磁盘存放地
SANDBOX_VHDX = os.path.join(SANDBOX_DIR, f"{SANDBOX_NAME}.vhdx")

# Ubuntu 虚拟机的凭据 (请根据实际 Ubuntu 镜像的用户名和密码进行修改)
# 此处使用 SSH 方式进行连接，因此需要确保镜像中已安装并启动了 SSH 服务
VM_USER = "ubuntu"
VM_PASS = "ubuntu"
# ============================================

def run_ps_cmd(cmd, capture=True):
    """运行 PowerShell 命令"""
    creationflags = 0x08000000 if os.name == 'nt' else 0
    process = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd],
        capture_output=capture, text=True, creationflags=creationflags
    )
    return process

def setup_sandbox():
    """使用差异磁盘机制，秒级创建 Hyper-V 沙箱"""
    if not os.path.exists(SANDBOX_DIR):
        os.makedirs(SANDBOX_DIR)
        
    print(f"[1/4] 正在使用基础镜像创建 Hyper-V 差异磁盘 [{SANDBOX_NAME}]...")
    
    # 检查基础镜像是否存在
    if not os.path.exists(BASE_VHDX):
        print(f"[-] 找不到基础 VHDX 镜像: {BASE_VHDX}")
        return False
        
    # 1. 创建差异磁盘 (秒级)
    create_vhd_cmd = f"New-VHD -ParentPath '{BASE_VHDX}' -Path '{SANDBOX_VHDX}' -Differencing -ErrorAction SilentlyContinue"
    res = run_ps_cmd(create_vhd_cmd)
    
    # 2. 创建并配置虚拟机
    # 尝试使用第一代虚拟机 (Generation 1)，因为很多下回来的 VHDX 并不是 UEFI 引导的
    print(f"[+] 正在注册 Hyper-V 虚拟机...")
    create_vm_cmd = f"New-VM -Name '{SANDBOX_NAME}' -VHDPath '{SANDBOX_VHDX}' -MemoryStartupBytes 2GB -Generation 1 -ErrorAction SilentlyContinue"
    run_ps_cmd(create_vm_cmd)
    
    # 尝试将其连接到默认交换机。由于中文版叫 "Default Switch"，为了兼容性，我们通过 ID 查找
    connect_switch_cmd = f"Get-VMSwitch | Where-Object SwitchType -eq 'Internal' | Select-Object -First 1 | Connect-VMNetworkAdapter -VMName '{SANDBOX_NAME}'"
    run_ps_cmd(connect_switch_cmd)
    
    # 如果创建成了第二代，才需要关闭安全启动；第一代没有这个概念，执行会报错但被忽略
    run_ps_cmd(f"Set-VMFirmware -VMName '{SANDBOX_NAME}' -EnableSecureBoot Off -ErrorAction SilentlyContinue")
    
    # 3. 启动虚拟机
    print(f"[+] 正在启动沙箱虚拟机，等待开机和网络就绪...")
    run_ps_cmd(f"Start-VM -Name '{SANDBOX_NAME}'")
    
    import re
    
    # 等待虚拟机启动并获取 IP 地址
    # Linux 启动和通过 DHCP 获取 IP 需要较长时间，增加重试次数
    max_retries = 60
    vm_ip = None
    for i in range(max_retries):
        time.sleep(2)
        print(f"  ... 正在尝试获取 IP 地址 ({i+1}/{max_retries})", end="\r")
        
        # 方法1: 尝试通过 Get-VMNetworkAdapter 获取（最可靠）
        get_ip_cmd2 = f"(Get-VMNetworkAdapter -VMName '{SANDBOX_NAME}').IPAddresses | Where-Object {{ $_ -match '^(?:[0-9]{{1,3}}\\.){{3}}[0-9]{{1,3}}$' -and $_ -notmatch '^169\\.254\\.' }} | Select-Object -First 1"
        res = run_ps_cmd(get_ip_cmd2, capture=True)
        if res.stdout.strip():
            ip_candidate = res.stdout.strip()
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip_candidate):
                vm_ip = ip_candidate
                print(f"\n[+] 成功获取沙箱 IP 地址: {vm_ip}")
                break
            
        # 方法2: 尝试通过 Get-VMGuestNetworkInterface 获取（需要集成服务）
        get_ip_cmd1 = f"Get-VMGuestNetworkInterface -VMName '{SANDBOX_NAME}' 2>&1 | Where-Object {{ $_.IPAddresses }} | Select-Object -ExpandProperty IPAddresses -First 1"
        res = run_ps_cmd(get_ip_cmd1, capture=True)
        if res.stdout.strip():
            ip_candidate = res.stdout.strip()
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip_candidate):
                vm_ip = ip_candidate
                print(f"\n[+] 成功获取沙箱 IP 地址: {vm_ip}")
                break
            
        # 方法3: 尝试通过 ARP 缓存获取
        get_ip_cmd3 = f"arp -a | Where-Object {{ $_ -match '\\b(?:[0-9]{{1,3}}\\.){{3}}[0-9]{{1,3}}\\b' -and $_ -notmatch '^169\\.254\\.' -and $_ -notmatch '255\\.255\\.255\\.255' }} | Select-Object -First 1 | ForEach-Object {{ $_.Split()[0] }}"
        res = run_ps_cmd(get_ip_cmd3, capture=True)
        if res.stdout.strip():
            ip_candidate = res.stdout.strip()
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip_candidate):
                vm_ip = ip_candidate
                print(f"\n[+] 成功获取沙箱 IP 地址: {vm_ip}")
                break
            
    if not vm_ip:
        print("\n[-] 无法获取虚拟机 IP 地址，可能是系统未成功启动或未连接网络。")
        print("    建议：1. 检查基础镜像 VHDX 是否损坏。")
        print("          2. 打开 Hyper-V 管理器查看虚拟机是否卡在启动界面。")
        print("          3. 确保虚拟机已连接到 Default Switch 或内部交换机。")
        return False
        
    # 等待 SSH 服务启动
    print("[+] 正在等待 SSH 服务就绪...")
    time.sleep(10) 
    return vm_ip

def execute_in_sandbox(commands, vm_ip):
    """通过 SSH 执行命令"""
    print(f"\n[2/4] 正在通过 SSH 向沙箱注入指令...")
    
    # 将命令保存到临时文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
        f.write(commands)
        temp_script = f.name
        
    try:
        # 使用 sshpass 提供密码并执行 ssh 命令
        # 注意：这需要宿主机安装了 OpenSSH 客户端 (Windows 10/11 默认已安装)
        # 但是 Windows 没有原生的 sshpass，所以我们使用一个折中方案：
        # 将脚本内容通过 stdin 传给 ssh。
        # 这里为了简化，假设已经配置了免密或者可以直接通过 plink/外部工具，
        # 但标准的 ssh 命令在交互式密码输入上在 python 的 subprocess 中很难处理。
        # 
        # 最稳妥且不需要外部工具的方式是使用 paramiko 库，但为了保持单文件脚本，
        # 我们这里依然尝试使用内置组件。
        # 由于 PowerShell Direct 对 Linux 支持有限（需要安装额外的集成服务和 powershell），
        # 我们改用 SSH。如果环境不允许安装 paramiko，下面的代码尝试用最基础的 ssh 客户端执行，
        # 但它可能因为需要输入密码而阻塞。
        
        # 更好的方案（如果只是测试）：要求用户设置免密，或者...
        # 这里我们使用一个简单的技巧，如果没法免密，至少把命令传过去
        print(f"[*] 注意：请确保已配置免密登录，或者准备好在终端输入密码 ({VM_PASS})。")
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{VM_USER}@{vm_ip}", "bash", "-s"]
        
        creationflags = 0x08000000 if os.name == 'nt' else 0
        process = subprocess.Popen(
            ssh_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # 不要使用 CREATE_NO_WINDOW 如果需要用户输入密码，
            # 但我们要尝试自动化，所以还是用。如果阻塞，说明需要配免密。
            creationflags=creationflags 
        )
        
        stdout_bytes, stderr_bytes = process.communicate(input=commands.encode('utf-8'))
        stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ''
        stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ''
        return stdout, stderr
        
    finally:
        if os.path.exists(temp_script):
            os.remove(temp_script)

def destroy_sandbox():
    """注销虚拟机，并粉碎差异磁盘文件"""
    print(f"\n[3/4] 触发用完即焚机制，正在销毁 Hyper-V 沙箱...")
    
    # 强制关闭、删除虚拟机
    run_ps_cmd(f"Stop-VM -Name '{SANDBOX_NAME}' -TurnOff -ErrorAction SilentlyContinue")
    run_ps_cmd(f"Remove-VM -Name '{SANDBOX_NAME}' -Force -ErrorAction SilentlyContinue")
    
    # 删除差异磁盘
    if os.path.exists(SANDBOX_VHDX):
        try:
            os.remove(SANDBOX_VHDX)
            print("[+] 对应的虚拟差异磁盘已被彻底粉碎。")
        except Exception as e:
            print(f"[-] 删除磁盘失败: {e}")
            
    print("[+] 影子沙箱已彻底销毁。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 影子沙箱执行环境 (Hyper-V 版 - Ubuntu)")
    parser.add_argument("-c", "--command", type=str, help="直接执行单条指令 (Bash)")
    parser.add_argument("-f", "--file", type=str, help="执行指定的本地 Bash 脚本文件")
    parser.add_argument("--keep", action="store_true", help="执行结束后保留沙箱不销毁")
    parser.add_argument("--cleanup", action="store_true", help="强制注销并清理现有的沙箱")
    args = parser.parse_args()

    # 需要管理员权限才能运行 Hyper-V 命令
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("[!] 警告: Hyper-V 模块通常需要管理员权限运行，如果后续报错请使用管理员身份运行此脚本。")

    if args.cleanup:
        destroy_sandbox()
        sys.exit(0)

    try:
        vm_ip = setup_sandbox()
        if not vm_ip:
            print("\n[❌] 沙箱注册/启动失败，程序退出。")
            sys.exit(1)
            
        if args.command:
            out, err = execute_in_sandbox(args.command, vm_ip)
            if out: print(out, end="")
            if err: print(err, file=sys.stderr, end="")
        elif args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                script = f.read()
            out, err = execute_in_sandbox(script, vm_ip)
            if out: print(out, end="")
            if err: print(err, file=sys.stderr, end="")
        else:
            print(f"\n[🤖] AI 虚拟环境 (Hyper-V Ubuntu @ {vm_ip}) 已就绪 (交互模式)。")
            print("当前在隔离的 Ubuntu 虚拟机内，默认执行 Bash 命令。")
            print("输入指令执行，或输入 'exit'、'quit' 退出。输入 'multiline' 开启多行输入。")
            while True:
                try:
                    cmd = input("Ubuntu-Env > ")
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
                    
                    out, err = execute_in_sandbox(cmd, vm_ip)
                    if out: print(out, end="")
                    if err: print(f"Error:\n{err}", file=sys.stderr, end="")
                except (EOFError, KeyboardInterrupt):
                    break
    except Exception as e:
        print(f"\n[❌] 发生致命错误: {str(e)}")
        import traceback
        traceback.print_exc()
        print("[!] 触发紧急清理机制...")
    finally:
        if not args.keep:
            destroy_sandbox()
            print("\n[✅] 影子沙箱已销毁，闭环完成！")
        else:
            print("\n[!] 沙箱未销毁 (--keep)，可通过运行 'python hyperv_sandbox.py --cleanup' 手动清理。")
