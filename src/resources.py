"""
Resource handling module for different Bilibili resource types.
"""
from typing import Dict, Tuple
import re
from client import BilibiliAPIClient


class ResourceType:
    """Resource type constants"""
    AV = "av"  # Video (av ID)
    BV = "BV"  # Video (bvid) - case sensitive prefix
    EP = "ep"  # Episode
    SS = "ss"  # Season
    MD = "md"  # Media


class ResourceID:
    """
    Class for handling different types of resource IDs.
    """

    def __init__(self, raw_id: str):
        """
        Parse the raw ID input from user.
        
        Args:
            raw_id: Resource ID with prefix (av, BV, ep, ss, md)
        """
        # Only trim whitespace, preserve case for bvids
        self.raw_id = raw_id.strip()

        # Match AV/EP/SS/mdids (numeric)
        numeric_match = re.match(r"^(av|ep|ss|md)(\d+)$", self.raw_id.lower())
        if numeric_match:
            self.prefix = numeric_match.group(1)
            self.id = numeric_match.group(2)
            return

        # Match bvids - case sensitive, must start with BV
        bv_match = re.match(r"^(BV)([a-zA-Z0-9]+)$", self.raw_id)
        if bv_match:
            self.prefix = bv_match.group(1)  # Preserve "BV" case
            self.id = bv_match.group(2)
            return

        raise ValueError(f"Invalid resource ID format: {raw_id}. Expected format: av/BV/ep/ss/md + ID")

    @property
    def resource_type(self) -> str:
        """Get the resource type."""
        return self.prefix.lower() if self.prefix != "BV" else "BV"

    @property
    def numeric_id(self) -> str:
        """Get the ID without prefix."""
        return self.id

    @property
    def api_id(self) -> str:
        """
        Get the ID formatted for API calls.
        For bvids, this is the full ID with prefix.
        For other IDs, this is just the numeric part.
        """
        if self.prefix == "BV":
            return f"{self.prefix}{self.id}"
        return self.id

    def __str__(self) -> str:
        """String representation of the resource ID."""
        return self.raw_id


class ResourceFetcher:
    """
    Fetcher for different types of resources.
    """

    def __init__(self, client: BilibiliAPIClient):
        """
        Initialize with API client.
        
        Args:
            client: Bilibili API client
        """
        self.client = client

    async def fetch_season_id_from_media_id(self, mdid: str) -> str:
        """
        Get season ID (ssid) from media ID (mdid).
        
        Args:
            mdid: Media ID
            
        Returns:
            Season ID
        """
        url = "https://api.bilibili.com/pgc/review/user"
        params = {"media_id": mdid}

        response = await self.client.get_json(url, params)
        if response["code"] != 0:
            raise ValueError(f"Error fetching season ID: {response['message']}")

        return str(response["result"]["media"]["season_id"])

    async def fetch_episodes_from_season_id(self, ssid: str) -> Dict[str, Tuple[str, str, int]]:
        """
        Get episodes from season ID.
        
        Args:
            ssid: Season ID
            
        Returns:
            Dictionary mapping aid to (title, chat_id, duration_seconds)
        """
        url = "https://api.bilibili.com/pgc/view/web/season"
        params = {"season_id": ssid}

        response = await self.client.get_json(url, params)
        if response["code"] != 0:
            raise ValueError(f"Error fetching episodes: {response['message']}")

        # Extract episodes from main section
        episodes = {}
        for episode in response["result"]["episodes"]:
            aid = str(episode["aid"])
            title = episode["long_title"] or episode["title"]
            cid = str(episode["cid"])
            # Duration in seconds
            duration = episode.get("duration", 0) // 1000  # Convert from milliseconds to seconds if present
            episodes[aid] = (title, cid, duration)

        # Extract episodes from other sections if available
        if "section" in response["result"]:
            for section in response["result"]["section"]:
                for episode in section["episodes"]:
                    aid = str(episode["aid"])
                    title = episode["title"]
                    cid = str(episode["cid"])
                    # Duration in seconds
                    duration = episode.get("duration", 0) // 1000  # Convert from milliseconds to seconds if present
                    episodes[aid] = (title, cid, duration)

        return episodes

    async def fetch_episodes_from_episode_id(self, epid: str) -> Dict[str, Tuple[str, str, int]]:
        """
        Get episodes from episode ID.
        
        Args:
            epid: Episode ID
            
        Returns:
            Dictionary mapping aid to (title, chat_id, duration_seconds)
        """
        url = "https://api.bilibili.com/pgc/view/web/season"
        params = {"ep_id": epid}

        response = await self.client.get_json(url, params)
        if response["code"] != 0:
            raise ValueError(f"Error fetching episodes: {response['message']}")

        # Extract season ID and use it to fetch all episodes
        ssid = str(response["result"]["season_id"])
        return await self.fetch_episodes_from_season_id(ssid)

    async def fetch_pages_from_avid(self, avid: str) -> Dict[str, Tuple[str, str, int]]:
        """
        Get video pages from avid.
        
        Args:
            avid: Video ID
            
        Returns:
            Dictionary mapping page number to (title, chat_id, duration_seconds)
        """
        url = "https://api.bilibili.com/x/web-interface/view"
        params = {"aid": avid}

        response = await self.client.get_json(url, params)
        if response["code"] != 0:
            raise ValueError(f"Error fetching video pages: {response['message']}")

        pages = {}
        for page in response["data"]["pages"]:
            page_num = str(page["page"])
            title = page["part"]
            cid = str(page["cid"])
            duration = page.get("duration", 0)  # Duration in seconds
            pages[page_num] = (title, cid, duration)

        return pages

    async def fetch_pages_from_bvid(self, bvid: str) -> Dict[str, Tuple[str, str, int]]:
        """
        Get video pages from bvid.
        
        Args:
            bvid: Full bvid including prefix
            
        Returns:
            Dictionary mapping page number to (title, chat_id, duration_seconds)
        """
        url = "https://api.bilibili.com/x/web-interface/view"
        params = {"bvid": bvid}

        response = await self.client.get_json(url, params)
        if response["code"] != 0:
            raise ValueError(f"Error fetching video pages: {response['message']}")

        pages = {}
        for page in response["data"]["pages"]:
            page_num = str(page["page"])
            title = page["part"]
            cid = str(page["cid"])
            duration = page.get("duration", 0)  # Duration in seconds
            pages[page_num] = (title, cid, duration)

        return pages

    async def fetch_content_ids(self, resource_id: ResourceID) -> Dict[str, Tuple[str, str, int]]:
        """
        Get content IDs based on resource type.
        
        Args:
            resource_id: Parsed resource ID
            
        Returns:
            Dictionary mapping id to (title, chat_id, duration_seconds)
        """
        resource_type = resource_id.resource_type.lower()

        if resource_type == ResourceType.AV.lower():
            return await self.fetch_pages_from_avid(resource_id.numeric_id)
        elif resource_type == ResourceType.BV.lower():
            # Pass the full bvid (with prefix) to the API
            return await self.fetch_pages_from_bvid(resource_id.api_id)
        elif resource_type == ResourceType.EP.lower():
            return await self.fetch_episodes_from_episode_id(resource_id.numeric_id)
        elif resource_type == ResourceType.SS.lower():
            return await self.fetch_episodes_from_season_id(resource_id.numeric_id)
        elif resource_type == ResourceType.MD.lower():
            ssid = await self.fetch_season_id_from_media_id(resource_id.numeric_id)
            return await self.fetch_episodes_from_season_id(ssid)
        else:
            raise ValueError(f"Unsupported resource type: {resource_id.resource_type}")
