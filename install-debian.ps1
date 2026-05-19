# ==============================
# 全自动 Debian WSL 镜像提取 + 导入脚本
# ==============================

# 1. 创建临时目录
cd C:\
mkdir TempSandbox -Force | Out-Null
cd C:\TempSandbox

# 2. 下载官方 Debian
Write-Host "正在下载 Debian WSL 发行包..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://aka.ms/wsl-debian-gnulinux" -OutFile "debian.appx" -UseBasicParsing

# 3. 第一次解压（外层包）
Write-Host "第一次解压..." -ForegroundColor Cyan
Rename-Item -Path "debian.appx" -NewName "debian.zip" -Force
Expand-Archive -Path "debian.zip" -DestinationPath "debian_extracted" -Force

# 4. 第二次解压（真正的 rootfs 所在目录）
Write-Host "第二次解压（提取镜像）..." -ForegroundColor Cyan
$appx = Get-ChildItem -Recurse .\debian_extracted\*x64.appx | Select-Object -First 1
Expand-Archive -Path $appx.FullName -DestinationPath "debian_rootfs" -Force

# 5. 找到 install.tar.gz
$tar = Get-ChildItem -Recurse .\debian_rootfs\install.tar.gz | Select-Object -First 1
Write-Host "找到镜像：$($tar.FullName)" -ForegroundColor Green

# 6. 创建 WSL 安装目录
mkdir C:\wsl\Debian -Force | Out-Null

# 7. 导入到 WSL
Write-Host "正在导入 Debian 到 WSL..." -ForegroundColor Cyan
wsl --import Debian C:\wsl\Debian $tar.FullName

# 8. 完成
Write-Host "`n✅ 导入完成！输入以下命令启动：" -ForegroundColor Green
Write-Host "wsl -d Debian`n" -ForegroundColor Yellow

改成linux命令
