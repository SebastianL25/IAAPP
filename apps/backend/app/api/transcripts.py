from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.database.session import get_db
from app.models.job import ProcessingJob
from app.models.video import Transcript, TranscriptSegment
from app.workers import job_queue

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])


class SegmentUpdate(BaseModel):
    text: str


@router.post("/{transcript_id}/regenerate")
async def regenerate_transcript(transcript_id: str, db: Session = Depends(get_db)) -> dict:
    transcript = db.get(Transcript, transcript_id)
    if not transcript:
        raise NotFoundError("Transcripcion no encontrada")
    job = ProcessingJob(source_video_id=transcript.source_video_id, job_type="analyze", status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    await job_queue.enqueue(job.id)
    return {"job_id": job.id}


@router.patch("/{transcript_id}/segments/{segment_id}")
def update_segment(transcript_id: str, segment_id: str, payload: SegmentUpdate, db: Session = Depends(get_db)) -> dict:
    segment = db.get(TranscriptSegment, segment_id)
    if not segment or segment.transcript_id != transcript_id:
        raise NotFoundError("Segmento no encontrado")
    segment.text = payload.text
    db.commit()
    return {"ok": True}
