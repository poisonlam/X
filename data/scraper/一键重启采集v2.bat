@echo off
chcp 65001 >nul 2>&1
title R6 数据采集 v2 - 一键重启

echo ══════════════════════════════════════════════════════════════
echo   R6 Siege 数据采集 v2 - 一键重启脚本
echo ══════════════════════════════════════════════════════════════
echo.

cd /d "%~dp0"

:: Step 1: 备份现有数据
echo [Step 1/5] 备份现有数据...
python backup_data.py --clean-progress
if %errorlevel% neq 0 (
    echo [WARN] 备份失败或无数据可备份，继续...
)
echo.

:: Step 2: 构建名称映射表
echo [Step 2/5] 扫描已有数据，构建名称映射表...
python id_mapping.py
echo.

:: Step 3: 启动PC排行榜采集（5个分片）
echo [Step 3/5] 启动 PC 排行榜采集 (5 分片)...
set TOTAL_PC_SHARDS=5

start "PC-Shard-0" /min python parallel_collect_v2.py run --shard-id 0 --total-shards 5 --delay 1.0 --max-matches 10 --health-threshold 5
timeout /t 2 /nobreak >nul
start "PC-Shard-1" /min python parallel_collect_v2.py run --shard-id 1 --total-shards 5 --delay 1.0 --max-matches 10 --health-threshold 5
timeout /t 2 /nobreak >nul
start "PC-Shard-2" /min python parallel_collect_v2.py run --shard-id 2 --total-shards 5 --delay 1.0 --max-matches 10 --health-threshold 5
timeout /t 2 /nobreak >nul
start "PC-Shard-3" /min python parallel_collect_v2.py run --shard-id 3 --total-shards 5 --delay 1.0 --max-matches 10 --health-threshold 5
timeout /t 2 /nobreak >nul
start "PC-Shard-4" /min python parallel_collect_v2.py run --shard-id 4 --total-shards 5 --delay 1.0 --max-matches 10 --health-threshold 5
timeout /t 2 /nobreak >nul
echo   5 个 PC 分片已启动
echo.

:: Step 4: 启动额外玩家采集（8个分片）
echo [Step 4/5] 启动额外玩家采集 (8 分片)...
set TOTAL_EX_SHARDS=8

start "Extra-Shard-0" /min python extra_collect_v2.py run --shard-id 0 --total-shards 8 --delay 1.0 --max-matches 5 --health-threshold 5
timeout /t 2 /nobreak >nul
start "Extra-Shard-1" /min python extra_collect_v2.py run --shard-id 1 --total-shards 8 --delay 1.0 --max-matches 5 --health-threshold 5
timeout /t 2 /nobreak >nul
start "Extra-Shard-2" /min python extra_collect_v2.py run --shard-id 2 --total-shards 8 --delay 1.0 --max-matches 5 --health-threshold 5
timeout /t 2 /nobreak >nul
start "Extra-Shard-3" /min python extra_collect_v2.py run --shard-id 3 --total-shards 8 --delay 1.0 --max-matches 5 --health-threshold 5
timeout /t 2 /nobreak >nul
start "Extra-Shard-4" /min python extra_collect_v2.py run --shard-id 4 --total-shards 8 --delay 1.0 --max-matches 5 --health-threshold 5
timeout /t 2 /nobreak >nul
start "Extra-Shard-5" /min python extra_collect_v2.py run --shard-id 5 --total-shards 8 --delay 1.0 --max-matches 5 --health-threshold 5
timeout /t 2 /nobreak >nul
start "Extra-Shard-6" /min python extra_collect_v2.py run --shard-id 6 --total-shards 8 --delay 1.0 --max-matches 5 --health-threshold 5
timeout /t 2 /nobreak >nul
start "Extra-Shard-7" /min python extra_collect_v2.py run --shard-id 7 --total-shards 8 --delay 1.0 --max-matches 5 --health-threshold 5
timeout /t 2 /nobreak >nul
echo   8 个 Extra 分片已启动
echo.

:: Step 5: 启动监控面板
echo [Step 5/5] 启动监控面板...
echo.
echo ══════════════════════════════════════════════════════════════
echo   所有采集进程已启动！
echo   PC 排行榜: 5 个分片
echo   额外玩家: 8 个分片
echo   总计: 13 个采集进程
echo ══════════════════════════════════════════════════════════════
echo.

python live_monitor_v2.py

pause
