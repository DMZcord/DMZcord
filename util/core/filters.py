class Filters:
    @staticmethod
    def filterlogs(record):
        # Suppress common, non-critical command errors
        if (
            record.exc_info
            and hasattr(record.exc_info[1], "__class__")
            and record.exc_info[1].__class__.__name__ in (
                "MissingPermissions",
                "NotOwner",
                "CommandNotFound"
            )
        ):
            return False  # Don't log this record
        return True