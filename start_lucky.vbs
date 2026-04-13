Set WshShell = CreateObject("WScript.Shell")
strPath = Wscript.ScriptFullName
Set objFSO = CreateObject("Scripting.FileSystemObject")
strFolder = objFSO.GetParentFolderName(objFSO.GetFile(strPath))
WshShell.CurrentDirectory = strFolder
WshShell.Run "powershell -Command ""Start-Process pythonw.exe -ArgumentList 'main.py' -Verb RunAs -WorkingDirectory '" & strFolder & "'""", 0, False
