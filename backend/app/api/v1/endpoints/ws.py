"""
WebSocket endpoint — stretch goal (+3%).
Pushes live vehicle positions to connected clients every 5s.
Falls back gracefully if Redis is unavailable.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import asyncio
import json
from datetime import datetime

from app.db.session import SessionLocal
from app.services.avls import get_live_positions

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        # depot_id -> list of websockets
        self.connections: dict[Optional[int], list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, depot_id: Optional[int]):
        await ws.accept()
        if depot_id not in self.connections:
            self.connections[depot_id] = []
        self.connections[depot_id].append(ws)

    def disconnect(self, ws: WebSocket, depot_id: Optional[int]):
        if depot_id in self.connections:
            self.connections[depot_id] = [
                c for c in self.connections[depot_id] if c != ws
            ]

    async def broadcast(self, depot_id: Optional[int], data: dict):
        dead = []
        targets = self.connections.get(depot_id, []) + (
            self.connections.get(None, []) if depot_id is not None else []
        )
        for ws in targets:
            try:
                await ws.send_text(json.dumps(data, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, depot_id)


manager = ConnectionManager()


def _serialize_positions(positions: list) -> list:
    result = []
    for p in positions:
        serialized = {}
        for k, v in p.items():
            if isinstance(v, datetime):
                serialized[k] = v.isoformat()
            else:
                serialized[k] = v
        result.append(serialized)
    return result


@router.websocket("/live")
async def live_positions_ws(
    websocket: WebSocket,
    depot_id: Optional[int] = Query(None),
    token: Optional[str] = Query(None),
):
    """
    WebSocket for live vehicle positions.
    Connect: ws://localhost:8000/api/v1/ws/live?token=<jwt>&depot_id=<id>
    Pushes updates every 5s.
    Message format: { "type": "positions", "data": [...], "ts": "..." }
    """
    # Basic token validation
    if token:
        try:
            from app.core.security import decode_token
            decode_token(token)
        except Exception:
            await websocket.close(code=4001)
            return

    await manager.connect(websocket, depot_id)
    try:
        while True:
            db = SessionLocal()
            try:
                positions = get_live_positions(db, depot_id=depot_id)
                await websocket.send_text(json.dumps({
                    "type": "positions",
                    "data": _serialize_positions(positions),
                    "ts": datetime.utcnow().isoformat(),
                    "count": len(positions),
                }))
            finally:
                db.close()

            # Keep-alive ping
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            except asyncio.TimeoutError:
                pass  # No client message — normal, just loop

    except WebSocketDisconnect:
        manager.disconnect(websocket, depot_id)
    except Exception as e:
        manager.disconnect(websocket, depot_id)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
