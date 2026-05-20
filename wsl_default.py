import subprocess
import os
import time

def execute_in_default_wsl(linux_commands):
    """直接调用默认的 WSL2 发行版执行命令"""
    print(f"\n[⚡] 正在调用默认 WSL2 发行版执行命令...")
    CREATE_NO_WINDOW = 0x08000000
    
    # 直接使用 wsl.exe，不带 -d 参数，会自动使用默认发行版
    process = subprocess.Popen(
        ["wsl.exe", "--", "bash", "-c", linux_commands],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=CREATE_NO_WINDOW
    )
    
    stdout_bytes, stderr_bytes = process.communicate()
    stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ''
    stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ''
    return stdout, stderr

if __name__ == "__main__":
    start_time = time.time()
    
    try:
        test_script = """
        echo "=== 🖥️  默认 WSL2 环境信息 ==="
        echo "发行版:"
        cat /etc/os-release | grep PRETTY_NAME
        echo "内核:"
        uname -a
        echo "当前用户:"
        whoami
        echo "工作目录:"
        pwd
        """
        
        stdout_data, stderr_data = execute_in_default_wsl(test_script)
        
        print("\n[📤] WSL 执行结果:")
        print("-" * 40)
        print(stdout_data)
        if stderr_data:
            print(f"[错误]: {stderr_data}")
        print("-" * 40)
        
    except Exception as e:
        print(f"\n[❌] 发生错误: {str(e)}")
    finally:
        print(f"\n[⏱️] 执行耗时: {time.time() - start_time:.2f} 秒")
        print("[✅] 完成！")
