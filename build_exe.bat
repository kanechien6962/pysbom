
@echo off
setlocal

cd /d "%~dp0"
if errorlevel 1 goto :error

REM ==========================================
REM Configuration
REM ==========================================
set "APP_NAME=SBOM"
set "ENTRY_POINT=main.py"
set "JAR_SOURCE=tools\spdx\tools-java-2.0.7-jar-with-dependencies.jar"
set "JAVA_SOURCE=vendor\runtime"

set "DIST_DIR=dist\%APP_NAME%"
set "JAVA_TARGET=%DIST_DIR%\runtime"
set "JAR_TARGET=%DIST_DIR%\tools\spdx"

echo.
echo ==========================================
echo Building %APP_NAME%
echo ==========================================

REM Check source files
if not exist "%ENTRY_POINT%" (
    echo ERROR: %ENTRY_POINT% not found.
    goto :error
)

if not exist "%JAR_SOURCE%" (
    echo ERROR: SPDX JAR not found.
    goto :error
)

if not exist "%JAVA_SOURCE%\bin\java.exe" (
    echo Downloading the OpenJDK 25 runtime environment...
    powershell -Command "$url = 'https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4.1+1/OpenJDK25U-jre_x64_windows_hotspot_25.0.4.1_1.zip'; Invoke-WebRequest -Uri $url -OutFile 'openjdk.zip'"
    
    echo unzip...
    powershell -Command "Expand-Archive -Path 'openjdk.zip' -DestinationPath 'temp_jre' -Force"
    
    :: build floder and move correct path
    mkdir vendor\runtime
    xcopy /E /I /Y temp_jre\jdk-25.0.4.1+1-jre\* vendor\runtime\

    :: clear temp files
    del openjdk.zip
    rmdir /S /Q temp_jre
    echo JRE done！
)

REM Test bundled Java Runtime
"%JAVA_SOURCE%\bin\java.exe" -version
if errorlevel 1 (
    echo ERROR: Bundled Java Runtime cannot run.
    goto :error
)

REM Install PyInstaller
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

REM Clean previous build
if exist "build" rmdir /s /q "build"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"

REM Install the local python-uswid package into the build environment
python -m pip install -e "%~dp0python-uswid"
if errorlevel 1 goto :error

REM Build Python application
python -m PyInstaller ^
    --icon "sbom_48x48.ico" ^
    --add-data "sbom_48x48.ico;." ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --distpath "dist\%APP_NAME%" ^
    --paths "%~dp0python-uswid" ^
    --collect-all uswid ^
    --name "%APP_NAME%" ^
    "%ENTRY_POINT%"

if errorlevel 1 goto :error

REM Copy Java Runtime
xcopy "%JAVA_SOURCE%" "%JAVA_TARGET%\" /E /I /H /Y
if errorlevel 1 goto :error

REM Copy SPDX Java Tools JAR
if not exist "%JAR_TARGET%" mkdir "%JAR_TARGET%"
if errorlevel 1 goto :error

copy /Y "%JAR_SOURCE%" "%JAR_TARGET%\"
if errorlevel 1 goto :error

REM Verify bundled Java
"%JAVA_TARGET%\bin\java.exe" -version
if errorlevel 1 goto :error

REM Verify required output files
if not exist "%DIST_DIR%\%APP_NAME%.exe" goto :error
if not exist "%JAVA_TARGET%\bin\java.exe" goto :error
if not exist "%JAR_TARGET%\tools-java-2.0.7-jar-with-dependencies.jar" goto :error

echo.
echo ==========================================
echo BUILD SUCCESS
echo Output: %DIST_DIR%\%APP_NAME%.exe
echo Java Runtime: %JAVA_TARGET%
echo SPDX JAR: %JAR_TARGET%
echo ==========================================
pause
exit /b 0

:error
echo.
echo ==========================================
echo BUILD FAILED
echo Check the errors above.
echo ==========================================
pause
exit /b 1
