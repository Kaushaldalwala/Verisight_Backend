import os
import subprocess
import sys

def main():
    print("Building VeriSight Executable...")
    # Add hidden imports if necessary for fastapi/uvicorn
    # We will build run.py into an exe
    args = [
        "pyinstaller",
        "--name", "VeriSight",
        "--onefile",
        "run.py"
    ]
    subprocess.run(args, check=True)
    print("Build completed successfully. Check the 'dist' folder for VeriSight.exe.")

if __name__ == "__main__":
    main()
