const StreamlitBridge = {
  setFrameHeight(height = document.documentElement.scrollHeight) {
    window.parent.postMessage(
      {
        isStreamlitMessage: true,
        type: "streamlit:setFrameHeight",
        height,
      },
      "*"
    )
  },

  setComponentReady() {
    window.parent.postMessage(
      {
        isStreamlitMessage: true,
        type: "streamlit:componentReady",
        apiVersion: 1,
      },
      "*"
    )
  },
}

const state = {
  activeUsers: [],
  room: "demo",
  username: "navigateur",
  wsBase: "ws://localhost:8765/ws",
  socket: null,
  connectionKey: "",
}

const roomLabelNode = document.getElementById("roomLabel")
const usernameLabelNode = document.getElementById("usernameLabel")
const statusNode = document.getElementById("status")
const messagesNode = document.getElementById("messages")
const inputNode = document.getElementById("messageInput")
const sendButton = document.getElementById("sendButton")
const modeSelect = document.getElementById("modeSelect")
const recipientSelect = document.getElementById("recipientSelect")

function setStatus(text) {
  statusNode.textContent = text
}

function scrollToBottom() {
  messagesNode.scrollTop = messagesNode.scrollHeight
}

function storageKeyForRoom(room) {
  return `chat_streamlit_websocket_username_${room}`
}

function syncRecipientOptions() {
  const availableRecipients = state.activeUsers.filter((name) => name !== state.username)
  const previousValue = recipientSelect.value

  recipientSelect.innerHTML = ""

  const placeholder = document.createElement("option")
  placeholder.value = ""
  placeholder.textContent = availableRecipients.length
    ? "Choisissez un destinataire"
    : "Aucun destinataire disponible"
  recipientSelect.appendChild(placeholder)

  for (const recipient of availableRecipients) {
    const option = document.createElement("option")
    option.value = recipient
    option.textContent = recipient
    recipientSelect.appendChild(option)
  }

  if (availableRecipients.includes(previousValue)) {
    recipientSelect.value = previousValue
  } else {
    recipientSelect.value = ""
  }

  recipientSelect.disabled = !availableRecipients.length
}

function syncComposerMode() {
  const isPrivate = modeSelect.value === "private"
  recipientSelect.hidden = !isPrivate
  if (!isPrivate) {
    recipientSelect.value = ""
  }
}

function addMessage(payload) {
  const wrapper = document.createElement("div")
  const type = payload.type === "system" ? "system" : (payload.username === state.username ? "self" : "other")
  wrapper.className = `message ${type}`

  if (payload.type === "private") {
    wrapper.classList.add("private")
  }

  const meta = document.createElement("div")
  meta.className = "meta"
  if (type === "system") {
    meta.textContent = "system"
  } else if (payload.type === "private") {
    meta.textContent = payload.username === state.username
      ? `${payload.username} -> ${payload.target} (prive)`
      : `${payload.username} -> vous (prive)`
  } else {
    meta.textContent = payload.username
  }

  const body = document.createElement("div")
  body.className = "body"
  body.textContent = payload.message

  wrapper.appendChild(meta)
  wrapper.appendChild(body)
  messagesNode.appendChild(wrapper)
  scrollToBottom()
  StreamlitBridge.setFrameHeight(560)
}

function sendMessage() {
  const message = inputNode.value.trim()
  if (!message || !state.socket || state.socket.readyState !== WebSocket.OPEN) {
    return
  }

  const mode = modeSelect.value
  const target = recipientSelect.value
  if (mode === "private" && !target) {
    addMessage({ type: "system", username: "system", message: "Choisissez un destinataire pour envoyer un message prive." })
    return
  }

  state.socket.send(JSON.stringify({
    type: mode,
    username: state.username,
    message,
    target,
  }))
  inputNode.value = ""
  inputNode.focus()
}

function closeSocket() {
  if (state.socket && (state.socket.readyState === WebSocket.OPEN || state.socket.readyState === WebSocket.CONNECTING)) {
    state.socket.close()
  }
  state.socket = null
}

function connectSocket() {
  closeSocket()
  state.activeUsers = []
  syncRecipientOptions()

  const socket = new WebSocket(`${state.wsBase.replace(/\/$/, "")}/${encodeURIComponent(state.room)}`)
  state.socket = socket

  socket.addEventListener("open", () => {
    if (state.socket !== socket) {
      return
    }
    setStatus("Connecte - inscription...")
    socket.send(JSON.stringify({ type: "join", username: state.username }))
    sendButton.disabled = false
    syncComposerMode()
  })

  socket.addEventListener("close", () => {
    if (state.socket !== socket) {
      return
    }
    setStatus("Deconnecte")
    sendButton.disabled = true
    addMessage({ type: "system", message: "Connexion fermee.", username: "system" })
  })

  socket.addEventListener("error", () => {
    if (state.socket !== socket) {
      return
    }
    setStatus("Erreur de connexion")
    sendButton.disabled = true
  })

  socket.addEventListener("message", (event) => {
    if (state.socket !== socket) {
      return
    }
    try {
      const payload = JSON.parse(event.data)
      if (payload.type === "presence") {
        state.activeUsers = Array.isArray(payload.users) ? payload.users : []
        syncRecipientOptions()
        setStatus(`Connecte - ${state.activeUsers.length} utilisateur(s)`)
        return
      }
      addMessage(payload)
    } catch (error) {
      addMessage({ type: "system", message: "Message invalide recu.", username: "system" })
    }
  })
}

function applyArgs(args) {
  state.room = args.room || "demo"
  state.wsBase = args.ws_url || "ws://localhost:8765/ws"

  const configuredUsername = (args.username || "navigateur").trim()
  const storedUsername = window.localStorage.getItem(storageKeyForRoom(state.room))?.trim() || ""
  state.username = configuredUsername && configuredUsername !== "navigateur"
    ? configuredUsername
    : storedUsername || configuredUsername || "navigateur"

  window.localStorage.setItem(storageKeyForRoom(state.room), state.username)
  roomLabelNode.textContent = `Salon: ${state.room}`
  usernameLabelNode.textContent = `Utilisateur: ${state.username}`
}

function onRender(event) {
  if (!event.data || event.data.type !== "streamlit:render") {
    return
  }

  const data = event.data
  const previousConnectionKey = state.connectionKey
  applyArgs(data.args)
  state.connectionKey = `${state.room}::${state.username}::${state.wsBase}`
  if (state.connectionKey !== previousConnectionKey) {
    messagesNode.innerHTML = ""
    connectSocket()
  }
  StreamlitBridge.setFrameHeight(data.args.height || 560)
}

sendButton.addEventListener("click", sendMessage)
modeSelect.addEventListener("change", syncComposerMode)
inputNode.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
})

syncRecipientOptions()
syncComposerMode()
sendButton.disabled = true

window.addEventListener("message", onRender)
StreamlitBridge.setComponentReady()
StreamlitBridge.setFrameHeight(560)