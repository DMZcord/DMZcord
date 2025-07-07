import os
import io
import discord
import logging
from datetime import datetime
from typing import Dict, Any, List

from util.owner.attachments import AttachmentAnalyzer
from util.community.constants import AttachmentOrder, GunsPerClass

logger = logging.getLogger(__name__)

Start_Time = getattr(os, "BOT_START_TIME", None) or datetime.now().timestamp()
Short = {cat.upper(): cat.upper()[:3] for cat in AttachmentOrder}

class DebugHelpers:
    @staticmethod
    def find_cog_extensions(base_dir="cogs"):
        extensions = []
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith("Cog.py"):
                    rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                    module = rel_path.replace(os.sep, ".")[:-3]
                    extensions.append(f"cogs.{module}")
        return sorted(extensions, key=lambda x: x.lower())

    @staticmethod
    def get_bot_info() -> Dict[str, Any]:
        """Get bot instance information"""
        return {
            "pid": os.getpid(),
            "start_time": datetime.fromtimestamp(Start_Time).strftime("%Y-%m-%d %H:%M:%S"),
            "start_timestamp": Start_Time
        }

    @staticmethod
    def paginate_lines(lines: List[str], max_chars: int = 1900) -> List[str]:
        """Paginate lines to fit within Discord message limits"""
        pages = []
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > max_chars:
                pages.append(current)
                current = ""
            current += line + "\n"
        if current:
            pages.append(current)
        return pages

class AttachmentUtils:
    @staticmethod
    def send_attachment_json(json_data, gun_name=None):
        filename = f"{gun_name}_attachments.json" if gun_name else "attachments.json"
        return discord.File(io.BytesIO(json_data), filename=filename)

    @staticmethod
    def get_empty_guns_text():
        empty_guns = AttachmentAnalyzer.get_guns_with_empty_attachments()
        return "\n".join(empty_guns) if empty_guns else "No guns found with 0 attachments in any category."

    @staticmethod
    def get_gun_attachments_text(gun_name):
        data = AttachmentAnalyzer.get_gun_attachments(gun_name)
        if not data["found"]:
            return f"Gun '{gun_name}' not found in attachment mapping."
        gun = data["gun"]
        attachments = data["attachments"]
        lines = [f"**{gun}**"]
        for att_type, names in sorted(attachments.items()):
            lines.append(f"- {att_type}: {len(names)} attachments")
        return "\n".join(lines)

    @staticmethod
    def get_all_guns_pages():
        all_guns = AttachmentAnalyzer.get_gun_attachments(None)["all_guns"]
        lines = []
        for gun in sorted(all_guns.keys(), key=lambda x: x.lower()):
            lines.append(f"**{gun}**")
            for att_type, names in sorted(all_guns[gun].items()):
                lines.append(f"- {att_type}: {len(names)} attachments")
            lines.append("")
        return DebugHelpers.paginate_lines(lines)

    @staticmethod
    async def get_sync_data(bot) -> List[Dict[str, str]]:
        """Get user sync data"""
        if not bot or not hasattr(bot, 'db'):
            logger.warning("Bot instance or database pool not found")
            return []
        try:
            async with bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT discord_id, wzhub_username, discord_username FROM user_sync"
                    )
                    rows = await cur.fetchall()
            return [
                {
                    "discord_id": row[0],
                    "discord_username": row[2] if len(row) > 2 else "Unknown",
                    "wzhub_username": row[1]
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting sync data: {e}")
            return []

    @staticmethod
    def get_gun_attachment_count_tables_by_class():
        """
        Returns a list of markdown tables, one per gun class (category).
        Each table only includes attachment categories actually used by at least one gun in that class.
        Each column is padded for Discord markdown alignment.
        """
        gun_to_types = AttachmentAnalyzer.build_attachment_mapping()
        tables = []

        for class_name, guns in GunsPerClass.items():
            guns_in_class = list(guns)  # Show all guns in the class

            # Find all attachment categories used by at least one gun in this class
            used_categories = set()
            for gun in guns_in_class:
                if gun in gun_to_types:
                    used_categories.update(gun_to_types[gun].keys())
            filtered_categories = [cat.upper() for cat in AttachmentOrder if cat.upper() in used_categories]
            if not filtered_categories:
                continue

            # Prepare header and rows
            header = ["Gun"] + [Short.get(cat, cat[:3]) for cat in filtered_categories]
            rows = []
            for gun in guns_in_class:
                row = [gun]
                for cat in filtered_categories:
                    if gun in gun_to_types:
                        row.append(str(len(gun_to_types[gun].get(cat, []))))
                    else:
                        row.append("0")
                rows.append(row)

            # Calculate max width for each column
            col_widths = [max(len(str(cell)) for cell in col) for col in zip(*([header] + rows))]

            # Build markdown table lines
            lines = []
            lines.append(f"### {class_name}")
            lines.append("```markdown")
            # Header row
            header_row = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(header)) + " |"
            lines.append(header_row)
            # Separator row
            sep_row = "|-" + "-|-".join("-" * w for w in col_widths) + "-|"
            lines.append(sep_row)
            # Data rows
            for row in rows:
                line = "| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) + " |"
                lines.append(line)
            lines.append("```")
            tables.append("\n".join(lines))
        return tables
