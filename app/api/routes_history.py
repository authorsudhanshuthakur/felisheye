import io
import csv
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, Response, HTTPException
from app.db.database import get_history, clear_history

router = APIRouter(prefix="/api/history", tags=["Recognition History"])

@router.get("")
async def list_history(
    status: Optional[str] = Query(None, description="Filter by status (HIGH_CONFIDENCE, POSSIBLE_MATCH, LOW_CONFIDENCE, UNKNOWN)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Retrieves paginated recognition event history."""
    items, total = get_history(limit=limit, offset=offset, status_filter=status)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": items
    }

@router.delete("")
async def clear_all_history():
    """Clears all logged recognition events."""
    deleted_count = clear_history()
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Cleared {deleted_count} recognition history events."
    }

@router.get("/export")
async def export_history(format: str = Query("json", pattern="^(json|csv)$")):
    """Exports history logs as JSON or CSV."""
    items, _ = get_history(limit=5000, offset=0)
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "timestamp", "result_status", "matched_person_id", 
            "matched_person_name", "similarity_score", "distance", "source"
        ])
        writer.writeheader()
        for it in items:
            writer.writerow({
                "id": it["id"],
                "timestamp": it["timestamp"],
                "result_status": it["result_status"],
                "matched_person_id": it["matched_person_id"] or "",
                "matched_person_name": it["matched_person_name"] or "",
                "similarity_score": it["similarity_score"] if it["similarity_score"] is not None else "",
                "distance": it["distance"] if it["distance"] is not None else "",
                "source": it["source"]
            })
        csv_data = output.getvalue()
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=feliseye_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    else:
        json_data = json.dumps(items, indent=2)
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=feliseye_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
        )
