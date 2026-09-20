from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws/jobs")
async def ws_jobs(websocket: WebSocket) -> None:
    await manager.connect_global(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_global(websocket)


@router.websocket("/api/ws/projects/{project_id}")
async def ws_project(websocket: WebSocket, project_id: str) -> None:
    await manager.connect_project(websocket, project_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_project(websocket, project_id)
