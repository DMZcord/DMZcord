from util.community.data import Gun_Attachments
from typing import List, Optional

class AttachmentLookup:
    @staticmethod
    def get_attachments_for_gun(gun_name: str, category: Optional[str] = None) -> List[dict]:
        """Get all attachments available for a specific gun."""
        gun_name = gun_name.upper()
        available_attachments = []
        
        for attachment_category, attachments in Gun_Attachments.items():
            if category and attachment_category.upper() != category.upper():
                continue
                
            for attachment_name, compatible_guns in attachments.items():
                if gun_name in compatible_guns:
                    available_attachments.append({
                        'name': attachment_name,
                        'category': attachment_category,
                        'guns': compatible_guns
                    })
        
        return available_attachments

    @staticmethod
    def get_guns_for_attachment(attachment_name: str) -> List[str]:
        """Get all guns compatible with a specific attachment."""
        attachment_name = attachment_name.upper()
        
        for category, attachments in Gun_Attachments.items():
            if attachment_name in attachments:
                return attachments[attachment_name]
        
        return []

    @staticmethod
    def validate_attachment(gun_name: str, attachment_name: str) -> bool:
        """Check if an attachment is compatible with a gun."""
        gun_name = gun_name.upper()
        attachment_name = attachment_name.upper()
        
        compatible_guns = AttachmentLookup.get_guns_for_attachment(attachment_name)
        return gun_name in compatible_guns

    @staticmethod
    def get_attachment_categories() -> List[str]:
        """Get all attachment categories."""
        return list(Gun_Attachments.keys())

    @staticmethod
    def search_attachments(query: str, category: Optional[str] = None) -> List[dict]:
        """Search for attachments by name."""
        query = query.upper()
        results = []
        
        for attachment_category, attachments in Gun_Attachments.items():
            if category and attachment_category.upper() != category.upper():
                continue
                
            for attachment_name, compatible_guns in attachments.items():
                if query in attachment_name.upper():
                    results.append({
                        'name': attachment_name,
                        'category': attachment_category,
                        'guns': compatible_guns
                    })
        
        return results