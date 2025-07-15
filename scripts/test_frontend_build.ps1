# Frontend Docker Build Testing Script for Windows
# Tests the frontend build pipeline using Docker Compose

Write-Host "=== Testing Frontend Build Pipeline ===" -ForegroundColor Green

# Navigate to project root directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $scriptDir "..")

# Check if docker-compose is installed
try {
    docker-compose --version | Out-Null
}
catch {
    Write-Host "Error: docker-compose is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check if the frontend.Dockerfile exists
if (-not (Test-Path ".\docker\frontend.Dockerfile")) {
    Write-Host "Error: docker/frontend.Dockerfile not found" -ForegroundColor Red
    exit 1
}

# Check if the docker-compose.frontend.yml exists
if (-not (Test-Path ".\docker-compose.frontend.yml")) {
    Write-Host "Error: docker-compose.frontend.yml not found" -ForegroundColor Red
    exit 1
}

Write-Host "Running frontend build with Docker Compose..." -ForegroundColor Cyan

# Build the frontend service
try {
    docker-compose -f docker-compose.yml -f docker-compose.frontend.yml build frontend
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build exited with code $LASTEXITCODE"
    }
}
catch {
    Write-Host "Error: Frontend build failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Frontend build successful." -ForegroundColor Green

# Check for built assets
Write-Host "Checking for built assets..." -ForegroundColor Cyan
if (-not (Test-Path ".\app\static\dist")) {
    Write-Host "Warning: Built assets directory not found at .\app\static\dist" -ForegroundColor Yellow
}
else {
    $fileCount = (Get-ChildItem -Path ".\app\static\dist" -Recurse -File).Count
    Write-Host "Found $fileCount files in the dist directory" -ForegroundColor Green
}

# Test dev server mode (optional)
Write-Host "Would you like to test the development server? (y/n)" -ForegroundColor Cyan
$response = Read-Host
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "Starting development server (press Ctrl+C to stop)..." -ForegroundColor Yellow
    try {
        docker-compose -f docker-compose.yml -f docker-compose.frontend.yml up frontend
    }
    catch {
        Write-Host "Development server stopped: $_" -ForegroundColor Yellow
    }
}

Write-Host "Frontend build pipeline test completed successfully." -ForegroundColor Green
