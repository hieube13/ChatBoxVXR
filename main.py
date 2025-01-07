from datetime import datetime
import json
import os
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import openai
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

templates = Jinja2Templates(
    directory= "templates"
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Cấu hình database
DATABASE_URL = "sqlite:///./chat_history.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatHistory(Base):
    __tablename__ = "chat_histories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    role = Column(String) 
    content = Column(String)  
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# OpenAI API Key
api_key = os.getenv("OPENAI_API_KEY")

# Input từ người dùng
class ChatRequest(BaseModel):
    user_id: str
    message: str

# Fake data API
def fake_get_ticket_info(route: str, date: str, time: str):
    return {
        "route": route,
        "date": date,
        "time": time,
        "status": "available",
        "remaining_seats": 12,
        "price": 150000
    }

def fake_book_ticket(route: str, time: str, seats: int):
    return {
        "status": "success",
        "route": route,
        "time": time,
        "seats": seats,
        "ticket_id": "ABC12345",
        "total_price": seats * 150000
    }

def fake_cancel_ticket(ticket_id: str):
    return {
        "status": "success",
        "message": f"Vé có mã {ticket_id} đã được hủy thành công.",
        "refund": 150000
    }

class HistoryChatServices():
    def __init__(self, db: Session):
        self.db = db

    # Lưu dữ liệu vào db
    def save_message_to_db(self, user_id: str, role: str, content: str):
        try:
            history_chat = ChatHistory(user_id=user_id, role=role, content=content)
            self.db.add(history_chat)
            self.db.commit()
            self.db.refresh(history_chat)
        except Exception as e:
            print(f"Error saving to database: {e}")
            self.db.rollback()
            raise

    # Lấy lịch sử trò chuyện gần đây - 4 hội thoai
    def get_recent_chat_history(self, user_id: str, limit: int = 5):
        history_chat = (self.db.query(ChatHistory)
                        .filter(ChatHistory.user_id == user_id)
                        .order_by(ChatHistory.timestamp.desc())
                        .limit(limit)
                        .all())
        return [{"role": row.role, "content": row.content} for row in reversed(history_chat)]

    # Hàm gọi ChatGPT API 
    def call_chatgpt_api(self, user_message: str, functions: list, user_id: str):
        today = datetime.now().strftime("%Y-%m-%d")
        system_message = {
            "role": "system",
            "content": (
                f"Hôm nay là ngày {today}. Bạn là một tư vấn viên hỗ trợ đặt vé xe khách, xưng 'em' và gọi người dùng là 'mình'. "
                f"Khi người dùng nói 'hôm nay', hãy hiểu đó là ngày {today}. Hãy nói chuyện thân thiện và tư vấn thông tin về đặt vé xe khách, "
                f"bao gồm tra cứu chuyến, giá vé, giờ giấc và hỗ trợ đặt vé. Nếu thiếu thông tin cần thiết để gọi API, hãy hỏi lại rõ ràng."
                f"Không được tự nhận bạn là chatbot. Bạn phải ám thị mình là con người. Chỉ là có thể còn thiếu sót trong kinh nghiệm."
            )
        }
        previous_messages = self.get_recent_chat_history(user_id)
        if previous_messages:
            messages = [system_message] + previous_messages + [{"role": "user", "content": user_message}]
        else:
            messages = [system_message, {"role": "user", "content": user_message}]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            functions=functions,
            function_call="auto"
        )
        
        return response
    
def get_history_chat_service(db: Session = Depends(get_db)) -> HistoryChatServices:
    return HistoryChatServices(db)

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, db: Session = Depends(get_db)):
    await websocket.accept()
    service = HistoryChatServices(db)
    try:
        while True:
            data = await websocket.receive_text()
            user_message = json.loads(data)["message"]
            service.save_message_to_db(user_id, "user", user_message)

            functions = [
                {
                    "name": "get_ticket_info",
                    "description": "Lấy thông tin vé xe cho một tuyến cụ thể.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "route": {"type": "string", "description": "Tuyến đường cần tra cứu, ví dụ: Hà Nội - Hải Phòng"},
                            "date": {"type": "string", "description": "Ngày đi, định dạng YYYY-MM-DD"},
                            "time": {"type": "string", "description": "Giờ khởi hành, ví dụ: 08:00"}
                        },
                        "required": ["route", "date", "time"]
                    }
                },
                {
                    "name": "book_ticket",
                    "description": "Đặt vé cho khách hàng.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "route": {"type": "string", "description": "Tuyến xe cần đặt"},
                            "time": {"type": "string", "description": "Giờ khởi hành, ví dụ: 08:00"},
                            "seats": {"type": "integer", "description": "Số lượng ghế cần đặt"}
                        },
                        "required": ["route", "time", "seats"]
                    }
                },
                {
                    "name": "cancel_ticket",
                    "description": "Hủy vé xe đã đặt.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string", "description": "Mã vé cần hủy"}
                        },
                        "required": ["ticket_id"]
                    }
                }
            ]

            response = service.call_chatgpt_api(user_message, functions, user_id)
            message = response["choices"][0]["message"]
            if message.get("function_call"):
                function_name = message["function_call"]["name"]
                arguments = json.loads(message["function_call"]["arguments"])
                if function_name == "get_ticket_info":
                    api_response = fake_get_ticket_info(arguments["route"], arguments["date"], arguments["time"])
                elif function_name == "book_ticket":
                    api_response = fake_book_ticket(arguments["route"], arguments["time"], arguments["seats"])
                elif function_name == "cancel_ticket":
                    api_response = fake_cancel_ticket(arguments["ticket_id"])
                else:
                    api_response = {"error": "Invalid function name."}
                assistant_message = str(api_response)
            else:
                assistant_message = message["content"]
            service.save_message_to_db(user_id, "assistant", assistant_message)
            await websocket.send_text(json.dumps({"role": "assistant", "content": assistant_message}))
    except WebSocketDisconnect:
        print("Client disconnected")

@app.get("/")
async def get_app(request : Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"title": "ChatBox đặt vé"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


