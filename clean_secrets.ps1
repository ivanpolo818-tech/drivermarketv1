
# Script para limpiar secretos de todos los archivos
$googleClientId = "812955308663-htj55eqsni45mvhtl10gp0bioaoiptkg.apps.googleusercontent.com"
$googleClientSecret = "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"

Get-ChildItem -Path "." -File -Recurse -Include "*.py", "*.md", ".env" | ForEach-Object {
    Write-Host "Procesando: $($_.FullName)"
    $content = Get-Content $_.FullName -Raw
    $modified = $false
    
    if ($content -like "*$googleClientId*") {
        $content = $content -replace [regex]::Escape($googleClientId), "[REDACTED_GOOGLE_CLIENT_ID]"
        $modified = $true
    }
    
    if ($content -like "*$googleClientSecret*") {
        $content = $content -replace [regex]::Escape($googleClientSecret), "[REDACTED_GOOGLE_CLIENT_SECRET]"
        $modified = $true
    }
    
    if ($modified) {
        Set-Content $_.FullName $content -Encoding UTF8
        Write-Host "  ✓ Secretos reemplazados"
    }
}
Write-Host "Completado"
