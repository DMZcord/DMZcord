import json
import logging
from typing import Optional, Dict, Any, List
from util.community.data import Gun_Attachments

logger = logging.getLogger(__name__)


class AttachmentAnalyzer:
    """Analyze attachment data for debugging"""

    @staticmethod
    def get_gun_attachments(gun_name: Optional[str] = None) -> Dict[str, Any]:
        """Get attachment data for guns"""
        gun_to_types = AttachmentAnalyzer.build_attachment_mapping()

        if gun_name:
            gun_name_lower = gun_name.lower()
            found = None
            for gun in gun_to_types:
                if gun.lower() == gun_name_lower:
                    found = gun
                    break

            if not found:
                return {"found": False, "gun": gun_name}

            return {
                "found": True,
                "gun": found,
                "attachments": gun_to_types[found]
            }

        return {
            "found": True,
            "all_guns": gun_to_types
        }

    @staticmethod
    def get_guns_with_empty_attachments() -> List[str]:
        """Get guns that have 0 attachments in any category"""
        gun_to_types = AttachmentAnalyzer.build_attachment_mapping()
        guns_with_empty = []

        for gun, types_dict in gun_to_types.items():
            if any(len(names) == 0 for names in types_dict.values()):
                guns_with_empty.append(gun)

        return guns_with_empty

    @staticmethod
    def export_attachments_json(gun_name: Optional[str] = None) -> bytes:
        """Export attachment data as JSON"""
        gun_to_types = AttachmentAnalyzer.build_attachment_mapping()

        if gun_name:
            gun_name_lower = gun_name.lower()
            for gun in gun_to_types:
                if gun.lower() == gun_name_lower:
                    data = {gun: gun_to_types[gun]}
                    break
            else:
                data = {"error": f"Gun '{gun_name}' not found"}
        else:
            data = gun_to_types

        return json.dumps(data, indent=2).encode("utf-8")

    @staticmethod
    def build_attachment_mapping() -> Dict[str, Dict[str, List[str]]]:
        """Build gun to attachment type mapping"""

        gun_to_types = {}

        if not Gun_Attachments:
            logger.warning("Gun_Attachments is empty or not loaded")
            return gun_to_types

        for att_type, att_dict in Gun_Attachments.items():
            if not isinstance(att_dict, dict):
                logger.warning(
                    f"Attachment type {att_type} is not a dictionary")
                continue

            for att_name, guns in att_dict.items():
                if not isinstance(guns, list):
                    logger.warning(f"Gun list for {att_name} is not a list")
                    continue

                for gun in guns:
                    gun_to_types.setdefault(gun, {}).setdefault(
                        att_type, []).append(att_name)

        return gun_to_types
