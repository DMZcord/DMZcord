from enum import Enum

class AttachmentCategory(Enum):
    AMMUNITION = "AMMUNITION"
    BARREL = "BARREL"
    LASER = "LASER"
    MAGAZINE = "MAGAZINE"
    MUZZLE = "MUZZLE"
    OPTIC = "OPTIC"
    REAR_GRIP = "REAR GRIP"
    STOCK = "STOCK"
    UNDERBARREL = "UNDERBARREL"
    COMB = "COMB"
    TRIGGER_ACTION = "TRIGGER ACTION"
    LOADER = "LOADER"
    ARMS = "ARMS"
    BOLT = "BOLT"
    CABLE = "CABLE"
    GUARD = "GUARD"
    LEVER = "LEVER"
    RAIL = "RAIL"
    CARRY_HANDLE = "CARRY HANDLE"

class AttachmentType:
    """Helper class for attachment operations."""
    
    @staticmethod
    def is_valid_category(category: str) -> bool:
        try:
            AttachmentCategory(category.upper())
            return True
        except ValueError:
            return False
    
    @staticmethod
    def normalize_category(category: str) -> str:
        return category.upper().replace("_", " ")