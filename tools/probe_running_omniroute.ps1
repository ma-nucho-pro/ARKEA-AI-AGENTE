$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http

$key = $env:ARKEA_E2E_API_KEY
if (-not $key) { throw "ARKEA_E2E_API_KEY no está definida" }

$client = [Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromSeconds(75)

function Read-BoundedBody($Response, [int]$Seconds) {
  $task = $Response.Content.ReadAsStringAsync()
  if (-not $task.Wait([TimeSpan]::FromSeconds($Seconds))) {
    throw "El cuerpo HTTP no finalizó dentro del límite"
  }
  return $task.GetAwaiter().GetResult()
}

function Send-WithKey($Method, [string]$Url, [string]$Json = "") {
  $request = [Net.Http.HttpRequestMessage]::new(
    [Net.Http.HttpMethod]$Method,
    [Uri]$Url
  )
  $request.Headers.Authorization = [Net.Http.Headers.AuthenticationHeaderValue]::new(
    "Bearer",
    $key
  )
  if ($Json) {
    $request.Content = [Net.Http.StringContent]::new(
      $Json,
      [Text.Encoding]::UTF8,
      "application/json"
    )
  }
  return $client.SendAsync(
    $request,
    [Net.Http.HttpCompletionOption]::ResponseHeadersRead
  ).GetAwaiter().GetResult()
}

try {
  $health = $client.GetAsync(
    "http://127.0.0.1:20128/api/monitoring/health"
  ).GetAwaiter().GetResult()
  $healthData = ConvertFrom-Json (Read-BoundedBody $health 10)

  $unauthenticated = $client.GetAsync(
    "http://127.0.0.1:20128/v1/models"
  ).GetAwaiter().GetResult()

  $models = Send-WithKey `
    ([Net.Http.HttpMethod]::Get) `
    "http://127.0.0.1:20128/v1/models"
  $modelsData = ConvertFrom-Json (Read-BoundedBody $models 30)

  $chatJson = @{
    model = "auto"
    messages = @(@{role = "user"; content = "Responde únicamente: ARKEA_E2E_OK"})
    max_tokens = 24
    temperature = 0
    stream = $false
  } | ConvertTo-Json -Depth 8 -Compress
  $chat = Send-WithKey `
    ([Net.Http.HttpMethod]::Post) `
    "http://127.0.0.1:20128/v1/chat/completions" `
    $chatJson
  $chatBody = Read-BoundedBody $chat 60
  try { $chatData = ConvertFrom-Json $chatBody } catch { $chatData = $null }

  [ordered]@{
    health_status = [int]$health.StatusCode
    reported_version = $healthData.version
    models_without_key = [int]$unauthenticated.StatusCode
    models_with_key = [int]$models.StatusCode
    models_count = @($modelsData.data).Count
    chat_status = [int]$chat.StatusCode
    chat_has_choices = [bool]($chatData -and $chatData.choices)
    chat_error_class = if ($chatData -and $chatData.error) {
      $chatData.error.code
    } else {
      ""
    }
    chat_decision_header_present = $chat.Headers.Contains("X-OmniRoute-Decision")
  } | ConvertTo-Json -Depth 5
} finally {
  $client.Dispose()
}
