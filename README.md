# Chat Streamlit + WebSocket

Cette application permet d'echanger des messages en temps reel entre deux navigateurs via une interface Streamlit et un serveur WebSocket Python. Elle prend en charge les messages publics dans un salon ainsi que les messages prives entre utilisateurs connectes au meme salon.

Le frontend de chat est maintenant implemente comme un composant Streamlit local dans [chat_ui_component/__init__.py](chat_ui_component/__init__.py) avec ses fichiers frontend separes dans [chat_ui_component/frontend/index.html](chat_ui_component/frontend/index.html), [chat_ui_component/frontend/styles.css](chat_ui_component/frontend/styles.css) et [chat_ui_component/frontend/main.js](chat_ui_component/frontend/main.js).

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Demarrage

Commande unique sous Windows:

```powershell
.\start.ps1
```

Ce script lit `.streamlit/secrets.toml` si le fichier existe, recupere le port de `websocket_url`, puis ouvre deux fenetres PowerShell: une pour Uvicorn et une pour Streamlit.

L'interface Streamlit n'affiche plus de champ pour saisir l'URL WebSocket. L'application utilise directement la valeur de `websocket_url` definie dans `.streamlit/secrets.toml`.

Demarrage manuel si besoin:

Lancer le serveur WebSocket dans un terminal:

```powershell
uvicorn websocket_server:app --host 0.0.0.0 --port 9876
```

Lancer Streamlit dans un second terminal:

```powershell
streamlit run app.py --server.port 8501
```

Le fichier .streamlit/secrets.toml est optionnel. Avec la configuration actuelle, l'application utilise automatiquement ws://localhost:9876/ws. Sans ce fichier, l'application utilise automatiquement ws://localhost:8765/ws par defaut.

Ouvrir ensuite l'application dans deux navigateurs ou deux onglets, saisir le meme salon, puis envoyer des messages.

## Utilisation

- Chaque utilisateur choisit un pseudo dans un salon donne.
- Le mode Message public diffuse le message a tous les participants du salon.
- Le mode Message prive affiche la liste des autres utilisateurs connectes et envoie le message uniquement au destinataire choisi.
- Deux utilisateurs ne peuvent pas utiliser le meme pseudo dans le meme salon.

## Notes

- L'URL WebSocket configuree via `.streamlit/secrets.toml` est `ws://localhost:9876/ws`.
- Sans `.streamlit/secrets.toml`, l'URL WebSocket par defaut reste `ws://localhost:8765/ws`.
- Pour un usage reseau local, remplacez `localhost` par l'IP de la machine qui heberge le serveur WebSocket.
