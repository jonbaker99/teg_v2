@echo off
REM Test runner script for TEG Analysis test suite
REM Runs all tests with coverage report

echo ========================================
echo TEG Analysis Test Suite Runner
echo ========================================
echo.

REM Run all tests with coverage
echo Running tests with coverage analysis...
python -m pytest tests/ -v --cov=streamlit --cov-report=html --cov-report=term-missing

echo.
echo ========================================
echo Test Results Summary
echo ========================================
echo.
echo Coverage report generated in htmlcov/index.html
echo.
pause
