#!/usr/bin/env python3
"""
Script to reinstall llama-cpp-python with GPU support
"""

import os
import subprocess
import sys

def main():
    print("Starting setup for GPU-enabled llama-cpp-python...")

    # Set environment variables for CUDA support
    os.environ["CMAKE_ARGS"] = "-DGGML_CUDA=on"
    os.environ["FORCE_CMAKE"] = "1"

    # Uninstall existing package
    print("Removing existing llama-cpp-python installation...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "llama-cpp-python"])

    # Install with CUDA support
    print("Installing llama-cpp-python with CUDA support...")
    subprocess.run([sys.executable, "-m", "pip", "install", "llama-cpp-python", "--no-cache-dir"])

    # Verify installation
    print("\nVerifying installation:")
    try:
        import llama_cpp
        print(f"llama-cpp-python version: {llama_cpp.__version__}")

        # Try to detect CUDA capabilities
        from ctypes import cdll
        try:
            cdll.LoadLibrary("cublas64_11.dll")
            print("CUDA libraries detected!")
        except:
            try:
                cdll.LoadLibrary("cublas64_12.dll")
                print("CUDA libraries detected!")
            except:
                print("Warning: CUDA libraries not found in standard locations")

        print("\nChecking GPU layers support...")
        result = subprocess.run([sys.executable, "-c",
            "import llama_cpp; print('GPU layers supported in your build' if hasattr(llama_cpp.llama_cpp, 'llama_context_offload_layers') else 'GPU support NOT detected in your build')"],
            capture_output=True, text=True)
        print(result.stdout.strip())

    except ImportError as e:
        print(f"Error importing llama_cpp: {e}")

    print("\nSetup complete. If GPU support is shown as available, you should now be able to use GPU acceleration.")
    print("If you still have issues, ensure your NVIDIA drivers are up to date.")
    print("\nTo use GPU acceleration, make sure n_gpu_layers is set to a value between 1 and the total number of layers (-1 for all).")

if __name__ == "__main__":
    main()
