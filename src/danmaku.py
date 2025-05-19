"""
Danmaku downloader and exporter.
"""
import asyncio
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List

import aiofiles

import dm_pb2
from client import BilibiliAPIClient


class DanmakuExportFormat:
    """Danmaku export format constants"""
    XML = "xml"  # XML format (for player compatibility)
    JSON = "json"  # JSON format (for analysis)
    CSV = "csv"  # CSV format (for spreadsheet)
    TEXT = "txt"  # Plain text format


class DanmakuDownloader:
    """
    Downloader for danmaku from Bilibili.
    """

    def __init__(self, client: BilibiliAPIClient):
        """
        Initialize with API client.
        
        Args:
            client: Bilibili API client
        """
        self.client = client

    async def download_danmaku(self, cid: str, duration_seconds: int = 0) -> List[dm_pb2.DanmakuElem]:
        """
        Download danmaku for a specific Chat ID.
        
        Args:
            cid: Chat ID
            duration_seconds: Video duration in seconds (used to determine segment count)
            
        Returns:
            List of DanmakuElem
        """
        all_danmaku = []

        # Calculate number of segments (each segment is 6 minutes = 360 seconds)
        # Add 1 extra segment to ensure we capture all danmaku
        segment_count = max(1, (duration_seconds // 360) + 1)

        # Create tasks for fetching all segments
        tasks = []
        for segment_index in range(1, segment_count + 1):
            tasks.append(self.client.get_danmaku(cid, segment_index))

        # Execute tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                print(f"Error fetching danmaku segment: {result}")
                continue
            all_danmaku.extend(result)

        return all_danmaku


class DanmakuExporter:
    """
    Exporter for danmaku to different formats.
    """

    @staticmethod
    async def export_xml(danmaku_list: List[dm_pb2.DanmakuElem], output_file: str):
        """
        Export danmaku to XML format.
        
        Args:
            danmaku_list: List of DanmakuElem
            output_file: Output file path
        """
        root = ET.Element("i")

        # Add metadata
        chatserver = ET.SubElement(root, "chatserver")
        chatserver.text = "chat.bilibili.com"

        chatid = ET.SubElement(root, "chatid")
        chatid.text = "0"

        mission = ET.SubElement(root, "mission")
        mission.text = "0"

        maxlimit = ET.SubElement(root, "maxlimit")
        maxlimit.text = str(len(danmaku_list))

        source = ET.SubElement(root, "source")
        source.text = "k-v"

        # Add danmaku items
        for dm in danmaku_list:
            # Format: time, mode, fontsize, color, create_time, pool, user_hash, dmid
            attr_str = f"{dm.progress / 1000},{dm.mode},{dm.fontsize},{dm.color},{dm.ctime},0,{dm.midHash},{dm.id}"

            d = ET.SubElement(root, "d", {"p": attr_str})
            d.text = dm.content

        # Save file
        async with aiofiles.open(output_file, "w", encoding="utf-8") as f:
            await f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            await f.write(ET.tostring(root, encoding="unicode"))

    @staticmethod
    async def export_json(danmaku_list: List[dm_pb2.DanmakuElem], output_file: str):
        """
        Export danmaku to JSON format.
        
        Args:
            danmaku_list: List of DanmakuElem
            output_file: Output file path
        """
        json_data = []

        for dm in danmaku_list:
            json_data.append({
                "id": dm.id,
                "progress": dm.progress,
                "time": dm.progress / 1000,  # Convert to seconds
                "mode": dm.mode,
                "fontsize": dm.fontsize,
                "color": dm.color,
                "midHash": dm.midHash,
                "content": dm.content,
                "ctime": dm.ctime,
                "timestamp": datetime.fromtimestamp(dm.ctime).isoformat(),
                "weight": dm.weight,
                "pool": dm.pool,
                "attr": dm.attr
            })

        async with aiofiles.open(output_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(json_data, ensure_ascii=False, indent=2))

    @staticmethod
    async def export_csv(danmaku_list: List[dm_pb2.DanmakuElem], output_file: str):
        """
        Export danmaku to CSV format.
        
        Args:
            danmaku_list: List of DanmakuElem
            output_file: Output file path
        """
        header = "id,progress,time_sec,mode,fontsize,color,midHash,content,ctime,timestamp,weight,pool,attr\n"

        lines = []
        for dm in danmaku_list:
            # Escape commas and quotes in content
            content = f'"{dm.content.replace("\"", "\"\"")}"'
            timestamp = datetime.fromtimestamp(dm.ctime).isoformat()

            line = f"{dm.id},{dm.progress},{dm.progress / 1000},{dm.mode},{dm.fontsize},{dm.color},{dm.midHash},{content},{dm.ctime},{timestamp},{dm.weight},{dm.pool},{dm.attr}"
            lines.append(line)

        async with aiofiles.open(output_file, "w", encoding="utf-8") as f:
            await f.write(header)
            await f.write("\n".join(lines))

    @staticmethod
    async def export_text(danmaku_list: List[dm_pb2.DanmakuElem], output_file: str):
        """
        Export danmaku to plain text format.
        
        Args:
            danmaku_list: List of DanmakuElem
            output_file: Output file path
        """
        lines = []

        # Sort by progress (time)
        sorted_danmaku = sorted(danmaku_list, key=lambda x: x.progress)

        for dm in sorted_danmaku:
            time_str = f"{dm.progress / 1000:.1f}s"
            lines.append(f"[{time_str}] {dm.content}")

        async with aiofiles.open(output_file, "w", encoding="utf-8") as f:
            await f.write("\n".join(lines))

    @staticmethod
    async def export(danmaku_list: List[dm_pb2.DanmakuElem], output_file: str, format: str = DanmakuExportFormat.XML):
        """
        Export danmaku to the specified format.
        
        Args:
            danmaku_list: List of DanmakuElem
            output_file: Output file path
            format: Export format
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

        # Export based on format
        if format == DanmakuExportFormat.XML:
            await DanmakuExporter.export_xml(danmaku_list, output_file)
        elif format == DanmakuExportFormat.JSON:
            await DanmakuExporter.export_json(danmaku_list, output_file)
        elif format == DanmakuExportFormat.CSV:
            await DanmakuExporter.export_csv(danmaku_list, output_file)
        elif format == DanmakuExportFormat.TEXT:
            await DanmakuExporter.export_text(danmaku_list, output_file)
        else:
            raise ValueError(f"Unsupported export format: {format}")
