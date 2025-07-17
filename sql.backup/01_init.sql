# 创建新的数据库初始化脚本

# 确保sql目录存在
if (!(Test-Path "sql")) {
    New-Item -ItemType Directory -Name "sql"
}

# 创建新的初始化文件
$sqlContent = Get-Content -Path "上面提供的SQL内容" -Raw

# 保存到文件
$sqlContent | Out-File -FilePath "sql\01-mold-tables.sql" -Encoding UTF8

Write-Host "✅ 数据库表结构文件已创建" -ForegroundColor Green