$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptsDir = Join-Path $projectRoot ".venv\Scripts"
$uvicornExe = Join-Path $scriptsDir "uvicorn.exe"
$streamlitExe = Join-Path $scriptsDir "streamlit.exe"
$secretPath = Join-Path $projectRoot ".streamlit\secrets.toml"
$defaultWebSocketUrl = "ws://localhost:8765/ws"
$streamlitPort = 8501

if (-not (Test-Path $uvicornExe)) {
    throw "Uvicorn est introuvable. Verifiez que l'environnement virtuel est installe dans .venv et que les dependances sont installees."
}

if (-not (Test-Path $streamlitExe)) {
    throw "Streamlit est introuvable. Verifiez que l'environnement virtuel est installe dans .venv et que les dependances sont installees."
}

$websocketUrl = $defaultWebSocketUrl

if (Test-Path $secretPath) {
    $secretContent = Get-Content -Path $secretPath -Raw
    if ($secretContent -match 'websocket_url\s*=\s*"([^"]+)"') {
        $websocketUrl = $Matches[1]
    }
}

try {
    $websocketUri = [Uri]$websocketUrl
    $websocketPort = if ($websocketUri.Port -gt 0) { $websocketUri.Port } else { 8765 }
}
catch {
    throw "L'URL WebSocket '$websocketUrl' est invalide dans .streamlit/secrets.toml."
}

$escapedProjectRoot = $projectRoot.Replace("'", "''")
$escapedUvicornExe = $uvicornExe.Replace("'", "''")
$escapedStreamlitExe = $streamlitExe.Replace("'", "''")

$uvicornCommand = "Set-Location '$escapedProjectRoot'; & '$escapedUvicornExe' websocket_server:app --host 0.0.0.0 --port $websocketPort"
$streamlitCommand = "Set-Location '$escapedProjectRoot'; & '$escapedStreamlitExe' run app.py --server.port $streamlitPort"

Write-Host "WebSocket URL configuree: $websocketUrl"
Write-Host "Lancement d'Uvicorn sur le port $websocketPort"
Write-Host "Lancement de Streamlit sur le port $streamlitPort"

Start-Process -FilePath "powershell.exe" -WorkingDirectory $projectRoot -ArgumentList @(
    "-NoExit",
    "-Command",
    $uvicornCommand
)

Start-Process -FilePath "powershell.exe" -WorkingDirectory $projectRoot -ArgumentList @(
    "-NoExit",
    "-Command",
    $streamlitCommand
)