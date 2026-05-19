# ==============================
# Full-featured WSL Image Builder
# Based on Ubuntu 22.04 with pre-installed tools
# ==============================

# Configuration
$IMAGE_NAME = "ShadowUbuntu"
$INSTALL_DIR = "C:\TempSandbox\ActiveInstance"
$ROOTFS_DIR = "C:\TempSandbox\ubuntu_rootfs"
$TAR_PATH = "$ROOTFS_DIR\jammy-server-cloudimg-amd64-root.tar.xz"

# Create directories
mkdir C:\TempSandbox -Force | Out-Null
mkdir $INSTALL_DIR -Force | Out-Null

Write-Host "`n🚀 Starting to build full-featured Ubuntu image..." -ForegroundColor Cyan

# Step 1: Download official Ubuntu WSL package
if (-not (Test-Path $TAR_PATH)) {
    Write-Host "`n[1/4] Downloading official Ubuntu WSL package..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "https://aka.ms/wslubuntu2204" -OutFile "C:\TempSandbox\ubuntu.appx" -UseBasicParsing
    
    Write-Host "[2/4] Extracting image files..." -ForegroundColor Cyan
    Rename-Item -Path "C:\TempSandbox\ubuntu.appx" -NewName "ubuntu.zip" -Force
    Expand-Archive -Path "C:\TempSandbox\ubuntu.zip" -DestinationPath "C:\TempSandbox\ubuntu_extracted" -Force
    
    $appx = Get-ChildItem -Recurse "C:\TempSandbox\ubuntu_extracted\*x64.appx" | Select-Object -First 1
    Expand-Archive -Path $appx.FullName -DestinationPath $ROOTFS_DIR -Force
}

# Step 2: Create temporary WSL instance for configuration
Write-Host "`n[3/4] Importing temporary instance for configuration..." -ForegroundColor Cyan
wsl --import __temp_build $INSTALL_DIR $TAR_PATH --version 2 2>&1 | Out-Null

# Step 3: Install tools inside sandbox
Write-Host "Installing common tools..." -ForegroundColor Yellow

# 使用 Base64 编码传递脚本，避免换行符问题
$setup_script = @'
set -e
export DEBIAN_FRONTEND=noninteractive

echo "Updating package sources..."
sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
apt-get update

echo "Installing base tools..."
apt-get install -y curl wget git vim nano htop tmux python3 python3-pip build-essential gcc g++ make net-tools iputils-ping dnsutils openssh-server openssl zip unzip tar gzip bzip2 tree jq rsync html2text ca-certificates apt-transport-https

echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

echo "Cleaning up..."
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "Setup completed"
'@

# 将脚本编码为 Base64 避免换行符问题
$bytes = [System.Text.Encoding]::UTF8.GetBytes($setup_script)
$base64 = [Convert]::ToBase64String($bytes)

# 通过 Base64 传递脚本到 WSL
wsl -d __temp_build -- bash -c "echo '$base64' | base64 -d | bash"

# Step 4: Export configured image
Write-Host "`n[4/4] Exporting configured image..." -ForegroundColor Cyan
mkdir "C:\TempSandbox\full_image" -Force | Out-Null
wsl --export __temp_build "C:\TempSandbox\full_image\ubuntu-full.tar.gz"

# Cleanup temporary instance
wsl --unregister __temp_build 2>&1 | Out-Null

Write-Host "`n✅ Image build completed!" -ForegroundColor Green
Write-Host "Image location: C:\TempSandbox\full_image\ubuntu-full.tar.gz" -ForegroundColor Yellow
Write-Host "`nUsage:" -ForegroundColor Cyan
Write-Host "1. Update ROOTFS_TAR_GZ in black.py to point to this image" -ForegroundColor White
Write-Host "2. Or run: wsl --import ShadowUbuntu $INSTALL_DIR C:\TempSandbox\full_image\ubuntu-full.tar.gz`n" -ForegroundColor White
