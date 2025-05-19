"""
API client for Bilibili API requests.
"""
import os
import time
import hashlib
import urllib.parse
from typing import Dict, Any, Optional, List, Tuple
from functools import reduce

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
    
    # WBI mixing key encoding table
    WBI_MIXIN_KEY_ENC_TAB = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]

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
        
        # WBI keys cache
        self._img_key = None
        self._sub_key = None
        self._wbi_keys_expire_time = 0  # Cache keys for 24 hours

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
        
    @staticmethod
    def _get_mixin_key(orig: str) -> str:
        """
        Generate mixin key from img_key and sub_key.
        
        Args:
            orig: Concatenated img_key and sub_key
            
        Returns:
            Mixed key
        """
        mixed = ''.join([orig[i] for i in BilibiliAPIClient.WBI_MIXIN_KEY_ENC_TAB])
        return mixed[:32]  # Take only the first 32 characters
        
    async def _get_wbi_keys(self) -> Tuple[str, str]:
        """
        Get img_key and sub_key from API.
        
        Returns:
            Tuple of (img_key, sub_key)
        """
        current_time = time.time()
        
        # Use cached keys if they're not expired (cached for 24 hours)
        if self._img_key and self._sub_key and current_time < self._wbi_keys_expire_time:
            print(f"Using cached WBI keys: img_key={self._img_key[:8]}..., sub_key={self._sub_key[:8]}...")
            return self._img_key, self._sub_key
            
        # Fetch new keys
        print("Fetching new WBI keys...")
        url = "https://api.bilibili.com/x/web-interface/nav"
        
        # Direct HTTP request to avoid recursive call to get_json
        if self.session is None or self.session.closed:
            await self.open()
            
        async with self.session.get(url) as response:
            if response.status != 200:
                error_message = f"HTTP {response.status} - {response.reason}"
                raise ValueError(f"Failed to get WBI keys: {error_message}")
                
            response_json = await response.json()
        
        if response_json["code"] != 0:
            raise ValueError(f"Failed to get WBI keys: {response_json['message']}")
            
        wbi_img = response_json["data"]["wbi_img"]
        img_url = wbi_img["img_url"]
        sub_url = wbi_img["sub_url"]
        
        # Extract keys from URLs
        self._img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        self._sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
        
        print(f"Got new WBI keys: img_key={self._img_key[:8]}..., sub_key={self._sub_key[:8]}...")
        
        # Set expiration time to 24 hours from now
        self._wbi_keys_expire_time = current_time + 86400
        
        return self._img_key, self._sub_key
        
    async def _sign_with_wbi(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign request parameters with WBI authentication.
        
        Args:
            params: Request parameters
            
        Returns:
            Parameters with WBI signature
        """
        img_key, sub_key = await self._get_wbi_keys()
        mixin_key = self._get_mixin_key(img_key + sub_key)
        
        print(f"WBI mixin_key={mixin_key[:8]}...")
        
        # Create a copy of the parameters to avoid modifying the original
        signed_params = params.copy()
        
        # Add timestamp
        current_time = int(time.time())
        signed_params["wts"] = current_time
        
        # Sort parameters by key
        signed_params = dict(sorted(signed_params.items()))
        
        # Filter out special characters from values
        filtered_params = {
            k: ''.join(c for c in str(v) if c not in "!'()*")
            for k, v in signed_params.items()
        }
        
        # Encode parameters
        query = urllib.parse.urlencode(filtered_params)
        
        # Calculate w_rid
        w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
        
        # Add w_rid to original params
        params["w_rid"] = w_rid
        params["wts"] = current_time
        
        print(f"WBI signed params: {', '.join([f'{k}={v}' for k, v in params.items()])}")
        
        return params

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
            if response.status != 200:
                # Try to parse error response as JSON if possible
                try:
                    error_json = await response.json()
                    error_message = f"HTTP {response.status} - {error_json.get('message', 'Unknown error')}"
                    print(f"API error: {error_message}")
                except:
                    error_message = f"HTTP {response.status} - {response.reason}"
                    print(f"API error: {error_message}")
                
                response.raise_for_status()  # This will raise an appropriate HTTPError
                
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
        # Try WBI authenticated endpoint first
        try:
            print(f"Fetching danmaku for cid={cid}, segment={segment_index} using WBI endpoint")
            url = "https://api.bilibili.com/x/v2/dm/wbi/web/seg.so"
            params = {
                "type": "1",
                "oid": cid,
                "segment_index": str(segment_index)
            }
            
            # Sign parameters with WBI
            signed_params = await self._sign_with_wbi(params)
            
            raw_data = await self.get_binary(url, signed_params)
            danmaku_seg = dm_pb2.DmSegMobileReply()
            danmaku_seg.ParseFromString(raw_data)
            
            result = list(danmaku_seg.elems)
            print(f"Successfully fetched {len(result)} danmaku items using WBI endpoint")
            return result
            
        except Exception as e:
            print(f"Error using WBI endpoint: {e}, falling back to legacy endpoint")
            
            # Fallback to original endpoint if WBI fails
            try:
                print(f"Fetching danmaku for cid={cid}, segment={segment_index} using legacy endpoint")
                url = "https://api.bilibili.com/x/v2/dm/web/seg.so"
                params = {
                    "type": "1",
                    "oid": cid,
                    "segment_index": str(segment_index)
                }
                
                raw_data = await self.get_binary(url, params)
                danmaku_seg = dm_pb2.DmSegMobileReply()
                danmaku_seg.ParseFromString(raw_data)
                
                result = list(danmaku_seg.elems)
                print(f"Successfully fetched {len(result)} danmaku items using legacy endpoint")
                return result
                
            except Exception as fallback_error:
                print(f"Error using fallback endpoint: {fallback_error}")
                # If both endpoints fail, return empty list
                return []
