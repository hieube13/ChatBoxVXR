from typing import Dict, List
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        # Lưu trữ các kết nối WebSocket theo user_id
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Thêm kết nối WebSocket vào danh sách active_connections."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        """Xóa kết nối WebSocket khỏi danh sách active_connections."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:  # Nếu không còn kết nối nào
                del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        """Gửi tin nhắn đến một user cụ thể."""
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                await websocket.send_text(message)

    async def broadcast(self, message: str):
        """Gửi tin nhắn đến tất cả các user đang kết nối."""
        for user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                await websocket.send_text(message)