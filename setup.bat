@echo off
REM Flex Box - One-click dependency installer (Windows)
REM Run this after cloning to set up the environment

echo =========================================
echo   Flex Box - Environment Setup
echo =========================================
echo.

REM Check Python version
python --version
echo.

echo Step 1: Installing PyTorch (CPU)...
echo   This downloads ~123MB and may take a few minutes.
pip install torch --timeout 3000
if %errorlevel% neq 0 (
    echo.
    echo ERROR: PyTorch installation failed.
    echo Try running: pip install torch --timeout 3000
    echo in a separate terminal with better connectivity.
    exit /b 1
)

echo.
echo Step 2: Installing transformers and PEFT stack...
pip install transformers peft accelerate sentencepiece protobuf
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Dependency installation failed.
    exit /b 1
)

echo.
echo Step 3: Installing Flex Box in editable mode...
pip install -e .

echo.
echo =========================================
echo   Setup Complete!
echo =========================================
echo.
echo Usage:
echo   flexbox route "Create a React button component"
echo   flexbox generate "Add bg-blue-500 text-white p-4"
echo   flexbox adapters
echo   flexbox info
echo.
echo Run tests:
echo   python tests/test_phase1.py
