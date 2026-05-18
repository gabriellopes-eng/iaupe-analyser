Set-Location "C:\Users\Elward\Repositorio IAUPE\iaupe-analyser\pipeline"

$pythonExe = "C:\Users\Elward\Repositorio IAUPE\iaupe-analyser\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python do ambiente virtual nao encontrado em: $pythonExe"
}

& $pythonExe ".\main.py" --source finep --run-reminders --reminder-steps 30,15,7
