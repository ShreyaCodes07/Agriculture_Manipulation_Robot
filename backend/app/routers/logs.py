"""
Router for Logs & Test Results Matrix
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db, MissionLogDB, TestResultDB
from app.models import TestResultModel, LogEntry

router = APIRouter(prefix="/api", tags=["Logs & Test Verification Matrix"])

@router.get("/logs", response_model=List[LogEntry])
def get_mission_logs(limit: int = 50, db: Session = Depends(get_db)):
    """
    Fetch recent system mission console log entries.
    """
    logs = db.query(MissionLogDB).order_by(MissionLogDB.id.desc()).limit(limit).all()
    return [
        LogEntry(
            id=log.id,
            timestamp=log.timestamp.strftime("%H:%M:%S"),
            level=log.level,
            message=log.message
        )
        for log in logs
    ]

@router.get("/results", response_model=List[TestResultModel])
def get_test_results(db: Session = Depends(get_db)):
    """
    Fetch system test verification matrix results directly from SQLite database.
    """
    results = db.query(TestResultDB).all()
    return [
        TestResultModel(
            test_id=res.test_id,
            scenario=res.scenario,
            expected=res.expected,
            actual=res.actual,
            mode=res.mode,
            status=res.status
        )
        for res in results
    ]
