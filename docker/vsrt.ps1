<#
.SYNOPSIS
  在 WSL 的 GPU 容器裡跑 VideoSrt CLI，供 Windows 端直接呼叫。

.DESCRIPTION
  只是把參數原封不動轉給 docker/vsrt.sh，路徑轉換與掛載邏輯都在那裡，
  避免兩份實作走鐘。Windows 路徑（D:\ai\...）可以直接傳。

.EXAMPLE
  .\docker\vsrt.ps1 VIDEO\影片.mp4 --model large-v3
  .\docker\vsrt.ps1 --input D:\影片\上課.mp4 --output D:\輸出 --model large-v3
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = 'Stop'

# 讓容器內 Python 的 UTF-8 輸出在主控台正常顯示
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)

$distro = if ($env:VSRT_DISTRO) { $env:VSRT_DISTRO } else { 'kali-linux' }

# 本腳本所在的 docker\ 目錄 → WSL 路徑
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptLinux = (wsl.exe -d $distro -- wslpath -a $scriptDir.Replace('\', '/')).Trim()

if (-not $Arguments) { $Arguments = @('--help') }

wsl.exe -d $distro -- "$scriptLinux/vsrt.sh" @Arguments
exit $LASTEXITCODE
