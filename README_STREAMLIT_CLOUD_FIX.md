# Sửa lỗi Gemini trên Streamlit Cloud

Trong Streamlit Community Cloud, mở **Manage app -> Settings -> Secrets** và cấu hình tối thiểu:

```toml
GEMINI_API_KEY = "YOUR_KEY"
GEMINI_MODEL = "gemini-3.5-flash-lite"
RAG_MODE = "hybrid"
RAG_EMBEDDING_MODEL = "gemini-embedding-001"
```

Sau khi Save, chọn **Reboot app**.

Bản này đã bỏ các fallback model cũ `gemini-2.0-flash` / `gemini-1.5-flash` và dùng các model hiện hành:
- gemini-3.5-flash-lite
- gemini-flash-lite-latest
- gemini-3.8-flash
- gemini-flash-latest

Nếu Gemini trả 429/403/404/503, chatbot sẽ hiển thị đúng nhóm lỗi thay vì luôn báo chung `server capacity`.
