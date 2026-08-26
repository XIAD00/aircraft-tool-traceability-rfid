param(
    [switch]$Compile
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$sketchPath = Join-Path $PSScriptRoot "RFID_Tool_Tracking\RFID_Tool_Tracking.ino"
$buildPath = Join-Path $workspaceRoot ".build\arduino-intellisense"
$databasePath = Join-Path $buildPath "compile_commands.json"
$fqbn = "esp32:esp32:esp32"

$cliCommand = Get-Command "arduino-cli" -ErrorAction SilentlyContinue
$cliCandidates = @()

if ($cliCommand) {
    $cliCandidates += $cliCommand.Source
}

$cliCandidates += Join-Path $env:ProgramFiles "Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
$arduinoCli = $cliCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $arduinoCli) {
    throw "Arduino CLI was not found. Install Arduino IDE 2 or add arduino-cli to PATH."
}

$compileArguments = @(
    "compile"
    "--fqbn", $fqbn
    "--build-path", $buildPath
)

if (-not $Compile) {
    $compileArguments += "--only-compilation-database"
}

$compileArguments += Split-Path -Parent $sketchPath

& $arduinoCli @compileArguments

if ($LASTEXITCODE -ne 0) {
    throw "Arduino CLI failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path -LiteralPath $databasePath)) {
    throw "Arduino CLI did not create $databasePath."
}

# Map Arduino's generated file back to the sketch opened in VS Code.
$database = Get-Content -Raw -LiteralPath $databasePath | ConvertFrom-Json
$generatedEntry = $database | Where-Object { $_.file -like "*.ino.cpp" } | Select-Object -First 1

if (-not $generatedEntry) {
    throw "The compilation database has no generated .ino.cpp entry."
}

# Expand the ESP32 include list so the VS Code C/C++ extension can read it.
foreach ($databaseEntry in $database) {
    $arguments = [System.Collections.Generic.List[string]]::new()
    foreach ($argument in $databaseEntry.arguments) {
        $arguments.Add($argument)
    }

    $prefixIndex = $arguments.IndexOf("-iprefix")
    if ($prefixIndex -ge 0 -and $prefixIndex + 1 -lt $arguments.Count) {
        $includePrefix = $arguments[$prefixIndex + 1]
        $responseIndex = -1

        for ($index = 0; $index -lt $arguments.Count; $index++) {
            if ($arguments[$index] -like "@*/flags/includes") {
                $responseIndex = $index
                break
            }
        }

        if ($responseIndex -ge 0) {
            $responsePath = $arguments[$responseIndex].Substring(1)
            $responseTokens = (Get-Content -Raw -LiteralPath $responsePath) -split "\s+" |
                Where-Object { $_ }
            $expandedIncludes = [System.Collections.Generic.List[string]]::new()

            for ($index = 0; $index -lt $responseTokens.Count; $index++) {
                if ($responseTokens[$index] -eq "-iwithprefixbefore" -and $index + 1 -lt $responseTokens.Count) {
                    $index++
                    $expandedIncludes.Add("-I" + (Join-Path $includePrefix $responseTokens[$index]))
                }
            }

            $arguments.RemoveAt($responseIndex)
            $arguments.InsertRange($responseIndex, $expandedIncludes)
            $databaseEntry.arguments = $arguments.ToArray()
        }
    }
}

$generatedSource = $generatedEntry.file
$resolvedSketchPath = (Resolve-Path -LiteralPath $sketchPath).Path
$generatedEntry.file = $resolvedSketchPath

for ($index = 0; $index -lt $generatedEntry.arguments.Count; $index++) {
    if ($generatedEntry.arguments[$index] -eq $generatedSource) {
        $generatedEntry.arguments[$index] = $resolvedSketchPath
    }
}

$database | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $databasePath -Encoding utf8

Write-Host "ESP32 IntelliSense database: $databasePath"
if (-not $Compile) {
    Write-Host "Run 'C/C++: Reset IntelliSense Database' if stale diagnostics remain."
}
