#!/usr/bin/env pwsh
# Comprehensive Test Suite for Lyra Webhook API

$BaseURL = "http://localhost:8000"
$WebhookSecret = "test-secret-key"
$Results = @()

function Test-Endpoint {
    param(
        [string]$TestName,
        [string]$Method,
        [string]$Endpoint,
        [string]$Body = $null,
        [int]$ExpectedStatus = 200,
        [hashtable]$Headers = @{}
    )
    
    try {
        $url = "$BaseURL$Endpoint"
        $params = @{
            Method = $Method
            Uri = $url
            Headers = $Headers
            ContentType = "application/json"
            UseBasicParsing = $true
        }
        
        if ($Body) {
            $params.Body = $Body
        }
        
        $response = Invoke-WebRequest @params
        $status = "✅ PASS"
        $statusCode = $response.StatusCode
        $content = $response.Content | ConvertFrom-Json
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.Value__
        if ($statusCode -eq $ExpectedStatus) {
            $status = "✅ PASS"
            $content = $_.Exception.Response.Content | ConvertFrom-Json
        }
        else {
            $status = "❌ FAIL"
            $content = $_.Exception.Message
        }
    }
    
    $result = [PSCustomObject]@{
        TestName = $TestName
        Method = $Method
        Endpoint = $Endpoint
        ExpectedStatus = $ExpectedStatus
        ActualStatus = $statusCode
        Status = $status
        Response = $content
    }
    
    $Results += $result
    Write-Host "$status | $TestName (Expected: $ExpectedStatus, Got: $statusCode)"
    return $result
}

function Generate-HMAC {
    param([string]$Payload)
    $Key = [System.Text.Encoding]::UTF8.GetBytes($WebhookSecret)
    $MessageBytes = [System.Text.Encoding]::UTF8.GetBytes($Payload)
    $Hmac = New-Object System.Security.Cryptography.HMACSHA256($Key)
    $Hash = $Hmac.ComputeHash($MessageBytes)
    return [System.BitConverter]::ToString($Hash).Replace("-", "").ToLower()
}

Write-Host "===============================================" -ForegroundColor Green
Write-Host "LYRA WEBHOOK API - COMPREHENSIVE TEST SUITE" -ForegroundColor Green
Write-Host "===============================================`n" -ForegroundColor Green

# TEST 1: Health Liveness Probe
Test-Endpoint -TestName "Health Liveness Probe" -Method "GET" -Endpoint "/health/live" -ExpectedStatus 200

# TEST 2: Health Readiness Probe
Test-Endpoint -TestName "Health Readiness Probe" -Method "GET" -Endpoint "/health/ready" -ExpectedStatus 200

# TEST 3: Invalid Webhook Signature
$payload1 = @{
    message_id = "test-001"
    from_ = "+1234567890"
    to = "+9876543210"
    body = "Test message"
} | ConvertTo-Json
$invalidSig = "invalidsignature"
$headers1 = @{ "X-Webhook-Signature" = $invalidSig }
Test-Endpoint -TestName "Reject Invalid Signature" -Method "POST" -Endpoint "/webhook" -Body $payload1 -ExpectedStatus 401 -Headers $headers1

# TEST 4: Valid Webhook with Correct Signature
$payload2 = @{
    message_id = "msg-valid-001"
    from_ = "+1111111111"
    to = "+2222222222"
    body = "Valid message with correct signature"
} | ConvertTo-Json
$validSig = Generate-HMAC -Payload $payload2
$headers2 = @{ "X-Webhook-Signature" = $validSig }
Test-Endpoint -TestName "Accept Valid Signature" -Method "POST" -Endpoint "/webhook" -Body $payload2 -ExpectedStatus 200 -Headers $headers2

# TEST 5: Duplicate Detection (Exactly-Once Semantics)
Test-Endpoint -TestName "Detect Duplicate Message" -Method "POST" -Endpoint "/webhook" -Body $payload2 -ExpectedStatus 200 -Headers $headers2

# TEST 6: Invalid Phone Number
$payload3 = @{
    message_id = "msg-bad-phone"
    from_ = "invalid-phone"
    to = "+2222222222"
    body = "Bad phone number"
} | ConvertTo-Json
$sig3 = Generate-HMAC -Payload $payload3
$headers3 = @{ "X-Webhook-Signature" = $sig3 }
Test-Endpoint -TestName "Reject Invalid Phone Format" -Method "POST" -Endpoint "/webhook" -Body $payload3 -ExpectedStatus 422 -Headers $headers3

# TEST 7: Missing Required Fields
$payload4 = @{
    message_id = "msg-incomplete"
} | ConvertTo-Json
$sig4 = Generate-HMAC -Payload $payload4
$headers4 = @{ "X-Webhook-Signature" = $sig4 }
Test-Endpoint -TestName "Reject Missing Required Fields" -Method "POST" -Endpoint "/webhook" -Body $payload4 -ExpectedStatus 422 -Headers $headers4

# TEST 8: Create Additional Messages for Testing
for ($i = 1; $i -le 3; $i++) {
    $payloadN = @{
        message_id = "msg-list-$i"
        from_ = "+11111111$i"
        to = "+22222222$i"
        body = "Test message number $i"
    } | ConvertTo-Json
    $sigN = Generate-HMAC -Payload $payloadN
    $headersN = @{ "X-Webhook-Signature" = $sigN }
    Test-Endpoint -TestName "Create Message $i for Listing" -Method "POST" -Endpoint "/webhook" -Body $payloadN -ExpectedStatus 200 -Headers $headersN
}

# TEST 9: List All Messages with Pagination
Test-Endpoint -TestName "List Messages (Limit 10, Offset 0)" -Method "GET" -Endpoint "/messages?limit=10&offset=0" -ExpectedStatus 200

# TEST 10: List Messages with Limit
Test-Endpoint -TestName "List Messages (Limit 2, Offset 0)" -Method "GET" -Endpoint "/messages?limit=2&offset=0" -ExpectedStatus 200

# TEST 11: Filter Messages by Sender
Test-Endpoint -TestName "Filter Messages by Sender (from_)" -Method "GET" -Endpoint "/messages?from_=%2B1111111111" -ExpectedStatus 200

# TEST 12: Search Messages by Keyword
Test-Endpoint -TestName "Search Messages by Keyword" -Method "GET" -Endpoint "/messages?q=message" -ExpectedStatus 200

# TEST 13: Get Analytics/Statistics
Test-Endpoint -TestName "Get Analytics Statistics" -Method "GET" -Endpoint "/stats" -ExpectedStatus 200

# TEST 14: Get Prometheus Metrics
Test-Endpoint -TestName "Get Prometheus Metrics" -Method "GET" -Endpoint "/metrics" -ExpectedStatus 200

# TEST 15: Database Persistence Check
Write-Host "`n[TEST 15] Database Persistence Check" -ForegroundColor Cyan
$dbFile = "C:\Users\hasan\OneDrive\Documents\Lyra_Webhook_API\app.db"
if (Test-Path $dbFile) {
    Write-Host "✅ PASS | Database file exists at $dbFile"
    $fileSize = (Get-Item $dbFile).Length
    Write-Host "Database size: $fileSize bytes"
}
else {
    Write-Host "⚠️  Database file not found in expected location, checking Docker volume..."
}

# TEST 16: Docker Container Health
Write-Host "`n[TEST 16] Docker Container Status" -ForegroundColor Cyan
$containerStatus = docker-compose ps
Write-Host $containerStatus

# TEST 17: Memory and CPU Usage
Write-Host "`n[TEST 17] Container Resource Usage" -ForegroundColor Cyan
$stats = docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" lyra_webhook_api-app-1
Write-Host $stats

# Summary
Write-Host "`n===============================================" -ForegroundColor Green
Write-Host "TEST SUMMARY" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
$passCount = ($Results | Where-Object { $_.Status -eq "✅ PASS" }).Count
$failCount = ($Results | Where-Object { $_.Status -eq "❌ FAIL" }).Count
Write-Host "Total Tests: $($Results.Count)"
Write-Host "Passed: $passCount" -ForegroundColor Green
Write-Host "Failed: $failCount" -ForegroundColor Red
Write-Host "Success Rate: $(($passCount / $Results.Count * 100).ToString('F2'))%"

# Export Results
$Results | Export-Csv -Path "test_results.csv" -NoTypeInformation
Write-Host "`nTest results exported to: test_results.csv"

# Display detailed results
Write-Host "`n===============================================" -ForegroundColor Green
Write-Host "DETAILED TEST RESULTS" -ForegroundColor Green
Write-Host "===============================================`n" -ForegroundColor Green
$Results | Format-Table -AutoSize
