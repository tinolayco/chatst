from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI(title="Streamlit Realtime WebSocket Server")


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    def register(self, websocket: WebSocket, room: str, username: str) -> bool:
        room_connections = self.rooms.setdefault(room, {})
        if username in room_connections:
            return False

        room_connections[username] = websocket
        return True

    def disconnect(self, websocket: WebSocket, room: str) -> str | None:
        room_connections = self.rooms.get(room, {})

        for username, connection in list(room_connections.items()):
            if connection == websocket:
                del room_connections[username]
                if not room_connections and room in self.rooms:
                    del self.rooms[room]
                return username

        if not room_connections and room in self.rooms:
            del self.rooms[room]
        return None

    def list_users(self, room: str) -> list[str]:
        return sorted(self.rooms.get(room, {}).keys(), key=str.lower)

    async def send_to_user(self, room: str, username: str, payload: dict[str, Any]) -> bool:
        connection = self.rooms.get(room, {}).get(username)
        if connection is None:
            return False

        try:
            await connection.send_text(json.dumps(payload))
            return True
        except RuntimeError:
            self.disconnect(connection, room)
            return False

    async def broadcast(self, room: str, payload: dict[str, Any]) -> None:
        message = json.dumps(payload)
        stale_connections: list[WebSocket] = []

        for connection in self.rooms.get(room, {}).values():
            try:
                await connection.send_text(message)
            except RuntimeError:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection, room)

    async def broadcast_user_list(self, room: str) -> None:
        await self.broadcast(
            room,
            {
                "type": "presence",
                "users": self.list_users(room),
            },
        )


manager = ConnectionManager()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str) -> None:
    room_name = room.strip() or "demo"
    await manager.connect(websocket)
    current_username: str | None = None

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                data = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "system",
                            "username": "system",
                            "message": "Message JSON invalide recu par le serveur.",
                        }
                    )
                )
                continue

            event_type = data.get("type", "message")

            if event_type == "join":
                requested_username = str(data.get("username", "")).strip()
                if not requested_username:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "system",
                                "username": "system",
                                "message": "Le pseudo ne peut pas etre vide.",
                            }
                        )
                    )
                    continue

                if current_username == requested_username:
                    await manager.broadcast_user_list(room_name)
                    continue

                if current_username is not None:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "system",
                                "username": "system",
                                "message": "Le pseudo de cette connexion est deja initialise.",
                            }
                        )
                    )
                    continue

                if not manager.register(websocket, room_name, requested_username):
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "system",
                                "username": "system",
                                "message": f"Le pseudo '{requested_username}' est deja utilise dans ce salon.",
                            }
                        )
                    )
                    continue

                current_username = requested_username
                await manager.broadcast(
                    room_name,
                    {
                        "type": "system",
                        "username": "system",
                        "message": f"{current_username} a rejoint le salon '{room_name}'.",
                    },
                )
                await manager.broadcast_user_list(room_name)
                continue

            if current_username is None:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "system",
                            "username": "system",
                            "message": "La connexion doit d'abord annoncer un pseudo.",
                        }
                    )
                )
                continue

            message = str(data.get("message", "")).strip()
            if not message:
                continue

            if event_type == "private":
                target_username = str(data.get("target", "")).strip()
                if not target_username:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "system",
                                "username": "system",
                                "message": "Choisissez un destinataire pour le message prive.",
                            }
                        )
                    )
                    continue

                if target_username == current_username:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "system",
                                "username": "system",
                                "message": "Vous ne pouvez pas vous envoyer un message prive a vous-meme.",
                            }
                        )
                    )
                    continue

                payload = {
                    "type": "private",
                    "username": current_username,
                    "target": target_username,
                    "message": message,
                }
                delivered = await manager.send_to_user(room_name, target_username, payload)
                if not delivered:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "system",
                                "username": "system",
                                "message": f"Le destinataire '{target_username}' n'est pas connecte.",
                            }
                        )
                    )
                    await manager.broadcast_user_list(room_name)
                    continue

                await manager.send_to_user(room_name, current_username, payload)
                continue

            await manager.broadcast(
                room_name,
                {
                    "type": "message",
                    "username": current_username,
                    "message": message,
                },
            )
    except WebSocketDisconnect:
        disconnected_username = manager.disconnect(websocket, room_name)
        if disconnected_username is not None:
            await manager.broadcast(
                room_name,
                {
                    "type": "system",
                    "username": "system",
                    "message": f"{disconnected_username} a quitte le salon '{room_name}'.",
                },
            )
            await manager.broadcast_user_list(room_name)
