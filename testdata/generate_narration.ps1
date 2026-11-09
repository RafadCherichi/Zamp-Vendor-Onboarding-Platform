$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$projectRoot = Split-Path -Parent $PSScriptRoot
$scenes = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'demo_script.json') -Raw | ConvertFrom-Json
$outputDirectory = Join-Path $projectRoot 'grade_evidence/narration'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $speaker.Rate = 1
    for ($sceneIndex = 0; $sceneIndex -lt $scenes.Count; $sceneIndex++) {
        $speaker.SetOutputToWaveFile((Join-Path $outputDirectory "scene-$sceneIndex.wav"))
        $speaker.Speak($scenes[$sceneIndex].text)
        $speaker.SetOutputToNull()
    }
} finally {
    $speaker.Dispose()
}
Write-Output "Generated $($scenes.Count) narration segments."
