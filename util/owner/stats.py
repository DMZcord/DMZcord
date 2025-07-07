import logging
import statistics
from collections import defaultdict
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DebugStats:
    @staticmethod
    async def get_command_stats(bot) -> List[Dict[str, Any]]:
        """Get command usage statistics (count, avg, min, max) for each command."""
        if not bot or not hasattr(bot, 'db'):
            logger.warning("Bot instance or database pool not found")
            return []
        try:
            async with bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT command_name,
                               COUNT(*) AS count,
                               AVG(response_time) AS avg_time,
                               MIN(response_time) AS min_time,
                               MAX(response_time) AS max_time
                        FROM command_logs
                        GROUP BY command_name
                        ORDER BY count DESC
                    """)
                    rows = await cur.fetchall()
                    logger.info(f"Fetched {len(rows)} rows from command_logs")
                    return [
                        {
                            "command_name": row[0],
                            "count": row[1],
                            "avg_time": row[2] or 0,
                            "min_time": row[3] or 0,
                            "max_time": row[4] or 0
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Error getting command stats: {e}")
            return []

    @staticmethod
    async def get_command_stats_with_times(bot) -> List[Dict[str, Any]]:
        """Get command usage statistics including all response times for median calculation."""
        if not bot or not hasattr(bot, 'db'):
            logger.warning("Bot instance or database pool not found")
            return []

        try:
            async with bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT command_name, response_time
                        FROM command_logs
                    """)
                    rows = await cur.fetchall()

            # Group response times by command_name
            stats = defaultdict(list)
            for cmd, resp_time in rows:
                if resp_time is not None:
                    stats[cmd].append(float(resp_time))

            result = []
            for cmd, times in stats.items():
                result.append({
                    "command_name": cmd,
                    "count": len(times),
                    "avg_time": statistics.mean(times) if times else 0,
                    "min_time": min(times) if times else 0,
                    "max_time": max(times) if times else 0,
                    "median_time": statistics.median(times) if times else 0,
                    "times": times
                })
            # Sort by count descending
            result.sort(key=lambda x: x["count"], reverse=True)
            return result

        except Exception as e:
            logger.error(f"Error getting command stats: {e}")
            return []

    @staticmethod
    async def get_command_abuse_stats(bot, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by total command usage."""
        if not bot or not hasattr(bot, 'db'):
            logger.warning("Bot instance or database pool not found")
            return []
        try:
            async with bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT user_id, COUNT(*) AS total_runs, 
                               AVG(response_time) AS avg_time, 
                               MAX(response_time) AS max_time
                        FROM command_logs
                        WHERE user_id IS NOT NULL
                        GROUP BY user_id
                        ORDER BY total_runs DESC
                        LIMIT %s
                    """, (limit,))
                    rows = await cur.fetchall()
            return [
                {
                    "user_id": row[0],
                    "total_runs": row[1],
                    "avg_time": row[2] or 0,
                    "max_time": row[3] or 0
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting command abuse stats: {e}")
            return []

    @staticmethod
    async def get_most_blacklisted_users(bot, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the top N most blacklisted users (active or inactive)."""
        if not bot or not hasattr(bot, 'db'):
            logger.warning("Bot instance or database pool not found")
            return []
        try:
            async with bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT user_id, COUNT(*) as count
                        FROM blacklist
                        WHERE user_id IS NOT NULL
                        GROUP BY user_id
                        ORDER BY count DESC
                        LIMIT %s
                    """, (limit,))
                    rows = await cur.fetchall()
            return [
                {"user_id": row[0], "count": row[1]}
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting most blacklisted users: {e}")
            return []
