"""
Scheduled tasks for the application.

This module contains scheduled tasks that run in the background to perform
maintenance operations like cache cleanup.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.config import settings
from app.crud import crud_price_cache, crud_conversion_cache

logger = logging.getLogger(__name__)


class ScheduledTaskManager:
    """
    Manager for scheduled background tasks.

    This class handles the scheduling and execution of background tasks
    like cache cleanup.
    """

    def __init__(self):
        """Initialize the scheduled task manager."""
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_cleanup: Optional[datetime] = None

    async def start_scheduled_tasks(self):
        """Start all scheduled tasks."""
        if self._running:
            logger.warning("Scheduled tasks are already running")
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._run_periodic_cache_cleanup())
        logger.info("Started scheduled tasks")

    async def stop_scheduled_tasks(self):
        """Stop all scheduled tasks."""
        if not self._running:
            logger.warning("Scheduled tasks are not running")
            return

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        self._running = False
        logger.info("Stopped scheduled tasks")

    async def _run_periodic_cache_cleanup(self):
        """Run cache cleanup periodically."""
        # Get cleanup intervals from settings
        price_cleanup_interval_hours = 24  # Run price cache cleanup once a day
        conversion_cleanup_interval_hours = (
            24  # Run conversion cache cleanup once a day
        )

        try:
            while True:
                try:
                    # Run cache cleanup
                    await self._cleanup_cache()
                    self._last_cleanup = datetime.utcnow()

                    # Sleep until next cleanup
                    # We use the shorter interval to ensure both caches are cleaned up regularly
                    sleep_interval = min(
                        price_cleanup_interval_hours, conversion_cleanup_interval_hours
                    )
                    await asyncio.sleep(
                        sleep_interval * 3600
                    )  # Convert hours to seconds
                except Exception as e:
                    logger.error(f"Error in cache cleanup task: {e}")
                    # Sleep for a while before retrying
                    await asyncio.sleep(3600)  # 1 hour
        except asyncio.CancelledError:
            logger.info("Cache cleanup task cancelled")
            raise

    async def _cleanup_cache(self):
        """Clean up expired cache entries."""
        # Removed noisy "Starting cache cleanup" log

        # Get database session
        async for db in get_db():
            try:
                # Clean up price cache
                price_cleanup_days = settings.PRICE_CACHE_CLEANUP_DAYS
                price_entries_cleared = (
                    await crud_price_cache.cleanup_old_cache_entries(
                        db=db, max_age_days=price_cleanup_days
                    )
                )

                # Clean up conversion cache
                conversion_cleanup_days = settings.CONVERSION_CACHE_CLEANUP_DAYS
                conversion_entries_cleared = (
                    await crud_conversion_cache.cleanup_old_conversion_cache_entries(
                        db=db, max_age_days=conversion_cleanup_days
                    )
                )

                # Only log if entries were actually cleared (reduce noise)
                if price_entries_cleared > 0:
                    logger.info(
                        f"Cleared {price_entries_cleared} expired price cache entries"
                    )
                if conversion_entries_cleared > 0:
                    logger.info(
                        f"Cleared {conversion_entries_cleared} expired conversion cache entries"
                    )

                return {
                    "price_entries_cleared": price_entries_cleared,
                    "conversion_entries_cleared": conversion_entries_cleared,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}")
                raise

    @property
    def last_cleanup(self) -> Optional[datetime]:
        """Get the timestamp of the last cache cleanup."""
        return self._last_cleanup

    @property
    def is_running(self) -> bool:
        """Check if scheduled tasks are running."""
        return self._running


# Global instance
scheduled_task_manager = ScheduledTaskManager()
