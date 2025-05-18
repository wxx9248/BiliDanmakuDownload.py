# Protobuf Generation for Bilibili Danmaku Downloader

This document explains how to generate the `dm_pb2.py` file used by the Bilibili Danmaku Downloader to parse danmaku data.

## Prerequisites

- Python 3.13+
- The `grpcio-tools` package installed (`pip install grpcio-tools`)
- The original protobuf definition file in `api/grpc_api/bilibili/community/service/dm/v1/dm.proto`

## Generate the Protobuf File

The `build_protobuf.py` script generates the complete protobuf Python module:

```bash
python build_protobuf.py
```

This will create a `dm_pb2.py` file in the current directory containing all the classes defined in the protobuf definition, ensuring compatibility with the Bilibili API.

## How to Use the Generated File

The script will generate a `dm_pb2.py` file in the current directory, which can be imported by the application:

```python
import dm_pb2

# Parse danmaku data
danmaku_reply = dm_pb2.DmSegMobileReply()
danmaku_reply.ParseFromString(binary_data)

# Access danmaku elements
for danmaku in danmaku_reply.elems:
    print(f"Content: {danmaku.content}")
```

## Troubleshooting

If you encounter issues with the protobuf generation:

1. Make sure the path to the protobuf definition file is correct
2. Ensure you have the required dependencies installed (`grpcio-tools`)
3. If you modify the protobuf structure, you may need to regenerate the file

For more complex issues, you may need to adjust the paths in the script to match your specific project structure.
