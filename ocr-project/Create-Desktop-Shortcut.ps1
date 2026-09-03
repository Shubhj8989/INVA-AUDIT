$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\INVA-AUDIT.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\Launch-INVA-AUDIT.vbs"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.Description = "INVA-AUDIT - Physical Inventory Verification System"
$Shortcut.Save()
Write-Host "[OK] INVA-AUDIT Desktop Shortcut created on Windows Desktop!"
