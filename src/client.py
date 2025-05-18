"""
API client for Bilibili API requests.
"""
import os
from typing import Dict, Any, Optional, List

import aiohttp

import dm_pb2


class BilibiliAPIClient:
    """
    Async client for making requests to Bilibili APIs.
    """
    DEFAULT_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh-TW;q=0.6,zh;q=0.5",
        "Cache-Control": "max-age=0",
        "Priority": "u=0, i",
        "Sec-Ch-Ua": "\"Chromium\";v=\"136\", \"Microsoft Edge\";v=\"136\", \"Not.A/Brand\";v=\"99\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"
    }

    COOKIE_FILE_PATH = "cookie.txt"

    @classmethod
    def load_cookies_from_file(cls, file_path: str = None) -> str:
        """
        Load cookies from a file.
        
        Args:
            file_path: Path to the cookie file. Defaults to COOKIE_FILE_PATH.
            
        Returns:
            Cookie string or empty string if file doesn't exist
        """
        path = file_path or cls.COOKIE_FILE_PATH

        if not os.path.exists(path):
            print(f"Cookie file not found: {path}")
            return ""

        try:
            with open(path, "r", encoding="utf-8") as f:
                cookie_content = f.read().strip()
                print(f"Loaded cookies from {path}")
                return cookie_content
        except Exception as e:
            print(f"Error loading cookies: {e}")
            return ""

    def __init__(self, headers: Optional[Dict[str, str]] = None, cookie_file: Optional[str] = None):
        """
        Initialize the client with optional headers and cookie file.
        
        Args:
            headers: Optional headers to override the default ones
            cookie_file: Optional path to cookie file
        """
        self.headers = {**self.DEFAULT_HEADERS, **(headers or {})}

        # Try to load cookies from file
        cookie = self.load_cookies_from_file(cookie_file)
        if cookie:
            self.headers["Cookie"] = cookie

        self.session = None
        self._closed = False

    async def __aenter__(self):
        """Context manager entry."""
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def open(self):
        """Open the HTTP client session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        self._closed = False
        return self

    async def close(self):
        """Close the HTTP client session."""
        if self.session and not self.session.closed:
            await self.session.close()
        self._closed = True

    async def get_json(self, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Make a GET request and return JSON response.
        
        Args:
            url: API URL
            params: URL query parameters
            
        Returns:
            JSON response as a dictionary
        """
        if self.session is None or self.session.closed:
            await self.open()

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def get_binary(self, url: str, params: Optional[Dict[str, str]] = None) -> bytes:
        """
        Make a GET request and return binary response.
        
        Args:
            url: API URL
            params: URL query parameters
            
        Returns:
            Binary response data
        """
        if self.session is None or self.session.closed:
            await self.open()

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.read()

    async def get_danmaku(self, cid: str, segment_index: int = 1) -> List[dm_pb2.DanmakuElem]:
        """
        Get danmaku for a specific Chat ID (cid).
        
        Args:
            cid: Chat ID
            segment_index: Segment index (6min per segment)
            
        Returns:
            List of DanmakuElem
        """
        url = "https://api.bilibili.com/x/v2/dm/web/seg.so"
        params = {
            "type": "1",
            "oid": cid,
            "segment_index": str(segment_index)
        }

        raw_data = await self.get_binary(url, params)
        danmaku_seg = dm_pb2.DmSegMobileReply()
        danmaku_seg.ParseFromString(raw_data)

        return list(danmaku_seg.elems)
