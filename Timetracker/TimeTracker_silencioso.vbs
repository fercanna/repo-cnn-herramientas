' Lanza TimeTracker sin dejar una ventana de consola abierta.
' Pensado para el acceso directo de escritorio.
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir
WshShell.Run "cmd /c """ & scriptDir & "\TimeTracker.bat""", 0, False
