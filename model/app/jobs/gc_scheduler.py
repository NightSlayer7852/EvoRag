import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import GC_INTERVAL_HOURS
from app.services.gc_service import run_garbage_collection

logger = logging.getLogger("evorag.gc_scheduler")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

_scheduler = None


def start_gc_scheduler() -> BackgroundScheduler:
    """
    Initializes and starts the periodic APScheduler background job for EvoRAG garbage collection.
    Runs every GC_INTERVAL_HOURS.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("[GCScheduler] Scheduler is already running.")
        return _scheduler

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        func=run_garbage_collection,
        trigger="interval",
        hours=GC_INTERVAL_HOURS,
        id="evorag_gc_job",
        name="EvoRAG Vector Memory Garbage Collection",
        replace_existing=True
    )
    _scheduler.start()
    logger.info(f"[GCScheduler] Started background GC scheduler running every {GC_INTERVAL_HOURS} hours.")
    return _scheduler
