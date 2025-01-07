// Hiển thị modal khi trang được tải
document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("username-modal");
    modal.style.display = "flex";
  });
  
  // Xử lý khi người dùng nhấn nút "Start Chat"
  document.getElementById("start-chat-button").addEventListener("click", () => {
    const usernameInput = document.getElementById("username-input");
    const username = usernameInput.value.trim();
  
    if (username) {
      // Tạo UserId từ tên người dùng (ví dụ: băm tên thành một chuỗi duy nhất)
      const userId = generateUserId(username);
  
      // Ẩn modal
      const modal = document.getElementById("username-modal");
      modal.style.display = "none";
  
      // Khởi tạo WebSocket với UserId
      initializeChat(userId);
    } else {
      alert("Please enter your name!");
    }
  });
  
  // Hàm tạo UserId từ tên người dùng
  function generateUserId(username) {
    // Ví dụ: Băm tên thành một chuỗi duy nhất
    return username.toLowerCase().replace(/\s+/g, "-") + "-" + Date.now();
  }
  
  // Hàm khởi tạo WebSocket và bắt đầu chat
  function initializeChat(userId) {
    const websocket = new WebSocket(`ws://localhost:8000/ws/${userId}`);
  
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const message = data.content;
      const role = data.role;
  
      // Thêm tin nhắn vào chat container
      const chatContainer = document.querySelector(".chat-list");
      const messageElement = document.createElement("div");
      messageElement.classList.add("message", role === "assistant" ? "incoming" : "outgoing");
      messageElement.innerHTML = `
        <div class="incoming-container">
            <div class="incoming-img">
                <img class="avatar" src="static/img/chatboximg.jpg" alt="assistant avatar">
            </div>
            <div class="incoming-message">
                <div class="incoming-message-content">
                    <p class="text">${message}</p>
                </div>
            </div>
        </div>
      `;
      chatContainer.appendChild(messageElement);
      chatContainer.scrollTo(0, chatContainer.scrollHeight);
    };
  
    document.querySelector("#send-message-button").addEventListener("click", () => {
        const input = document.querySelector(".typing-input");
        const message = input.value.trim();
        if (message) {
          // Thêm tin nhắn của người dùng vào chat container
          const chatContainer = document.querySelector(".chat-list");
          const messageElement = document.createElement("div");
          messageElement.classList.add("message", "outgoing");
          messageElement.innerHTML = `
            <div class="outgoing-message-content">
                <p class="text">${message}</p>
            </div>
          `;
          chatContainer.appendChild(messageElement);
          chatContainer.scrollTo(0, chatContainer.scrollHeight);
      
          // Gửi tin nhắn qua WebSocket
          websocket.send(JSON.stringify({ message }));
          input.value = "";
      
          // Ẩn dòng chữ "Hello, there" và "How can I help you today?"
          hideGreetings();
        }
      });

      // Hàm ẩn dòng chữ "Hello, there" và "How can I help you today?"
    function hideGreetings() {
        const header = document.querySelector(".header");
        if (header) {
        header.style.display = "none";
        }
    }
  }

// Thay đổi theme sáng/tối
const toggleThemeButton = document.querySelector("#theme-toggle-button");
toggleThemeButton.addEventListener("click", () => {
    const isLightMode = document.body.classList.toggle("light_mode");
    localStorage.setItem("themeColor", isLightMode ? "light_mode" : "dark_mode");
    toggleThemeButton.innerText = isLightMode ? "dark_mode" : "light_mode";
});

// Xóa toàn bộ đoạn chat
const deleteChatButton = document.querySelector("#delete-chat-button");
deleteChatButton.addEventListener("click", () => {
    if (confirm("Are you sure you want to delete all the chats?")) {
        const chatContainer = document.querySelector(".chat-list");
        chatContainer.innerHTML = ""; // Xóa nội dung chat
        localStorage.removeItem("saved-chats"); // Xóa lịch sử chat từ localStorage
    }
});

// Tải theme từ localStorage khi trang được tải
const loadThemeFromLocalStorage = () => {
    const isLightMode = localStorage.getItem("themeColor") === "light_mode";
    document.body.classList.toggle("light_mode", isLightMode);
    toggleThemeButton.innerText = isLightMode ? "dark_mode" : "light_mode";
};

// Khởi chạy
loadThemeFromLocalStorage();

