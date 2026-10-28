# RAG thứ hai: Vector RAG / Hybrid RAG

Bản này giữ nguyên RAG cũ dùng BM25 và bổ sung một RAG mới dùng **Gemini Embedding** để tìm sách/chính sách theo ngữ nghĩa.

## Ba chế độ

- `bm25`: RAG cũ, tìm theo từ khóa, chạy nhanh và không cần embedding.
- `vector`: RAG mới, dùng `gemini-embedding-001` để tìm nội dung gần nghĩa với câu hỏi.
- `hybrid`: kết hợp 45% BM25 + 55% Vector. Đây là chế độ khuyến nghị.

Nếu Vector RAG không gọi được Gemini API thì hệ thống tự fallback về BM25, không làm hỏng chatbot.

## Cấu hình

Trong `.env`:

```env
RAG_MODE=hybrid
RAG_EMBEDDING_MODEL=gemini-embedding-001
RAG_EMBEDDING_DIMENSIONS=768
```

Hoặc đăng nhập Admin -> **Cài đặt** -> **Chế độ RAG** và chọn:

1. Hybrid - BM25 + Vector
2. BM25 RAG - Từ khóa
3. Vector RAG - Ngữ nghĩa

Sau khi lưu, AIService được nạp lại và cấu hình có hiệu lực ở câu hỏi tiếp theo.

## Cách hoạt động

```text
Câu hỏi người dùng
       |
       v
BOOK / POLICY / GENERAL Router
       |
       +-----------------------+
       |                       |
       v                       v
   BM25 RAG                Vector RAG
  từ khóa                    embedding
       |                       |
       +-----------+-----------+
                   |
                   v
               Hybrid rank
                   |
                   v
              Top-K context
                   |
                   v
             Gemini trả lời
```

Vector của dữ liệu sách/chính sách được cache trong `.vector_rag_cache.json`. Khi dữ liệu thay đổi, chỉ tài liệu mới/thay đổi cần tạo embedding mới. File cache không được đưa lên Git.

## Chạy trên thiết bị khác trong cùng Wi-Fi/LAN

Máy chính chạy:

```powershell
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Xem IPv4 của máy chính bằng `ipconfig`, ví dụ `192.168.1.10`. Máy khác cùng mạng mở:

```text
http://192.168.1.10:8501
```

MySQL và Gemini/RAG vẫn chạy trên máy chính; điện thoại/laptop khác chỉ cần trình duyệt.
