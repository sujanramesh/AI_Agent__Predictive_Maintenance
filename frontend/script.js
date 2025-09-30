// frontend/script.js
const chatBox = document.getElementById("chat-box");
const inputField = document.getElementById("user-input");
const sendButton = document.getElementById("send-btn");

sendButton.addEventListener("click", sendMessage);
inputField.addEventListener("keypress", function (e) {
  if (e.key === "Enter") sendMessage();
});

function appendMessage(role, text) {
  const msg = document.createElement("div");
  msg.classList.add("message", role);
  msg.innerHTML = `<span class="avatar">${role === "user" ? "🙋" : "🤖"}</span> ${text}`;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
  const question = inputField.value.trim();
  if (!question) return;

  appendMessage("user", question);
  inputField.value = "";

  try {
    const response = await fetch("http://127.0.0.1:8000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });

    const data = await response.json();
    const answer = data.answer || "Sorry, I couldn't understand.";
    appendMessage("bot", answer);
  } catch (err) {
    appendMessage("bot", "❌ Error: " + err.message);
  }
}
