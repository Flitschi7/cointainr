import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.conversion_cache import ConversionCache
from app.models.price_cache import PriceCache
from app.models.session import Session
from app.core.auth_config import auth_settings

logger = logging.getLogger(__name__)


class DemoService:
    """
    Service for managing demo mode functionality including database cleanup
    and demo mode initialization.
    """

    def __init__(self):
        self.cleanup_time = self._parse_cleanup_time(auth_settings.DEMO_CLEANUP_TIME)
        self.preserve_asset_id = auth_settings.DEMO_PRESERVE_ASSET_ID
        self._cleanup_task: Optional[asyncio.Task] = None
        self._last_cleanup_date: Optional[str] = None

    def _parse_cleanup_time(self, time_str: str) -> time:
        """
        Parse cleanup time string (HH:MM) into a time object.

        Args:
            time_str: Time string in HH:MM format

        Returns:
            time object representing the cleanup time
        """
        try:
            hours, minutes = time_str.split(":")
            return time(int(hours), int(minutes))
        except (ValueError, IndexError):
            logger.warning(f"Invalid cleanup time format: {time_str}. Using 00:00")
            return time(0, 0)

    async def initialize_demo_mode(self) -> None:
        """
        Initialize demo mode by setting up necessary configurations.
        Note: Cleanup scheduling is now handled by the ScheduledTaskManager.
        """
        if not auth_settings.DEMO_MODE:
            logger.debug("Demo mode not enabled, skipping initialization")
            return

        logger.info("Initializing demo mode")

        # Check if cleanup is needed on startup
        await self._check_and_perform_cleanup()

        logger.info(
            "Demo mode initialized successfully (cleanup scheduling handled by ScheduledTaskManager)"
        )

    async def start_cleanup_scheduler(self) -> None:
        """
        Start the daily cleanup scheduler that runs database cleanup
        at the configured time each day.
        """
        if not auth_settings.DEMO_MODE:
            logger.debug("Demo mode not enabled, cleanup scheduler not started")
            return

        if self._cleanup_task and not self._cleanup_task.done():
            logger.debug("Cleanup scheduler already running")
            return

        logger.info(
            f"Starting demo mode cleanup scheduler for {auth_settings.DEMO_CLEANUP_TIME}"
        )
        self._cleanup_task = asyncio.create_task(self._cleanup_scheduler_loop())

    async def stop_cleanup_scheduler(self) -> None:
        """
        Stop the cleanup scheduler task.
        """
        if self._cleanup_task and not self._cleanup_task.done():
            logger.info("Stopping demo mode cleanup scheduler")
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_scheduler_loop(self) -> None:
        """
        Main loop for the cleanup scheduler that waits until the configured
        cleanup time and then performs database cleanup.
        """
        while True:
            try:
                # Calculate seconds until next cleanup time
                seconds_until_cleanup = self._calculate_seconds_until_cleanup()

                logger.debug(f"Next cleanup in {seconds_until_cleanup} seconds")

                # Wait until cleanup time
                await asyncio.sleep(seconds_until_cleanup)

                # Perform cleanup
                await self._check_and_perform_cleanup()

            except asyncio.CancelledError:
                logger.info("Cleanup scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup scheduler: {e}")
                # Wait 1 hour before retrying on error
                await asyncio.sleep(3600)

    def _calculate_seconds_until_cleanup(self) -> int:
        """
        Calculate the number of seconds until the next cleanup time.

        Returns:
            Number of seconds until next cleanup
        """
        now = datetime.now()
        cleanup_datetime = datetime.combine(now.date(), self.cleanup_time)

        # If cleanup time has passed today, schedule for tomorrow
        if cleanup_datetime <= now:
            cleanup_datetime += timedelta(days=1)

        return int((cleanup_datetime - now).total_seconds())

    async def _check_and_perform_cleanup(self) -> None:
        """
        Check if cleanup is needed (hasn't been done today) and perform it.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        if self._last_cleanup_date == today:
            logger.debug("Cleanup already performed today, skipping")
            return

        logger.info("Performing daily demo mode database cleanup")
        success = await self.cleanup_database()

        if success:
            self._last_cleanup_date = today
            logger.info("Demo mode database cleanup completed successfully")
        else:
            logger.error("Demo mode database cleanup failed")

    async def cleanup_database(self) -> bool:
        """
        Perform database cleanup by removing all data except the preserved asset.

        Returns:
            True if cleanup was successful, False otherwise
        """
        if not auth_settings.DEMO_MODE:
            logger.warning("Attempted to cleanup database when not in demo mode")
            return False

        try:
            async with SessionLocal() as db:
                # Start transaction
                async with db.begin():
                    # Clean up sessions (except current ones might be needed)
                    await self._cleanup_sessions(db)

                    # Clean up cache tables
                    await self._cleanup_cache_tables(db)

                    # Clean up assets (preserve the specified asset)
                    await self._cleanup_assets(db)

                    # Commit transaction
                    await db.commit()

                logger.info(
                    f"Database cleanup completed, preserved asset ID {self.preserve_asset_id}"
                )
                return True

        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            return False

    async def _cleanup_sessions(self, db: AsyncSession) -> None:
        """
        Clean up expired and old sessions.

        Args:
            db: Database session
        """
        try:
            # Delete expired sessions
            result = await db.execute(
                delete(Session).where(Session.expires_at < datetime.utcnow())
            )
            expired_count = result.rowcount

            # Delete sessions older than 7 days (keep recent ones for active users)
            week_ago = datetime.utcnow() - timedelta(days=7)
            result = await db.execute(
                delete(Session).where(Session.created_at < week_ago)
            )
            old_count = result.rowcount

            logger.debug(
                f"Cleaned up {expired_count} expired sessions and {old_count} old sessions"
            )

        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {e}")
            raise

    async def _cleanup_cache_tables(self, db: AsyncSession) -> None:
        """
        Clean up cache tables (price cache and conversion cache).

        Args:
            db: Database session
        """
        try:
            # Clean up price cache
            result = await db.execute(delete(PriceCache))
            price_count = result.rowcount

            # Clean up conversion cache
            result = await db.execute(delete(ConversionCache))
            conversion_count = result.rowcount

            logger.debug(
                f"Cleaned up {price_count} price cache entries and {conversion_count} conversion cache entries"
            )

        except Exception as e:
            logger.error(f"Failed to cleanup cache tables: {e}")
            raise

    async def _cleanup_assets(self, db: AsyncSession) -> None:
        """
        Clean up assets table while preserving the specified asset.

        Args:
            db: Database session
        """
        try:
            # Verify the preserved asset exists
            preserved_asset = await db.execute(
                select(Asset).where(Asset.id == self.preserve_asset_id)
            )
            asset = preserved_asset.scalar_one_or_none()

            if asset:
                logger.debug(f"Preserving asset: {asset.name} (ID: {asset.id})")
            else:
                logger.warning(
                    f"Asset with ID {self.preserve_asset_id} not found, will be created if needed"
                )

            # Delete all assets except the preserved one
            result = await db.execute(
                delete(Asset).where(Asset.id != self.preserve_asset_id)
            )
            deleted_count = result.rowcount

            logger.debug(
                f"Cleaned up {deleted_count} assets, preserved asset ID {self.preserve_asset_id}"
            )

        except Exception as e:
            logger.error(f"Failed to cleanup assets: {e}")
            raise

    async def ensure_demo_asset_exists(self) -> None:
        """
        Ensure that the demo asset (ID 1) exists for demo mode.
        Creates a default asset if it doesn't exist.
        """
        if not auth_settings.DEMO_MODE:
            return

        try:
            async with SessionLocal() as db:
                # Check if the preserved asset exists
                result = await db.execute(
                    select(Asset).where(Asset.id == self.preserve_asset_id)
                )
                asset = result.scalar_one_or_none()

                if not asset:
                    # Create a default demo asset
                    from app.models.asset import AssetType

                    demo_asset = Asset(
                        id=self.preserve_asset_id,
                        type=AssetType.CASH,
                        name="Demo Cash",
                        assetname="Demo Portfolio",
                        quantity=1000.0,
                        currency="USD",
                        purchase_price=1.0,
                        buy_currency="USD",
                    )

                    db.add(demo_asset)
                    await db.commit()

                    logger.info(f"Created demo asset with ID {self.preserve_asset_id}")
                else:
                    logger.debug(
                        f"Demo asset with ID {self.preserve_asset_id} already exists"
                    )

        except Exception as e:
            logger.error(f"Failed to ensure demo asset exists: {e}")

    async def get_cleanup_status(self) -> dict:
        """
        Get the current status of the demo mode cleanup system.

        Returns:
            Dictionary containing cleanup status information
        """
        if not auth_settings.DEMO_MODE:
            return {"demo_mode": False, "message": "Demo mode not enabled"}

        now = datetime.now()
        next_cleanup = datetime.combine(now.date(), self.cleanup_time)
        if next_cleanup <= now:
            next_cleanup += timedelta(days=1)

        return {
            "demo_mode": True,
            "cleanup_time": auth_settings.DEMO_CLEANUP_TIME,
            "preserve_asset_id": self.preserve_asset_id,
            "last_cleanup_date": self._last_cleanup_date,
            "next_cleanup": next_cleanup.isoformat(),
            "scheduler_running": self._cleanup_task is not None
            and not self._cleanup_task.done(),
        }


# Global demo service instance
demo_service = DemoService()
