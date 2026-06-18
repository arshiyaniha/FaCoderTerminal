# Simple Persian PowerShell

A minimal terminal app for Windows.

It uses:

- pywebview for the window
- xterm.js for terminal rendering
- pywinpty for a real PowerShell session
- UTF-8 startup settings for Persian text

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m simple_terminal.main
```

## Test Persian

Inside the terminal:

```powershell
Write-Output "سلام فارسی"
```

## Notes

This version intentionally has no AI, no GitHub panel, no server settings, and no command catalog.
It is only a clean PowerShell-like terminal window.
