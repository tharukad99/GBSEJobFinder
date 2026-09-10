@echo off
echo Starting UK Software Engineering Job Finder (Unified Single App)...
echo Database: bsync (job schema) on Azure MSSQL Server
echo.
echo =======================================================
echo Application UI:    http://127.0.0.1:8000
echo Swagger API Docs:  http://127.0.0.1:8000/docs
echo Ready for Azure App Service single-instance hosting!
echo =======================================================
echo.
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

