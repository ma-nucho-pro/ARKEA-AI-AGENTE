$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http

$exe = Join-Path $env:LOCALAPPDATA "Programs\OmniRoute\OmniRoute.exe"
if (-not (Test-Path -LiteralPath $exe)) {
  throw "OmniRoute 3.8.49 no está instalado"
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$runDir = Join-Path $root ("_omni_auth_e2e_" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
function New-RandomValue([int]$Length) {
  $bytes = New-Object byte[] $Length
  $rng.GetBytes($bytes)
  return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

$storageBytes = New-Object byte[] 32
$rng.GetBytes($storageBytes)
$key = if ($env:ARKEA_E2E_API_KEY) {
  $env:ARKEA_E2E_API_KEY
} else {
  "sk-e2e-" + (New-RandomValue 32)
}
$psi = New-Object Diagnostics.ProcessStartInfo
$psi.FileName = $exe
$psi.Arguments = "--headless"
$psi.WorkingDirectory = Split-Path -Parent $exe
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden

$environment = @{
  OMNIROUTE_HEADLESS = "true"
  OMNIROUTE_SERVER_HOST = "127.0.0.1"
  HOST = "127.0.0.1"
  HOSTNAME = "127.0.0.1"
  OMNIROUTE_PORT = "20128"
  PORT = "20128"
  LIVE_WS_PORT = "20129"
  REQUIRE_API_KEY = "true"
  ALLOW_API_KEY_REVEAL = "false"
  OMNIROUTE_API_KEY = $key
  ROUTER_API_KEY = $key
  JWT_SECRET = New-RandomValue 48
  API_KEY_SECRET = New-RandomValue 32
  STORAGE_ENCRYPTION_KEY = ([BitConverter]::ToString($storageBytes)).Replace("-", "").ToLowerInvariant()
  INITIAL_PASSWORD = New-RandomValue 18
  DATA_DIR = $runDir
  ARENA_ELO_SYNC_ENABLED = "false"
  OMNIROUTE_MEMORY_MB = "4096"
  NODE_OPTIONS = "--max-old-space-size=4096"
  OMNIROUTE_ALLOW_PRIVATE_PROVIDER_URLS = "true"
}
foreach ($item in $environment.GetEnumerator()) {
  $psi.EnvironmentVariables[$item.Key] = $item.Value
}

$startedAt = Get-Date
$process = [Diagnostics.Process]::Start($psi)
$client = [Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromSeconds(90)
function Read-ResponseBody($Response, [int]$TimeoutSeconds = 30) {
  $task = $Response.Content.ReadAsStringAsync()
  if (-not $task.Wait([TimeSpan]::FromSeconds($TimeoutSeconds))) {
    throw "La respuesta HTTP no cerró su cuerpo dentro del tiempo permitido"
  }
  return $task.GetAwaiter().GetResult()
}
$result = [ordered]@{
  validated_at = (Get-Date).ToString("o")
  ready = $false
}

try {
  $deadline = (Get-Date).AddMinutes(3)
  do {
    Start-Sleep -Milliseconds 1500
    try {
      $health = $client.GetAsync(
        "http://127.0.0.1:20128/api/monitoring/health"
      ).GetAwaiter().GetResult()
      $healthBody = Read-ResponseBody $health 10
      if (
        [int]$health.StatusCode -eq 200 -and
        (ConvertFrom-Json $healthBody).status -eq "healthy" -and
        (ConvertFrom-Json $healthBody).version -eq "3.8.49"
      ) {
        $result.ready = $true
        break
      }
    } catch {}
  } while ((Get-Date) -lt $deadline)

  if (-not $result.ready) {
    throw "OmniRoute no estuvo listo para E2E autenticado"
  }

  $unauthenticated = $client.GetAsync(
    "http://127.0.0.1:20128/v1/models"
  ).GetAwaiter().GetResult()
  $result.models_without_key = [int]$unauthenticated.StatusCode

  $result.reported_version = "3.8.49"

  $modelsRequest = [Net.Http.HttpRequestMessage]::new(
    [Net.Http.HttpMethod]::Get,
    [Uri]"http://127.0.0.1:20128/v1/models"
  )
  $modelsRequest.Headers.Authorization = [Net.Http.Headers.AuthenticationHeaderValue]::new(
    "Bearer",
    $key
  )
  $modelsResponse = $client.SendAsync($modelsRequest).GetAwaiter().GetResult()
  $modelsBody = Read-ResponseBody $modelsResponse 30
  $result.models_with_key = [int]$modelsResponse.StatusCode
  try {
    $result.models_count = @((ConvertFrom-Json $modelsBody).data).Count
  } catch {
    $result.models_count = 0
  }

  $chatPayload = @{
    model = "auto"
    messages = @(@{role = "user"; content = "Responde únicamente: ARKEA_E2E_OK"})
    max_tokens = 24
    temperature = 0
    stream = $false
  } | ConvertTo-Json -Depth 8 -Compress
  $chatRequest = [Net.Http.HttpRequestMessage]::new(
    [Net.Http.HttpMethod]::Post,
    [Uri]"http://127.0.0.1:20128/v1/chat/completions"
  )
  $chatRequest.Headers.Authorization = [Net.Http.Headers.AuthenticationHeaderValue]::new(
    "Bearer",
    $key
  )
  $chatRequest.Content = [Net.Http.StringContent]::new(
    $chatPayload,
    [Text.Encoding]::UTF8,
    "application/json"
  )
  $chatResponse = $client.SendAsync($chatRequest).GetAwaiter().GetResult()
  $chatBody = Read-ResponseBody $chatResponse 60
  $result.chat_status = [int]$chatResponse.StatusCode
  $result.chat_has_choices = $chatBody -match '"choices"'
  if ([int]$chatResponse.StatusCode -ge 400) {
    try {
      $result.chat_error_class = (ConvertFrom-Json $chatBody).error.code
    } catch {
      $result.chat_error_class = "http_error"
    }
  } else {
    $result.chat_error_class = ""
  }
  $result.decision_header_present = $chatResponse.Headers.Contains("X-OmniRoute-Decision")

  $result | ConvertTo-Json -Depth 6
} finally {
  $client.Dispose()
  $rng.Dispose()
  Get-Process -Name "OmniRoute" -ErrorAction SilentlyContinue |
    Where-Object {
      $_.StartTime -ge $startedAt.AddSeconds(-2) -and
      $_.Path -eq $exe
    } |
    Stop-Process -Force -ErrorAction SilentlyContinue
  if (-not $process.HasExited) {
    $process.Kill()
  }
}
