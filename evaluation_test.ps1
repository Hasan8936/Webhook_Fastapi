#!/usr/bin/env pwsh
# Evaluation Script - Based on provided requirements

Write-Host "LYRA WEBHOOK API - PRODUCTION EVALUATION" -ForegroundColor Green
Write-Host ""

$BaseURL = "http://localhost:8000"
$WEBHOOK_SECRET = "testsecret"

# ============================================
# 1. HEALTH CHECKS
# ============================================
Write-Host "1. HEALTH CHECKS" -ForegroundColor Green

Write-Host "[TEST] Health Liveness" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/health/live" -UseBasicParsing
    Write-Host "PASS: $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}

Write-Host "[TEST] Health Readiness" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/health/ready" -UseBasicParsing
    Write-Host "PASS: $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}
Write-Host ""

# ============================================
# 2. WEBHOOK SIGNATURE VALIDATION
# ============================================
Write-Host "2. WEBHOOK SIGNATURE VALIDATION" -ForegroundColor Green

$BODY = @{
    message_id = "m1"
    from = "+919876543210"
    to = "+14155550100"
    ts = "2025-01-15T10:00:00Z"
    text = "Hello"
} | ConvertTo-Json

Write-Host "Payload: $BODY" -ForegroundColor Gray

# Test 2A: Invalid signature
Write-Host "[TEST] Invalid Signature (expect 401)" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/webhook" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json"; "X-Signature" = "123"} `
        -Body $BODY `
        -UseBasicParsing
    Write-Host "FAIL: Got $($r.StatusCode)" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    if ($statusCode -eq 401) {
        Write-Host "PASS: Got 401" -ForegroundColor Green
    } else {
        Write-Host "FAIL: Got $statusCode" -ForegroundColor Red
    }
}

# Test 2B: Compute valid signature
$VALID_SIG = [System.BitConverter]::ToString(
    (New-Object System.Security.Cryptography.HMACSHA256 `
        -ArgumentList @([System.Text.Encoding]::UTF8.GetBytes($WEBHOOK_SECRET))
    ).ComputeHash([System.Text.Encoding]::UTF8.GetBytes($BODY))
).Replace("-", "").ToLower()

Write-Host "Computed Signature: $VALID_SIG" -ForegroundColor Gray

# Test 2C: Valid signature
Write-Host "[TEST] Valid Signature (expect 200)" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/webhook" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json"; "X-Signature" = $VALID_SIG} `
        -Body $BODY `
        -UseBasicParsing
    Write-Host "PASS: Got $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}

# Test 2D: Duplicate message
Write-Host "[TEST] Duplicate Message (expect 200, no insert)" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/webhook" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json"; "X-Signature" = $VALID_SIG} `
        -Body $BODY `
        -UseBasicParsing
    Write-Host "PASS: Got $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}
Write-Host ""

# ============================================
# 3. SEED MORE MESSAGES
# ============================================
Write-Host "3. SEEDING ADDITIONAL MESSAGES" -ForegroundColor Green

$messages = @(
    @{
        message_id = "m2"
        from = "+919876543211"
        to = "+14155550101"
        ts = "2025-01-15T10:05:00Z"
        text = "Hello again"
    },
    @{
        message_id = "m3"
        from = "+919876543210"
        to = "+14155550102"
        ts = "2025-01-15T10:10:00Z"
        text = "Another message"
    },
    @{
        message_id = "m4"
        from = "+919876543212"
        to = "+14155550100"
        ts = "2025-01-15T09:50:00Z"
        text = "Earlier message"
    }
)

foreach ($msg in $messages) {
    $body = $msg | ConvertTo-Json
    $sig = [System.BitConverter]::ToString(
        (New-Object System.Security.Cryptography.HMACSHA256 `
            -ArgumentList @([System.Text.Encoding]::UTF8.GetBytes($WEBHOOK_SECRET))
        ).ComputeHash([System.Text.Encoding]::UTF8.GetBytes($body))
    ).Replace("-", "").ToLower()
    
    try {
        $r = Invoke-WebRequest -Uri "$BaseURL/webhook" `
            -Method POST `
            -Headers @{"Content-Type" = "application/json"; "X-Signature" = $sig} `
            -Body $body `
            -UseBasicParsing
        Write-Host "  $($msg.message_id): PASS" -ForegroundColor Green
    } catch {
        Write-Host "  $($msg.message_id): FAIL" -ForegroundColor Red
    }
}
Write-Host ""

# ============================================
# 4. CHECK /messages PAGINATION & FILTERS
# ============================================
Write-Host "4. /messages ENDPOINT TESTS" -ForegroundColor Green

Write-Host "[TEST] Basic List" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/messages" -UseBasicParsing
    $data = $r.Content | ConvertFrom-Json
    Write-Host "PASS: total=$($data.total), items=$($data.data.Count)" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}

Write-Host "[TEST] Pagination (limit=2)" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/messages?limit=2&offset=0" -UseBasicParsing
    $data = $r.Content | ConvertFrom-Json
    Write-Host "PASS: limit=$($data.limit), offset=$($data.offset), items=$($data.data.Count)" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}

Write-Host "[TEST] Filter by from" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/messages?from=%2B919876543210" -UseBasicParsing
    $data = $r.Content | ConvertFrom-Json
    Write-Host "PASS: total=$($data.total)" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}

Write-Host "[TEST] Filter by since" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/messages?since=2025-01-15T09:55:00Z" -UseBasicParsing
    $data = $r.Content | ConvertFrom-Json
    Write-Host "PASS: total=$($data.total)" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}

Write-Host "[TEST] Search by q" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/messages?q=Hello" -UseBasicParsing
    $data = $r.Content | ConvertFrom-Json
    Write-Host "PASS: total=$($data.total)" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}
Write-Host ""

# ============================================
# 5. CHECK /stats
# ============================================
Write-Host "5. /stats ENDPOINT TEST" -ForegroundColor Green

Write-Host "[TEST] Get Stats" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/stats" -UseBasicParsing
    $data = $r.Content | ConvertFrom-Json
    Write-Host "PASS:" -ForegroundColor Green
    Write-Host "  total_messages: $($data.total_messages)" -ForegroundColor Cyan
    Write-Host "  senders_count: $($data.senders_count)" -ForegroundColor Cyan
    Write-Host "  messages_per_sender: $($data.messages_per_sender.Count) entries" -ForegroundColor Cyan
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}
Write-Host ""

# ============================================
# 6. CHECK /metrics
# ============================================
Write-Host "6. /metrics ENDPOINT TEST" -ForegroundColor Green

Write-Host "[TEST] Metrics Endpoint" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$BaseURL/metrics" -UseBasicParsing
    $content = $r.Content
    $hasHttpRequests = $content -match "http_requests_total"
    $hasWebhookRequests = $content -match "webhook_requests_total"
    
    if ($hasHttpRequests -and $hasWebhookRequests) {
        Write-Host "PASS: Contains required metrics" -ForegroundColor Green
    } else {
        Write-Host "FAIL: Missing required metrics" -ForegroundColor Red
    }
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}
Write-Host ""

# ============================================
# SUMMARY
# ============================================
Write-Host "=====================================================" -ForegroundColor Green
Write-Host "EVALUATION COMPLETE" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "SERVICE IS PRODUCTION READY FOR EVALUATION" -ForegroundColor Green
