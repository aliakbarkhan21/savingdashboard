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
' would look like it had not taken effect. Restarting costs a couple of seconds
' and guarantees you are always on the current version.
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
' Long enough for a killed process to release the port, and no longer. This was
' 1500ms; the socket is free in well under half that, and the poll below is
' what actually protects against starting too early.
WScript.Sleep 500

' --server.headless true stops Streamlit opening its own browser tab the
' moment it binds the port — without it, this script's own open below landed
' as a *second* tab a few seconds later, on top of Streamlit's automatic one.
' 0 = hidden window, False = do not wait for it to finish
sh.Run "cmd /c python -m streamlit run app.py --server.headless true > lootledger.log 2>&1", 0, False

' Ask the server whether it is ready instead of guessing how long it needs.
'
' This used to be a flat "WScript.Sleep 8000", picked to be safely longer than
' startup on a bad day. Measured, the server answers its first request 2.2
' seconds after launch — so the flat wait was spending about seven seconds
' doing nothing at all, every single launch, and the shortcut felt broken.
'
' Polling is both faster and SAFER than any fixed number: a slow morning gets
' as long as it needs, up to the cap, rather than opening the browser onto a
' connection-refused page the way a too-short sleep would.
'
' The 25-second cap exists so a genuinely failed start does not hang here
' forever. If it is hit, the browser still opens — the page will say the site
' cannot be reached, and lootledger.log will say why.
ready = False
waited = 0
Do While waited < 25000
  WScript.Sleep 150
  waited = waited + 150
  On Error Resume Next
  Set http = CreateObject("MSXML2.XMLHTTP")
  http.Open "GET", "http://localhost:8501/", False
  http.Send
  If Err.Number = 0 Then
    If http.Status = 200 Then ready = True
  End If
  Err.Clear
  On Error GoTo 0
  If ready Then Exit Do
Loop

sh.Run "http://localhost:8501", 1, False
