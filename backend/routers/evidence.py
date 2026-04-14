from fastapi import APIRouter

from services.evidence_service import get_trade_evidence_snapshot

router = APIRouter()


@router.get("/snapshot")
async def snapshot():
    return await get_trade_evidence_snapshot()
