# Python Not Found - Quick Fix

## The Problem
Python is not found at the path your system is looking for.

## Solutions (Choose ONE):

### ✅ Solution 1: Use the batch script (EASIEST)
```bash
run_tests.bat
```
This will automatically install dependencies and run tests.

---

### ✅ Solution 2: Use `py` launcher
```bash
# Install dependencies
py -m pip install -r requirements.txt

# Run tests
py -m pytest tests/ -v
```

---

### ✅ Solution 3: Find and use your Python directly
```bash
# Find Python
where python

# Use the path shown (example):
C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe -m pip install -r requirements.txt
C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/ -v
```

---

### ✅ Solution 4: Reinstall Python
1. Download from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Restart terminal
4. Run: `python -m pip install -r requirements.txt`
5. Run: `python -m pytest tests/ -v`

---

## Quick Test
After fixing, verify with:
```bash
py --version
py -m pytest --version
```

Both should show version numbers.
