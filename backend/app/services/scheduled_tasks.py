"""
Scheduled tasks for the application.

This module contains scheduled tasks that run in the background to perform
maintenance operations like cache cleanup and session management.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.config import settings
from app.crud import crud_price_cache, crud_conversion_cache

logger = logging.getLogger(__name__)


class ScheduledTaskManager:
    """
    Manager for scheduled background tasks.

    This class handles the scheduling and execution of background tasks
    like cache cleanup and session management.
    """

    def __init__(self):
        """Initialize the scheduled task manager."""
        self._cleanup_task: Optional[asyncio.Task] = None
        self._session_cleanup_task: Optional[asyncio.Task] = None
        self._demo_cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_cleanup: Optional[datetime] = None
        self._last_session_cleanup: Optional[datetime] = None
        self._last_demo_cleanup: Optional[datetime] = None

    async def start_scheduled_tasks(self):
        """Start all scheduled tasks."""
        if self._running:
            logger.warning("Scheduled tasks are already running")
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._run_periodic_cache_cleanup())
        self._session_cleanup_task = asyncio.create_task(
            self._run_periodic_session_cleanup()
        )
        self._demo_cleanup_task = asyncio.create_task(self._run_periodic_demo_cleanup())
        logger.info(
            "Started scheduled tasks (cache cleanup, session management, and demo mode cleanup)"
        )

    async def stop_scheduled_tasks(self):
        """Stop all scheduled tasks."""
        if not self._running:
            logger.warning("Scheduled tasks are not running")
            return

        # Cancel cache cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Cancel session cleanup task
        if self._session_cleanup_task:
            self._session_cleanup_task.cancel()
            try:
                await self._session_cleanup_task
            except asyncio.CancelledError:
                pass
            self._session_cleanup_task = None

        # Cancel demo cleanup task
        if self._demo_cleanup_task:
            self._demo_cleanup_task.cancel()
            try:
                await self._demo_cleanup_task
            except asyncio.CancelledError:
                pass
            self._demo_cleanup_task = None

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

    async def _run_periodic_session_cleanup(self):
        """Run session cleanup periodically."""
        # Session cleanup runs every hour
        session_cleanup_interval_hours = 1

        try:
            while True:
                try:
                    # Run session cleanup
                    await self._cleanup_sessions()
                    self._last_session_cleanup = datetime.utcnow()

                    # Sleep until next cleanup
                    await asyncio.sleep(
                        session_cleanup_interval_hours * 3600
                    )  # Convert hours to seconds
                except Exception as e:
                    logger.error(f"Error in session cleanup task: {e}")
                    # Sleep for a while before retrying
                    await asyncio.sleep(1800)  # 30 minutes
        except asyncio.CancelledError:
            logger.info("Session cleanup task cancelled")
            raise

    async def _cleanup_sessions(self):
        """Clean up expired and inactive sessions."""
        from app.services.auth_service import auth_service
        from app.core.auth_config import auth_settings

        # Only run session cleanup if authentication is enabled
        if not auth_settings.auth_enabled:
            return

        # Get database session
        async for db in get_db():
            try:
                # Clean up expired sessions
                expired_sessions_cleared = await auth_service.cleanup_expired_sessions(
                    db
                )

                # Clean up inactive sessions (inactive for more than 7 days)
                inactive_sessions_cleared = (
                    await auth_service.cleanup_inactive_sessions(db, inactive_hours=168)
                )  # 7 days

                # Get session security info for monitoring
                security_info = await auth_service.get_session_security_info(db)

                # Log session cleanup activity for security monitoring
                total_cleared = expired_sessions_cleared + inactive_sessions_cleared
                if total_cleared > 0:
                    logger.info(
                        f"Session cleanup completed: {expired_sessions_cleared} expired, {inactive_sessions_cleared} inactive sessions cleared",
                        extra={
                            "event_type": "session_cleanup_summary",
                            "expired_sessions_cleared": expired_sessions_cleared,
                            "inactive_sessions_cleared": inactive_sessions_cleared,
                            "total_sessions_cleared": total_cleared,
                            "active_sessions_remaining": security_info.get(
                                "active_sessions", 0
                            ),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )

                return {
                    "expired_sessions_cleared": expired_sessions_cleared,
                    "inactive_sessions_cleared": inactive_sessions_cleared,
                    "total_sessions_cleared": total_cleared,
                    "security_info": security_info,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except Exception as e:
                logger.error(f"Error during session cleanup: {e}")
                raise

    async def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics for monitoring purposes."""
        from app.services.auth_service import auth_service
        from app.core.auth_config import auth_settings
        from sqlalchemy import select, func
        from app.models.session import Session

        if not auth_settings.auth_enabled:
            return {"auth_enabled": False}

        async for db in get_db():
            try:
                # Count total sessions
                total_sessions_result = await db.execute(select(func.count(Session.id)))
                total_sessions = total_sessions_result.scalar()

                # Count active sessions
                active_sessions_result = await db.execute(
                    select(func.count(Session.id)).where(
                        Session.is_active == True,
                        Session.expires_at > datetime.utcnow(),
                    )
                )
                active_sessions = active_sessions_result.scalar()

                # Count expired sessions
                expired_sessions_result = await db.execute(
                    select(func.count(Session.id)).where(
                        Session.expires_at <= datetime.utcnow()
                    )
                )
                expired_sessions = expired_sessions_result.scalar()

                return {
                    "auth_enabled": True,
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "expired_sessions": expired_sessions,
                    "last_session_cleanup": (
                        self._last_session_cleanup.isoformat()
                        if self._last_session_cleanup
                        else None
                    ),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except Exception as e:
                logger.error(f"Error getting session statistics: {e}")
                return {
                    "auth_enabled": True,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }

    async def _run_periodic_demo_cleanup(self):
        """Run demo mode database cleanup at the configured time daily."""
        from app.core.auth_config import auth_settings

        # Only run demo cleanup if demo mode is enabled
        if not auth_settings.DEMO_MODE:
            logger.debug("Demo mode not enabled, demo cleanup task will not run")
            return

        try:
            while True:
                try:
                    # Calculate seconds until next cleanup time
                    seconds_until_cleanup = self._calculate_seconds_until_demo_cleanup()

                    logger.debug(
                        f"Next demo cleanup in {seconds_until_cleanup} seconds"
                    )

                    # Wait until cleanup time
                    await asyncio.sleep(seconds_until_cleanup)

                    # Perform demo cleanup
                    await self._perform_demo_cleanup()
                    self._last_demo_cleanup = datetime.utcnow()

                except Exception as e:
                    logger.error(f"Error in demo cleanup task: {e}")
                    # Wait 1 hour before retrying on error
                    await asyncio.sleep(3600)

        except asyncio.CancelledError:
            logger.info("Demo cleanup task cancelled")
            raise

    def _calculate_seconds_until_demo_cleanup(self) -> int:
        """Calculate seconds until the next demo cleanup time."""
        from app.core.auth_config import auth_settings
        from datetime import time, timedelta

        # Parse cleanup time from settings
        try:
            hours, minutes = auth_settings.DEMO_CLEANUP_TIME.split(":")
            cleanup_time = time(int(hours), int(minutes))
        except (ValueError, IndexError):
            logger.warning(
                f"Invalid cleanup time format: {auth_settings.DEMO_CLEANUP_TIME}. Using 00:00"
            )
            cleanup_time = time(0, 0)

        now = datetime.utcnow()
        cleanup_datetime = datetime.combine(now.date(), cleanup_time)

        # If cleanup time has passed today, schedule for tomorrow
        if cleanup_datetime <= now:
            cleanup_datetime += timedelta(days=1)

        return int((cleanup_datetime - now).total_seconds())

    async def _perform_demo_cleanup(self):
        """Perform demo mode database cleanup with error handling and recovery."""
        from app.services.demo_service import demo_service
        from app.core.auth_config import auth_settings

        # Only run demo cleanup if demo mode is enabled
        if not auth_settings.DEMO_MODE:
            return

        # Check if cleanup was already done today
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if (
            hasattr(self, "_last_demo_cleanup_date")
            and self._last_demo_cleanup_date == today
        ):
            logger.debug("Demo cleanup already performed today, skipping")
            return

        max_retries = 3
        retry_delay = 300  # 5 minutes

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Starting scheduled demo mode database cleanup (attempt {attempt + 1}/{max_retries})"
                )

                # Perform the cleanup using the demo service
                success = await demo_service.cleanup_database()

                if success:
                    self._last_demo_cleanup_date = today
                    logger.info(
                        "Scheduled demo mode database cleanup completed successfully",
                        extra={
                            "event_type": "demo_cleanup_completed",
                            "cleanup_date": today,
                            "preserve_asset_id": auth_settings.DEMO_PRESERVE_ASSET_ID,
                            "attempt": attempt + 1,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )

                    # Ensure demo asset exists after cleanup
                    try:
                        await demo_service.ensure_demo_asset_exists()
                        logger.debug("Demo asset verification completed after cleanup")
                    except Exception as asset_error:
                        logger.warning(
                            f"Failed to verify demo asset after cleanup: {asset_error}"
                        )

                    return  # Success, exit retry loop
                else:
                    logger.warning(
                        f"Demo cleanup attempt {attempt + 1} failed, will retry if attempts remain"
                    )

                    # If this is not the last attempt, wait before retrying
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting {retry_delay} seconds before retry...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff

            except Exception as e:
                logger.error(
                    f"Error during scheduled demo cleanup attempt {attempt + 1}: {e}",
                    extra={
                        "event_type": "demo_cleanup_error",
                        "cleanup_date": today,
                        "attempt": attempt + 1,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                # If this is not the last attempt, wait before retrying
                if attempt < max_retries - 1:
                    logger.info(f"Waiting {retry_delay} seconds before retry...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

        # All attempts failed
        logger.error(
            f"Demo mode database cleanup failed after {max_retries} attempts",
            extra={
                "event_type": "demo_cleanup_failed_all_attempts",
                "cleanup_date": today,
                "max_retries": max_retries,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def get_demo_cleanup_status(self) -> Dict[str, Any]:
        """Get demo mode cleanup status for monitoring purposes."""
        from app.core.auth_config import auth_settings
        from datetime import time, timedelta

        if not auth_settings.DEMO_MODE:
            return {"demo_mode": False}

        try:
            # Parse cleanup time
            try:
                hours, minutes = auth_settings.DEMO_CLEANUP_TIME.split(":")
                cleanup_time = time(int(hours), int(minutes))
            except (ValueError, IndexError):
                cleanup_time = time(0, 0)

            now = datetime.utcnow()
            next_cleanup = datetime.combine(now.date(), cleanup_time)
            if next_cleanup <= now:
                next_cleanup += timedelta(days=1)

            return {
                "demo_mode": True,
                "cleanup_time": auth_settings.DEMO_CLEANUP_TIME,
                "preserve_asset_id": auth_settings.DEMO_PRESERVE_ASSET_ID,
                "last_cleanup": (
                    self._last_demo_cleanup.isoformat()
                    if self._last_demo_cleanup
                    else None
                ),
                "last_cleanup_date": getattr(self, "_last_demo_cleanup_date", None),
                "next_cleanup": next_cleanup.isoformat(),
                "cleanup_task_running": self._demo_cleanup_task is not None
                and not self._demo_cleanup_task.done(),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting demo cleanup status: {e}")
            return {
                "demo_mode": True,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    @property
    def last_cleanup(self) -> Optional[datetime]:
        """Get the timestamp of the last cache cleanup."""
        return self._last_cleanup

    @property
    def last_session_cleanup(self) -> Optional[datetime]:
        """Get the timestamp of the last session cleanup."""
        return self._last_session_cleanup

    @property
    def last_demo_cleanup(self) -> Optional[datetime]:
        """Get the timestamp of the last demo cleanup."""
        return self._last_demo_cleanup

    @property
    def is_running(self) -> bool:
        """Check if scheduled tasks are running."""
        return self._running


# Global instance
scheduled_task_manager = ScheduledTaskManager()
