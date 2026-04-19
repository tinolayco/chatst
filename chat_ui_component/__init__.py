from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components


_COMPONENT = components.declare_component(
    "chat_ui_component",
    path=str(Path(__file__).resolve().parent / "frontend"),
)


def chat_ui_component(
    *,
    room: str,
    username: str,
    ws_url: str,
    height: int = 560,
    key: str | None = None,
) -> None:
    """Render the realtime chat component.

    Parameters
    ----------
    room:
        Nom du salon courant.
    username:
        Pseudo suggere par l'application Streamlit.
    ws_url:
        URL de base du backend WebSocket, sans le nom du salon final.
    height:
        Hauteur de l'iframe du composant dans Streamlit.
    key:
        Cle Streamlit facultative pour stabiliser l'instance du composant.
    """

    _COMPONENT(
        room=room,
        username=username,
        ws_url=ws_url,
        key=key,
        default=None,
        height=height,
    )