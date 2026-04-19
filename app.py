"""Interface Streamlit du chat temps reel.

Ce fichier ne contient pas le serveur WebSocket lui-meme. Son role est de :
- configurer la page Streamlit ;
- recuperer les informations de connexion utiles a l'utilisateur ;
- lire l'URL du backend WebSocket depuis les secrets Streamlit ;
- instancier un composant Streamlit local qui ouvre la WebSocket, affiche les
  messages et envoie les nouveaux messages.

Le choix d'utiliser un composant Streamlit separe permet de garder `app.py`
concentre sur la configuration et de sortir toute la logique front dans des
fichiers dedies plus faciles a maintenir.
"""

from __future__ import annotations

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from chat_ui_component import chat_ui_component


st.set_page_config(
    page_title="Realtime Browser Chat",
    page_icon="💬",
    layout="wide",
)

st.title("Chat temps reel entre deux navigateurs")
st.caption("Ouvrez cette page dans deux navigateurs ou deux onglets et rejoignez le meme salon.")


def get_default_ws_url() -> str:
    """Retourne l'URL WebSocket configuree pour l'application.

    Streamlit expose les secrets via `st.secrets`, mais l'acces peut lever une
    exception si aucun fichier `.streamlit/secrets.toml` n'est present. Cette
    fonction centralise donc la lecture de `websocket_url` et applique un
    fallback local raisonnable pour le developpement.
    """

    try:
        return st.secrets["websocket_url"]
    except (KeyError, StreamlitSecretNotFoundError):
        return "ws://localhost:8765/ws"


default_ws_url = get_default_ws_url()

# La sidebar ne contient que les informations encore pertinentes cote UI.
# L'adresse du backend est imposee par la configuration serveur et n'est plus
# editable depuis l'interface.
with st.sidebar:
    st.header("Connexion")
    room = st.text_input("Nom du salon", value="demo")
    username = st.text_input("Pseudo", value="navigateur")
    ws_url = default_ws_url
    st.caption(f"Serveur WebSocket: {ws_url}")
    st.markdown(
        "Lancez le serveur WebSocket puis partagez le meme nom de salon dans les deux navigateurs. L'URL WebSocket est lue depuis le secret Streamlit."
    )

# Le composant Streamlit local encapsule tout le frontend du chat.
chat_ui_component(
    room=room,
    username=username,
    ws_url=ws_url,
    height=560,
    key=f"chat-ui-{room}",
)

# Ce bloc rappelle les commandes de lancement utiles pendant le developpement.
st.markdown("### Lancement")
st.code(
    "uvicorn websocket_server:app --host 0.0.0.0 --port 8765\nstreamlit run app.py --server.port 8501"
)
