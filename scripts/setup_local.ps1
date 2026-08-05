Param()
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Join-Path $ScriptDir ".."
$Venv = Join-Path $RepoRoot ".venv"

Write-Host "Creating virtual environment at $Venv"
python -m venv "$Venv"

Write-Host "Activating venv"
& "$Venv\Scripts\Activate.ps1"

Write-Host "Upgrading pip and installing requirements"
python -m pip install --upgrade pip
if (Test-Path -Path (Join-Path $RepoRoot "requirements.txt")) {
    pip install -r (Join-Path $RepoRoot "requirements.txt")
} else {
    Write-Host "requirements.txt not found in repo root; skipping requirements install"
}

Write-Host "Installing streamlit"
pip install streamlit

Write-Host "Setup completed. To run the Setup UI:"
Write-Host "  .\" + $Venv + "\Scripts\Activate.ps1"
Write-Host "  streamlit run tools/setup_ui.py"
