import json
from typing import List, Dict, Set
from util.community.queries import CommunityQueries
from .models import Loadout, Attachment, LoadoutSearchResult

class LoadoutRepository:
    @staticmethod
    async def get_all_loadouts(guild_id: str = None) -> List[Loadout]:
        rows = await CommunityQueries.get_cached_loadouts(guild_id=guild_id)
        loadouts = []
        
        for row in rows:
            try:
                username = row["username"]
                data = json.loads(row["data"])
                last_updated = row["last_updated"]
                
                for loadout_data in data:
                    attachments = [
                        Attachment(
                            type=att["type"],
                            name=att["name"],
                            tuning1=att.get("tuning1"),
                            tuning2=att.get("tuning2")
                        )
                        for att in loadout_data["attachments"]
                    ]
                    
                    loadout = Loadout(
                        gun_name=loadout_data["gun_name"],
                        gun_type=loadout_data["gun_type"],
                        gun_image_url=loadout_data.get("gun_image_url"),
                        attachments=attachments,
                        username=username,
                        last_updated=last_updated
                    )
                    loadouts.append(loadout)
            except Exception:
                continue
        
        return loadouts

    @staticmethod
    async def search_loadouts_by_gun(gun_name: str, guild_id: str = None) -> List[LoadoutSearchResult]:
        """Search for loadouts by gun name."""
        all_loadouts = await LoadoutRepository.get_all_loadouts(guild_id)
        
        found = []
        for loadout in all_loadouts:
            if gun_name.lower() in loadout.gun_name.lower():
                result = LoadoutSearchResult(
                    username=loadout.username,
                    loadout=loadout,
                    last_updated=loadout.last_updated or ""
                )
                found.append(result)
        
        return sorted(found, key=lambda x: x.username.lower())

    @staticmethod
    async def get_guns_by_type(guild_id: str = None) -> Dict[str, Set[str]]:
        """Get all guns organized by type."""
        all_loadouts = await LoadoutRepository.get_all_loadouts(guild_id)
        
        guns = {}
        for loadout in all_loadouts:
            gun_type = loadout.gun_type
            gun_name = loadout.gun_name
            
            if gun_type not in guns:
                guns[gun_type] = set()
            guns[gun_type].add(gun_name)
        
        return guns