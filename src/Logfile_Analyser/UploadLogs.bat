@echo off
setlocal enabledelayedexpansion

REM =====================================================
REM Hamilton .trc Log Backup
REM Copies .trc files created/modified since the last run
REM to a serial-number-specific folder on the network share.
REM Designed to be called from Windows Task Scheduler.
REM =====================================================

REM --- Config (edit these for this machine) ---
set "INITIAL_DAYS=30"
set "SERIALNUMBER=0000"
set "SOURCEFOLDER=C:\Program Files (x86)\HAMILTON\LogFiles"
set "DESTBASE=W:\0.051 Research & Development\Instrumentation\Logfiles\Hamilton"
set "SCRIPTDIR=%~dp0"
set "DESTFOLDER=%DESTBASE%\%SERIALNUMBER%"
set "LASTRUNFILE=%SCRIPTDIR%lastrun_%SERIALNUMBER%.txt"
set "LOGFILE=%SCRIPTDIR%copylog_%SERIALNUMBER%.txt"

REM --- Config Checks ---
if "!SERIALNUMBER!"=="0000" (
    echo ERROR: SERIALNUMBER has not been set.
    exit /b 1
)

if not exist "!SOURCEFOLDER!" (
    echo ERROR: Source folder does not exist: !SOURCEFOLDER!
    exit /b 1
)

if not exist "!DESTBASE!" (
    echo ERROR: Destination base is not accessible: !DESTBASE!
    exit /b 1
)

if not exist "!DESTFOLDER!" (
    mkdir "!DESTFOLDER!" 2>>"%LOGFILE%"
    if not exist "!DESTFOLDER!" (
        echo ERROR: Could not create destination folder: !DESTFOLDER! >> "%LOGFILE%"
        echo ERROR: Could not create destination folder: !DESTFOLDER!
        exit /b 1
    )
)

echo ==================================================== >> "%LOGFILE%"
echo Run started: %DATE% %TIME% >> "%LOGFILE%"

REM --- Determine cutoff date (YYYYMMDD) from last run marker ---
REM If no marker exists yet (first run), default to INITIAL_DAYS ago.
if exist "%LASTRUNFILE%" (
    set /p MAXAGE=<"%LASTRUNFILE%"
) else (
    for /f %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-%INITIAL_DAYS%).ToString('yyyyMMdd')"') do set "MAXAGE=%%D"
)

echo Using cutoff date (MAXAGE): %MAXAGE% >> "%LOGFILE%"
echo Source: %SOURCEFOLDER% >> "%LOGFILE%"
echo Destination: %DESTFOLDER% >> "%LOGFILE%"

REM --- Copy only .trc files modified on/after MAXAGE date ---
robocopy "%SOURCEFOLDER%" "%DESTFOLDER%" *.trc /MAXAGE:%MAXAGE% /R:2 /W:5 /NJH /LOG+:"%LOGFILE%"
set "ROBOEXIT=%ERRORLEVEL%"
if %ROBOEXIT% GEQ 8 (
    echo ERROR: Robocopy failed with exit code %ROBOEXIT% >> "%LOGFILE%"
    exit /b %ROBOEXIT%
)
for /f %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd')"') do set "TODAY=%%D"

echo %TODAY%>"%LASTRUNFILE%"
echo Run completed successfully: %DATE% %TIME% >> "%LOGFILE%"
echo ==================================================== >> "%LOGFILE%"
exit /b 0