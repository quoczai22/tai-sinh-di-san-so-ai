# API bridge

API này nối `web_ui` với metadata và pipeline PyTorch.

Chạy local:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Khi deploy, đặt `WEB_UI_ORIGINS` bằng danh sách domain frontend, phân tách bằng dấu phẩy:

```text
WEB_UI_ORIGINS=https://your-project.vercel.app
```

GPU worker cần chạy trên máy có CUDA; Vercel chỉ phục vụ frontend tĩnh trong MVP.
