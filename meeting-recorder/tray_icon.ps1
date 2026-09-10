param(
    [string]$lockFile = ""
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

if (-not $lockFile) {
    exit
}

# Wait up to 5 seconds for the lock file to appear (in case of delay in file creation)
for ($i = 0; $i -lt 10; $i++) {
    if (Test-Path $lockFile) {
        break
    }
    Start-Sleep -Milliseconds 500
}

if (-not (Test-Path $lockFile)) {
    exit
}

$icon = New-Object System.Windows.Forms.NotifyIcon
$icon.Icon = [System.Drawing.SystemIcons]::Information
$icon.Text = "MOM is underway..."
$icon.Visible = $true

# Show balloon tip on start
$icon.BalloonTipTitle = "Meeting Note-Taker"
$icon.BalloonTipText = "Recording stopped. MOM is underway in the background..."
$icon.ShowBalloonTip(3000)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 1000
$timer.Add_Tick({
    if (-not (Test-Path $lockFile)) {
        $timer.Stop()
        $icon.Visible = $false
        $icon.Dispose()
        [System.Windows.Forms.Application]::Exit()
    }
})

$timer.Start()

[System.Windows.Forms.Application]::Run()
