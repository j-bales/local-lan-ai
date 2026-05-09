const statusEl = document.getElementById('status');
const inputEl = document.getElementById('userInput');
const btnEl = document.getElementById('sendBtn');
const chatHistory = document.getElementById('chatHistory');
let currentAiMessageEl = null;

// Web Audio API setup
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
let nextStartTime = 0; // Tracks when the next audio chunk should start

// Update your Host IP here for LAN access
const BACKEND_URL = `ws://${window.location.hostname}:8000/ws/chat`;
let socket;

function connect() {
    socket = new WebSocket(BACKEND_URL);
    socket.binaryType = 'arraybuffer'; // Crucial for receiving MP3 bytes

    socket.onopen = () => {
        statusEl.innerText = "Online - Ready to talk";
        statusEl.style.color = "#4CAF50";
        inputEl.disabled = false;
        btnEl.disabled = false;
    };

    socket.onmessage = async (event) => {
        if (event.data instanceof ArrayBuffer) {
            // Play audio as before
            playAudioChunk(event.data);
        } else {
            // Handle Text Data
            const textData = event.data;
            
            if (textData === "__END_OF_TURN__") {
                currentAiMessageEl = null; // Turn finished
            } else {
                // If we don't have a current AI bubble, create one
                if (!currentAiMessageEl) {
                    currentAiMessageEl = appendMessage('ai', '');
                }
                // Append the new text chunk to the bubble
                //currentAiMessageEl.innerText += textData;
                currentAiMessageEl.textContent += textData;
                // Auto-scroll to bottom
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }
        }
    };

    socket.onclose = () => {
        statusEl.innerText = "Disconnected. Retrying...";
        statusEl.style.color = "#f44336";
        setTimeout(connect, 3000);
    };
}

async function playAudioChunk(data) {
    try {
        // Decode the MP3 bytes into an AudioBuffer
        const audioBuffer = await audioCtx.decodeAudioData(data);
        
        const source = audioCtx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioCtx.destination);

        // Schedule playback
        const currentTime = audioCtx.currentTime;
        if (nextStartTime < currentTime) {
            nextStartTime = currentTime;
        }

        source.start(nextStartTime);
        nextStartTime += audioBuffer.duration; // Add length of this chunk to the timeline
    } catch (e) {
        console.error("Error decoding audio:", e);
    }
}

function appendMessage(sender, text) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    msgDiv.innerText = text;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return msgDiv;
}

function sendQuery() {
    const text = inputEl.value.trim();
    if (text && socket.readyState === WebSocket.OPEN) {
        // Reset timing for a new interaction
        nextStartTime = audioCtx.currentTime; 
	appendMessage('user', text);
        socket.send(text);
        inputEl.value = "";
    }
}

btnEl.onclick = sendQuery;
inputEl.onkeypress = (e) => { if(e.key === 'Enter') sendQuery(); };

// AudioContext Resume (Browsers block audio until a user clicks)
window.addEventListener('click', () => {
    if (audioCtx.state === 'suspended') audioCtx.resume();
});

connect();
