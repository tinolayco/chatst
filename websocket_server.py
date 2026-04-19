from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI(title="Streamlit Realtime WebSocket Server")


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, room: str) -> None:
        await websocket.accept()
        self.rooms[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str) -> None:
        connections = self.rooms.get(room, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections and room in self.rooms:
            del self.rooms[room]

    async def broadcast(self, room: str, payload: dict[str, Any]) -> None:
        message = json.dumps(payload)
        stale_connections: list[WebSocket] = []

        for connection in self.rooms.get(room, []):
            try:
                await connection.send_text(message)
            except RuntimeError:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection, room)


manager = ConnectionManager()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str) -> None:
    room_name = room.strip() or "demo"
    await manager.connect(websocket, room_name)

    try:
        await manager.broadcast(
            room_name,
            {
                "type": "system",
                "username": "system",
                "message": f"Un navigateur a rejoint le salon '{room_name}'.",
            },
        )

        while True:
            raw_message = await websocket.receive_text()
            data = json.loads(raw_message)

            await manager.broadcast(
                room_name,
                {
                    "type": data.get("type", "message"),
                    "username": data.get("username", "Anonyme"),
                    "message": data.get("message", ""),
                },
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_name)
        await manager.broadcast(
            room_name,
            {
                "type": "system",
                "username": "system",
                "message": f"Un navigateur a quitte le salon '{room_name}'.",
            },
        )
