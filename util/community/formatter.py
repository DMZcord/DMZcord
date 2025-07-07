from typing import List, Dict, Set
from datetime import datetime

from util.core.utils import TableUtils
from .models import Loadout, LoadoutSearchResult, Attachment
from util.community.constants import AttachmentOrder, MW2Emoji, TuningVertEmoji, TuningHorEmoji

class LoadoutFormatter:
    @staticmethod
    def sort_attachments(attachments: List[Attachment]) -> List[Attachment]:
        """Sort attachments by predefined order."""
        return sorted(
            attachments,
            key=lambda att: (
                AttachmentOrder.index(str(att.type).strip().lower())
                if att.type and str(att.type).strip().lower() in AttachmentOrder
                else 99
            )
        )

    @staticmethod
    def format_loadout_display(
        username: str, 
        loadout: Loadout, 
        last_updated: str,
        show_cache_time: bool = True
    ) -> str:
        """Format a complete loadout for display."""
        lines = []
        lines.append(f"{MW2Emoji} {username}'s {loadout.gun_name} ({loadout.gun_type})")
        
        # Sort and display attachments
        sorted_attachments = LoadoutFormatter.sort_attachments(loadout.attachments)
        
        for att in sorted_attachments:
            att_type = att.type.upper()
            tuning_display = att.get_tuning_display(TuningVertEmoji, TuningHorEmoji)
            lines.append(f"{att_type}: {att.name}{tuning_display}")
        
        # Add cache timestamp if requested
        if show_cache_time and last_updated:
            try:
                dt = datetime.fromisoformat(last_updated)
                lines.append("")
                lines.append(dt.strftime("Loadout cached: %A, %B %-d, %Y %-I:%M %p"))
            except Exception:
                pass
        
        return "\n".join(lines)

    @staticmethod
    def format_gun_table(guns_by_type: Dict[str, Set[str]]) -> str:
        """Format guns grouped by type into a table."""
        lines = []
        for gun_type in sorted(guns_by_type.keys(), key=str.lower):
            lines.append(f"**{gun_type}:**")
            
            table_rows = [["Gun Name"]]
            for gun_name in sorted(guns_by_type[gun_type], key=str.lower):
                table_rows.append([gun_name])
            
            lines.append(TableUtils.format_table(table_rows))
            lines.append("")
        
        return "\n".join(lines)

    @staticmethod
    def format_loadout_summary(results: List[LoadoutSearchResult], gun_name: str) -> str:
        """Format a summary of loadout search results."""
        if not results:
            return f"No cached loadouts found for gun '{gun_name}'."
        
        lines = [f"**Users with cached loadouts for '{gun_name}':**"]
        for result in results:
            lines.append(f"• {result.username}")
        
        return "\n".join(lines)