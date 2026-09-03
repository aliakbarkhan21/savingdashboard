' Starts Loot Ledger with no console window.
'
' The dashboard is a local web server: something has to stay running to serve
' the page, exactly like a program stays open while you use it. This runs that
' server hidden. Output goes to lootledger.log, so a failure is not silent
' just because there is no window to look at.
'
' It always stops an existing server before starting a new one. Streamlit
' refuses to bind a port that is already in use, so without this a second
' launch would quietly exit and the browser would reconnect to the OLD server
' — still running the code from whenever it was started. Any edit to the app
' would look like it had not taken effect. Restarting costs a few seconds and
' guarantees you are always on the current version.
'
' Use "Stop Loot Ledger.bat" to shut it down, since there is no window to close.

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

' This script's own folder, so it still works if the project is moved or run
' from a USB stick. The app is read from here every time — nothing is copied.
here = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = here

' Stop whatever is already on 8501, if anything. 0 = hidden, True = wait.
sh.Run "cmd /c for /f ""tokens=5"" %p in ('netstat -ano ^| findstr "":8501"" ^| findstr ""LISTENING""') do taskkill /PID %p /F", 0, True
WScript.Sleep 1500

' --server.headless true stops Streamlit opening its own browser tab the
' moment it binds the port — without it, this script's own open below landed
' as a *second* tab a few seconds later, on top of Streamlit's automatic one.
' 0 = hidden window, False = do not wait for it to finish
sh.Run "cmd /c python -m streamlit run app.py --server.headless true > lootledger.log 2>&1", 0, False

' Give the server a moment to bind the port before the browser asks for it.
WScript.Sleep 8000
sh.Run "http://localhost:8501", 1, False
