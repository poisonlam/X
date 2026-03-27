@echo off
chcp 65001 >nul 2>&1
title R6 采集 - 一键启动全部
color 0B

echo ╔═══════════════════════════════════════════════════════════╗
echo ║   R6 Siege 数据采集 - 一键启动                           ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/3] 清理旧进程...
:: 杀掉旧的 parallel_collect 和 extract_and_collect_extra 进程
for /f "tokens=2" %%i in ('wmic process where "commandline like '%%parallel_collect%%' and name='python.exe'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    echo   杀掉 PC 进程 PID %%i
    taskkill /PID %%i /F >nul 2>&1
)
for /f "tokens=2" %%i in ('wmic process where "commandline like '%%extract_and_collect_extra%%' and name='python.exe'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    echo   杀掉 Extra 进程 PID %%i
    taskkill /PID %%i /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo.
echo [2/3] 启动 PC 采集 (5个分片, 各有独立窗口)...
for /L %%i in (0,1,4) do (
    start "R6-PC-Shard-%%i" cmd /c "chcp 65001 >nul & title R6 PC Shard %%i & cd /d %~dp0 & python -u parallel_collect.py run --shard-id %%i --total-shards 5 --delay 1.0 & echo. & echo === 分片 %%i 已完成 === & pause"
    timeout /t 1 /nobreak >nul
)

echo [3/3] 启动 Extra 采集 (8个分片, 各有独立窗口)...
for /L %%i in (0,1,7) do (
    start "R6-Extra-Shard-%%i" cmd /c "chcp 65001 >nul & title R6 Extra Shard %%i & cd /d %~dp0 & python -u extract_and_collect_extra_players.py run --shard-id %%i --total-shards 8 --delay 1.0 & echo. & echo === Extra 分片 %%i 已完成 === & pause"
    timeout /t 1 /nobreak >nul
)

echo.
echo ══════════════════════════════════════════════════
echo   全部启动完成！
echo   PC: 5 个窗口 (Shard 0-4)
echo   Extra: 8 个窗口 (Shard 0-7)
echo   总计: 13 个采集窗口
echo.
echo   每个窗口都有实时输出，你可以直接看到采集过程
echo   关键: 用了 python -u 禁用输出缓冲
echo ══════════════════════════════════════════════════
echo.

echo 是否同时启动监控面板? (按任意键启动, 关闭此窗口跳过)
pause >nul
start "R6-Monitor" cmd /c "chcp 65001 >nul & title R6 实时监控面板 & cd /d %~dp0 & python -u live_monitor.py & pause"
