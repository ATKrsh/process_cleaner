# System Critical Processes - Never Terminate These (Fresh Windows Install Simulation)
SYSTEM_WHITELIST = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
    "lsass.exe", "svchost.exe", "fontdrvhost.exe", "explorer.exe", "taskmgr.exe",
    "dwm.exe", "spoolsv.exe", "conhost.exe", "winlogon.exe", "sihost.exe",
    "searchindexer.exe", "runtimebroker.exe", "ctfmon.exe", "taskhostw.exe",
    "wmiadap.exe", "wmiprvse.exe", "dllhost.exe", "lsaiso.exe", "nvdisplay.container.exe",
    "securityhealthservice.exe", "sgrmbroker.exe", "ntoskrnl.exe", "system idle process",
    "dashost.exe", "sppsvc.exe", "searchui.exe", "shellexperiencehost.exe", "smartscreen.exe",
    "applicationframehost.exe", "audiodg.exe", "backgroundtaskhost.exe", "credentialenrolementmanager.exe",
    "deviceassociationbroker.exe", "backgroundtransferhost.exe", "systemsettings.exe",
    "wudfhost.exe", "msmpeng.exe", "nissrv.exe", "startmenuexperiencehost.exe",
    "userinit.exe", "cmd.exe", "powershell.exe", "python.exe", "pythonw.exe", "py.exe",
    "main.exe" # Allow our own app to run
}

# Processes we know are bloatware or unnecessary background updaters
KNOWN_BLOATWARE = {
    "ccleaner64.exe", "ccleaner.exe", "onedrive.exe", "skype.exe", "spotify.exe",
    "discord.exe", "adobeupdate.exe", "googleupdate.exe", "msedgeupdate.exe",
    "steamwebhelper.exe", "epicgameslauncher.exe", "originwebhelper.exe",
    "uplaywebcore.exe", "gog galaxy.exe", "braveupdate.exe", "slack.exe",
    "teams.exe", "zoom.exe", "webex.exe"
}

# Layman descriptions for common processes
LAYMAN_DESCRIPTIONS = {
    "svchost.exe": "A core Windows component that runs various background services (like Windows Update or network connections).",
    "explorer.exe": "The main user interface of Windows (Taskbar, Desktop, File Explorer).",
    "dwm.exe": "Desktop Window Manager. It handles the visual effects on your screen, like transparent windows and animations.",
    "csrss.exe": "Client/Server Run-Time Subsystem. A critical process that handles console windows and creating/deleting threads.",
    "lsass.exe": "Local Security Authority Process. Handles user logins, password changes, and access tokens. Critical for security.",
    "smss.exe": "Session Manager Subsystem. The first user-mode process started by Windows, it initializes your session.",
    "wininit.exe": "Windows Initialization Process. Starts important background services when your computer boots up.",
    "services.exe": "Services Control Manager. It starts, stops, and manages all the background services running on your computer.",
    "taskmgr.exe": "Task Manager. The app you use to view and close running programs.",
    "system idle process": "Not a real program. It just shows how much of your processor's power is currently NOT being used.",
    "msmpeng.exe": "Windows Defender. The built-in antivirus software protecting your computer from malware.",
    "spoolsv.exe": "Print Spooler. Manages jobs sent to your printer.",
    "conhost.exe": "Console Window Host. Provides the black window for command-line programs.",
    "winlogon.exe": "Windows Logon Application. Handles the screen where you enter your password or pin.",
    "searchindexer.exe": "Windows Search Indexer. Looks through your files so you can find them quickly when you search."
}
