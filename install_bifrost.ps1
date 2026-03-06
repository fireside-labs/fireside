# install_bifrost.ps1
# Installs Bifrost as a scheduled task that auto-starts on logon.
# Run this once on each node (as admin for Set-ScheduledTask).

$python  = "C:\Users\Jorda\AppData\Local\Programs\Python\Python312\python.exe"
$script  = "C:\Users\Jorda\.openclaw\workspace\bot\bifrost.py"
$taskName = "Bifrost Bot"

# Remove old task if present
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action   = New-ScheduledTaskAction -Execute $python -Argument $script
$trigger  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -RestartCount 10 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Bifrost - inter-node Telegram approval bot"

Write-Host "Registered '$taskName'. Starting now..."
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 3

$info = Get-ScheduledTaskInfo -TaskName $taskName
Write-Host "LastResult: $($info.LastTaskResult)"
Write-Host "Done. Bifrost is running."
