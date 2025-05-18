#!/usr/bin/env python3
"""
Protobuf Generator Script for Bilibili Danmaku Downloader

This script generates the dm_pb2.py file from the Bilibili protobuf definition.
It uses the protobuf compiler (protoc) via grpcio-tools to create the Python bindings.
"""
import shutil
import subprocess
import sys
from pathlib import Path

# Path to the protobuf definition file
PROTO_FILE_PATH = "api/grpc_api/bilibili/community/service/dm/v1/dm.proto"
OUTPUT_DIR = "src"
OUTPUT_FILE = "dm_pb2.py"
TEMP_DIR = "_proto_build_temp"

# Required classes for verification
REQUIRED_CLASSES = ["DanmakuElem", "DmSegMobileReply"]


def find_proto_file():
    """Find the protobuf definition file in the project."""
    proto_path = Path(PROTO_FILE_PATH)

    if not proto_path.exists():
        print(f"Error: Could not find protobuf definition file at {PROTO_FILE_PATH}")
        print("Please ensure the file exists or update the path in this script.")
        return None

    return proto_path


def generate_protobuf(proto_path):
    """Generate the Python protobuf module."""
    print(f"Generating protobuf Python module from {proto_path}...")

    # Create a temporary directory for the build
    temp_dir = Path(TEMP_DIR)
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)

    # Get the proto file directory structure
    proto_dir = proto_path.parent

    # Generate Python files with protoc
    command = [
        sys.executable,  # Python executable
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={proto_dir.parent.parent.parent.parent.parent}",  # Up to the grpc_api dir
        f"--python_out={temp_dir}",
        str(proto_path)
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Protobuf generation completed.")

        # Find the generated file in the output directory structure
        output_files = list(temp_dir.glob("**/*_pb2.py"))
        if not output_files:
            print("Error: No protobuf file was generated.")
            print("Subprocess output:")
            print(result.stdout)
            print(result.stderr)
            return False

        # Move the generated file to the output directory
        generated_file = output_files[0]
        target_path = Path(OUTPUT_DIR) / OUTPUT_FILE

        # Copy the full generated file to the target path
        shutil.copy2(generated_file, target_path)

        print(f"Protobuf file generated at: {target_path}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to generate protobuf file. {e}")
        print(e.stdout if hasattr(e, 'stdout') else "")
        print(e.stderr if hasattr(e, 'stderr') else "")
        return False

    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def main():
    """Main function."""
    proto_path = find_proto_file()
    if not proto_path:
        return 1

    success = generate_protobuf(proto_path)

    if success:
        # Verify the output file exists and is not empty
        output_path = Path(OUTPUT_DIR) / OUTPUT_FILE
        if output_path.exists() and output_path.stat().st_size > 0:
            print("Protobuf generation completed successfully.")
            return 0
        else:
            print("Error: Generated file is empty or does not exist.")
            return 1
    else:
        print("Protobuf generation failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
