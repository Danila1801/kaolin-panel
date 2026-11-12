# Registers two scheduled tasks: morning board at 07:00, night clock at 23:00.
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $dir ".venv\Scripts\pythonw.exe"
$script = Join-Path $dir "morning.py"
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

$jobs = @(
    @{ Name = "pixel-morning push"; Arg = "push"; At = "07:00" },
    @{ Name = "pixel-morning night"; Arg = "night"; At = "23:00" }
)
foreach ($j in $jobs) {
    $action = New-ScheduledTaskAction -Execute $py -Argument "`"$script`" $($j.Arg)" -WorkingDirectory $dir
    $trigger = New-ScheduledTaskTrigger -Daily -At $j.At
    Register-ScheduledTask -TaskName $j.Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "registered: $($j.Name) at $($j.At)"
}
