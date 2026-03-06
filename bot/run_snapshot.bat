@echo off
:: OpenClaw Hydra Snapshot — runs every 6 hours via Task Scheduler
:: POSTs to local /snapshot to generate + push a permanent state snapshot
curl -s -X POST http://localhost:8765/snapshot -H "Content-Type: application/json" -d "{}" >> "%~dp0logs\hydra_snapshot.log" 2>&1
