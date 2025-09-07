# Stationery Flask App

A modern, responsive Flask UI for your Stationery management (originally CLI-based).

## Setup

1. Create and activate a virtual environment (recommended)
   - Windows PowerShell
   - 
2. Install dependencies
   ```powershell
   pip install -r requirements.txt
   ```
3. Configure MySQL via environment variables (optional)
   ```powershell
   $env:MYSQL_HOST = "localhost"
   $env:MYSQL_USER = "root"
   $env:MYSQL_PASSWORD = "your_password"
   $env:MYSQL_DATABASE = "StationeryDB"
   ```
   If `MYSQL_DATABASE` is not set, the app will prompt for it on first use.

## Run
```powershell
python app.py
```
Visit http://127.0.0.1:5000/ in your browser.

## Notes
- The default table name is `Stationery`. Override with `?table=YourTable` in URLs.
- CRUD and billing views are available via the navbar and buttons on the Items page.

