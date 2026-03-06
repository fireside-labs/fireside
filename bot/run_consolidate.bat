@echo off
:: OpenClaw Dream Consolidation — runs at 2 AM via Task Scheduler
:: Circadian contract: consolidate mortal memories, write eigen-memories, archive originals
cd /d "C:\Users\Jorda\.openclaw\workspace\bot\bot"
"C:\Users\Jorda\AppData\Local\Programs\Python\Python312\python.exe" war_room\consolidate.py >> "%~dp0logs\consolidate.log" 2>&1
