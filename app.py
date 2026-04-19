"""Interface Streamlit du chat temps reel.

Ce fichier ne contient pas le serveur WebSocket lui-meme. Son role est de :
- configurer la page Streamlit ;
- recuperer les informations de connexion utiles a l'utilisateur ;
- lire l'URL du backend WebSocket depuis les secrets Streamlit ;
- injecter un composant HTML/JavaScript autonome qui ouvre la WebSocket,
  affiche les messages et envoie les nouveaux messages.

Le choix d'utiliser `components.html` permet de garder Streamlit comme couche UI
simple, tout en deleguant la communication temps reel a un client JavaScript
embarque dans la page.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
from streamlit.errors import StreamlitSecretNotFoundError


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


# Le composant HTML embarque contient tout le client de chat : structure,
# styles et logique JavaScript WebSocket. Les valeurs Streamlit sont injectees
# dans la chaine pour personnaliser le salon, le pseudo et l'URL du backend.
chat_component = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    html {{
      height: 100%;
    }}

    :root {{
      --bg: linear-gradient(135deg, #fff6e8 0%, #f3f7ff 100%);
      --panel: rgba(255, 255, 255, 0.88);
      --border: rgba(21, 37, 68, 0.12);
      --accent: #0f766e;
      --accent-2: #1d4ed8;
      --text: #0f172a;
      --muted: #52607a;
      --self: #dff7f2;
      --other: #eef4ff;
      --system: #fff4da;
      --shadow: 0 24px 80px rgba(15, 23, 42, 0.12);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      height: 100%;
      font-family: Georgia, "Times New Roman", serif;
      background: var(--bg);
      color: var(--text);
      overflow: hidden;
    }}

    .shell {{
      border: 1px solid var(--border);
      border-radius: 24px;
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
      height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr auto;
      overflow: hidden;
    }}

    .header {{
      padding: 18px 22px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }}

    .title {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .title strong {{
      font-size: 1.1rem;
      letter-spacing: 0.02em;
    }}

    .title span, .status {{
      color: var(--muted);
      font-size: 0.92rem;
    }}

    #messages {{
      padding: 22px;
      min-height: 0;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .message {{
      padding: 14px 16px;
      border-radius: 18px;
      max-width: min(80%, 720px);
      border: 1px solid var(--border);
      animation: rise 180ms ease-out;
    }}

    .message.self {{
      align-self: flex-end;
      background: var(--self);
    }}

    .message.other {{
      align-self: flex-start;
      background: var(--other);
    }}

    .message.system {{
      align-self: center;
      background: var(--system);
      max-width: 90%;
    }}

    .meta {{
      font-size: 0.82rem;
      color: var(--muted);
      margin-bottom: 6px;
    }}

    .body {{
      font-size: 1rem;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    .composer {{
      padding: 18px;
      border-top: 1px solid var(--border);
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      background: rgba(255,255,255,0.55);
    }}

    textarea {{
      width: 100%;
      resize: none;
      min-height: 64px;
      max-height: 180px;
      border-radius: 18px;
      border: 1px solid var(--border);
      padding: 14px 16px;
      font: inherit;
      color: var(--text);
      background: white;
    }}

    button {{
      border: 0;
      border-radius: 18px;
      padding: 0 22px;
      font: inherit;
      min-width: 132px;
      cursor: pointer;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: white;
      transition: transform 120ms ease, opacity 120ms ease;
    }}

    button:hover {{ transform: translateY(-1px); }}
    button:disabled {{ opacity: 0.45; cursor: not-allowed; transform: none; }}

    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(8px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    @media (max-width: 720px) {{
      .shell {{ height: 100vh; border-radius: 18px; }}
      .composer {{ grid-template-columns: 1fr; }}
      button {{ min-height: 52px; }}
      .message {{ max-width: 100%; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="header">
      <div class="title">
        <strong>Salon: {room}</strong>
        <span>Utilisateur: {username}</span>
      </div>
      <div id="status" class="status">Connexion...</div>
    </div>

    <div id="messages"></div>

    <div class="composer">
      <textarea id="messageInput" placeholder="Tapez un message puis validez..."></textarea>
      <button id="sendButton">Envoyer</button>
    </div>
  </div>

  <script>
    const room = {room!r};
    const username = {username!r};
    // wsBase contient la base configuree, par exemple ws://localhost:9876/ws.
    // Le nom du salon est ajoute ensuite pour construire l'URL finale.
    const wsBase = {ws_url!r}.replace(/\/$/, "");
    const statusNode = document.getElementById("status");
    const messagesNode = document.getElementById("messages");
    const inputNode = document.getElementById("messageInput");
    const sendButton = document.getElementById("sendButton");

    // Une connexion WebSocket par onglet et par salon.
    const socket = new WebSocket(`${{wsBase}}/${{encodeURIComponent(room)}}`);

    const setStatus = (text) => {{
      statusNode.textContent = text;
    }};

    const scrollToBottom = () => {{
      messagesNode.scrollTop = messagesNode.scrollHeight;
    }};

    const addMessage = (payload) => {{
      const wrapper = document.createElement("div");
      // Les messages systeme sont centres. Les messages utilisateur sont
      // alignes a gauche ou a droite selon leur auteur.
      const type = payload.type === "system" ? "system" : (payload.username === username ? "self" : "other");
      wrapper.className = `message ${{type}}`;

      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = type === "system" ? "system" : payload.username;

      const body = document.createElement("div");
      body.className = "body";
      body.textContent = payload.message;

      wrapper.appendChild(meta);
      wrapper.appendChild(body);
      messagesNode.appendChild(wrapper);
      scrollToBottom();
    }};

    const sendMessage = () => {{
      const message = inputNode.value.trim();
      if (!message || socket.readyState !== WebSocket.OPEN) {{
        return;
      }}

      // Le backend attend un JSON simple contenant le type, l'auteur et le texte.
      socket.send(JSON.stringify({{
        type: "message",
        username,
        message,
      }}));
      inputNode.value = "";
      inputNode.focus();
    }};

    socket.addEventListener("open", () => {{
      setStatus("Connecte");
      sendButton.disabled = false;
    }});

    socket.addEventListener("close", () => {{
      setStatus("Deconnecte");
      sendButton.disabled = true;
      addMessage({{ type: "system", message: "Connexion fermee.", username: "system" }});
    }});

    socket.addEventListener("error", () => {{
      setStatus("Erreur de connexion");
      sendButton.disabled = true;
    }});

    socket.addEventListener("message", (event) => {{
      try {{
        const payload = JSON.parse(event.data);
        addMessage(payload);
      }} catch (error) {{
        // Le client reste resilient si le backend renvoie un message invalide.
        addMessage({{ type: "system", message: "Message invalide recu.", username: "system" }});
      }}
    }});

    sendButton.addEventListener("click", sendMessage);
    inputNode.addEventListener("keydown", (event) => {{
      if (event.key === "Enter" && !event.shiftKey) {{
        event.preventDefault();
        sendMessage();
      }}
    }});

    sendButton.disabled = true;
  </script>
</body>
</html>
"""

# Streamlit affiche le client HTML dans un iframe. La hauteur doit rester assez
# grande pour le chat, tout en laissant de la place au reste de la page.
components.html(chat_component, height=560, scrolling=False)

# Ce bloc rappelle les commandes de lancement utiles pendant le developpement.
st.markdown("### Lancement")
st.code(
    "uvicorn websocket_server:app --host 0.0.0.0 --port 8765\nstreamlit run app.py --server.port 8501"
)
