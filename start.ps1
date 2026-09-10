Write-Host "Starting UK Software Engineering Job Finder (Unified Single App)..." -ForegroundColor Cyan
Write-Host "Database: bsync (job schema) on Azure MSSQL Server" -ForegroundColor Gray
Write-Host ""
Write-Host "Application UI:    http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Swagger API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "Ready for single-instance Azure App Service hosting!" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

