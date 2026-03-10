# =============================================================================
# start_dynamodb_local.ps1 — Inicia o DynamoDB Local (sem Docker)
#
# Pré-requisitos:
#   - Java instalado (ex: Amazon Corretto ou OpenJDK)
#   - DynamoDB Local descompactado em C:\Users\$env:USERNAME\dynamodb_local_latest
#
# Uso:
#   .\scripts\start_dynamodb_local.ps1
#
# Após iniciar, configure o .env:
#   STORAGE_BACKEND=dynamodb
#   DYNAMODB_ENDPOINT_URL=http://localhost:8001
#   AWS_REGION=us-east-1
#
# Crie a tabela (apenas na primeira vez):
#   python scripts/setup_dynamodb_local.py
# =============================================================================

$DynamoPath = "$env:USERPROFILE\dynamodb_local_latest"
$Port       = 8001

# Localiza java.exe
$JavaExe = Get-Command "java" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $JavaExe) {
    # Fallback: busca nas instalações típicas
    $JavaExe = Get-ChildItem -Path "C:\Program Files\Microsoft\jdk*\bin\java.exe",
                                    "C:\Program Files\Amazon Corretto\*\bin\java.exe",
                                    "C:\Program Files\Eclipse Adoptium\*\bin\java.exe" `
               -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
}

if (-not $JavaExe) {
    Write-Error "Java não encontrado. Instale via: winget install Microsoft.OpenJDK.21"
    exit 1
}

Write-Host "Java: $JavaExe"
Write-Host "DynamoDB Local: $DynamoPath"
Write-Host "Porta: $Port"
Write-Host ""

# Mata instância anterior se existir
$existing = netstat -an 2>$null | Select-String ":$Port "
if ($existing) {
    Write-Host "[AVISO] Porta $Port já em uso. Encerrando processo Java anterior..."
    Get-Process -Name "java" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Inicia DynamoDB Local em background
$args = @(
    "-Djava.library.path=$DynamoPath\DynamoDBLocal_lib",
    "-jar", "$DynamoPath\DynamoDBLocal.jar",
    "-inMemory",
    "-sharedDb",
    "-port", "$Port"
)

$log    = "$env:USERPROFILE\dynamodb_local.log"
$logErr = "$env:USERPROFILE\dynamodb_local_err.log"

Start-Process -NoNewWindow -FilePath $JavaExe -ArgumentList $args `
    -RedirectStandardOutput $log -RedirectStandardError $logErr

Start-Sleep -Seconds 3

# Verifica se subiu
$listening = netstat -an 2>$null | Select-String ":$Port.*LISTENING"
if ($listening) {
    Write-Host "[OK] DynamoDB Local rodando na porta $Port"
    Write-Host ""
    Write-Host "Próximo passo — crie a tabela (apenas uma vez por sessão):"
    Write-Host "  python scripts/setup_dynamodb_local.py"
} else {
    Write-Error "DynamoDB Local não iniciou. Verifique: $logErr"
    Get-Content $logErr -ErrorAction SilentlyContinue | Select-Object -Last 10
    exit 1
}
