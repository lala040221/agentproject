FROM python:3.11-slim-bullseye

# 安裝依賴庫
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製檔案
COPY . .

# 安裝 Python 依賴
RUN pip install -r requirements.txt

# 設定容器啟動命令
CMD ["python3", "manage.py", "runserver", "0.0.0.0:5000"]
