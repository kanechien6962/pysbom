@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo Starting setup for PySBOM external dependencies...
echo ==========================================

:: ------------------------------------------
:: 1. Download and extract SPDX Java Tools Jar
:: ------------------------------------------
if not exist "tools\spdx\tools-java-2.0.7-jar-with-dependencies.jar" (
    echo [1/2] Downloading SPDX Java Tools v2.0.7...
    if not exist "tools\spdx" mkdir "tools\spdx"
    
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/spdx/tools-java/releases/download/v2.0.7/tools-java-2.0.7.zip' -OutFile 'tools_java.zip'"
    
    echo Extracting and capturing the jar file...
    powershell -Command "Expand-Archive -Path 'tools_java.zip' -DestinationPath 'temp_tools' -Force"
    powershell -Command "Copy-Item 'temp_tools\tools-java-2.0.7-jar-with-dependencies.jar' -Destination 'tools\spdx\' -Force"
    
    :: Clean up temporary files
    del tools_java.zip
    rmdir /S /Q temp_tools
    echo [SUCCESS] SPDX Java Tools installed to tools\spdx\
) else (
    echo [SKIPPED] SPDX Java Tools already exists.
)

echo.

:: ------------------------------------------
:: 2. Obtain python-uswid project
:: ------------------------------------------
if not exist "python-uswid\.git" (
    echo [2/2] Cloning python-uswid repository...
    if exist "python-uswid" rmdir /S /Q "python-uswid"
    
    git clone https://github.com/hughsie/python-uswid.git python-uswid
    echo [SUCCESS] python-uswid downloaded successfully!
) else (
    echo [SKIPPED] python-uswid directory already exists and contains Git tracking.
)

echo.
echo ==========================================
echo All dependencies are ready!
echo ==========================================
pause