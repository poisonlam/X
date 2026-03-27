@echo off
chcp 65001 >nul 2>&1
title R6 数据采集 - 实时监控面板
color 0A
echo ╔══════════════════════════════════════════════════════════╗
echo ║     R6 Siege 数据采集实时监控面板                       ║
echo ║     按 Ctrl+C 退出                                     ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
cd /d "%~dp0"
python -u live_monitor.py
pause
