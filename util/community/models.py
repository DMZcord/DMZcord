from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class Attachment:
    """Represents a weapon attachment."""
    name: str
    type: str
    tuning1: str = "0.00"
    tuning2: str = "0.00"
    
    def has_tuning(self) -> bool:
        """Check if attachment has non-zero tuning values."""
        return self.tuning1 not in ["-", "", "0.00", None] or self.tuning2 not in ["-", "", "0.00", None]
    
    def get_tuning_display(self, vert_emoji: str, hor_emoji: str) -> str:
        """Get formatted tuning display string."""
        if not self.has_tuning():
            return ""
        
        t1 = self.tuning1 if self.tuning1 not in ["-", "", None] else "0.00"
        t2 = self.tuning2 if self.tuning2 not in ["-", "", None] else "0.00"
        return f" {vert_emoji} {t1} {hor_emoji} {t2}"

@dataclass
class Loadout:
    """Represents a complete weapon loadout."""
    gun_name: str
    gun_type: str
    attachments: List[Attachment]
    gun_image_url: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Loadout':
        """Create Loadout from dictionary data."""
        attachments = [
            Attachment(
                name=att.get("name", ""),
                type=att.get("type", ""),
                tuning1=att.get("tuning1", "0.00"),
                tuning2=att.get("tuning2", "0.00")
            )
            for att in data.get("attachments", [])
        ]
        
        return cls(
            gun_name=data.get("gun_name", ""),
            gun_type=data.get("gun_type", ""),
            attachments=attachments,
            gun_image_url=data.get("gun_image_url")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert loadout to dictionary."""
        return {
            "gun_name": self.gun_name,
            "gun_type": self.gun_type,
            "gun_image_url": self.gun_image_url,
            "attachments": [
                {
                    "name": att.name,
                    "type": att.type,
                    "tuning1": att.tuning1,
                    "tuning2": att.tuning2
                }
                for att in self.attachments
            ]
        }

@dataclass
class LoadoutSearchResult:
    """Search result for loadout queries."""
    username: str
    loadout: Loadout
    last_updated: str
    
    @property
    def cache_timestamp(self) -> Optional[datetime]:
        """Get parsed cache timestamp."""
        try:
            return datetime.fromisoformat(self.last_updated)
        except Exception:
            return None