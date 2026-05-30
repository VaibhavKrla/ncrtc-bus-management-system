"""
SLA Monitor — stretch goal (+2%).
Runs alongside tick script. Every 60s checks open/in-progress incidents
and logs a breach event if SLA time has been exceeded.
"""
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SLA_MINUTES = {"P1": 60, "P2": 240, "P3": 1440}


def check_sla_breaches(db):
    """
    Check all open/acknowledged/in_progress incidents for SLA breaches.
    Logs a breach event the first time the SLA is exceeded.
    """
    from app.models.models import Incident, IncidentEvent, IncidentStatus

    breachable_statuses = [
        IncidentStatus.open,
        IncidentStatus.acknowledged,
        IncidentStatus.in_progress,
    ]

    incidents = db.query(Incident).filter(
        Incident.status.in_(breachable_statuses)
    ).all()

    breach_count = 0
    for inc in incidents:
        sla_mins = SLA_MINUTES.get(str(inc.severity).replace("IncidentSeverity.", ""))
        if not sla_mins:
            continue

        elapsed_mins = (datetime.utcnow() - inc.created_at).total_seconds() / 60
        if elapsed_mins <= sla_mins:
            continue

        # Check if breach event already logged
        already_logged = db.query(IncidentEvent).filter(
            IncidentEvent.incident_id == inc.id,
            IncidentEvent.note.like("SLA BREACH%"),
        ).first()

        if already_logged:
            continue

        # Log the breach
        breach_event = IncidentEvent(
            incident_id=inc.id,
            user_id=None,
            note=f"SLA BREACH: {inc.severity} incident exceeded {sla_mins} minute SLA "
                 f"(elapsed: {int(elapsed_mins)} min). Immediate attention required.",
        )
        db.add(breach_event)
        breach_count += 1
        logger.warning(
            f"SLA BREACH: Incident #{inc.id} [{inc.severity}] "
            f"'{inc.title}' — {int(elapsed_mins)} min elapsed (SLA: {sla_mins} min)"
        )

    if breach_count > 0:
        db.commit()

    return breach_count


def run_sla_monitor():
    """Runs in a loop, checking SLA every 60 seconds."""
    from app.db.session import SessionLocal
    logging.basicConfig(level=logging.INFO)
    logger.info("🕐 SLA monitor started — checking every 60s")

    while True:
        db = SessionLocal()
        try:
            breaches = check_sla_breaches(db)
            if breaches:
                logger.warning(f"  Found {breaches} new SLA breach(es)")
        except Exception as e:
            logger.error(f"SLA monitor error: {e}")
        finally:
            db.close()
        time.sleep(60)


if __name__ == "__main__":
    run_sla_monitor()
