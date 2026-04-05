Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & WScript.CreateObject("WScript.Shell").ExpandEnvironmentStrings("%USERPROFILE%\Documents\shopping_list_app_v4\start_shopping_app.bat") & Chr(34), 0
Set WshShell = Nothing
