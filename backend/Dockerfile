# Trùng phiên bản với CI và venv phát triển (`python-version: "3.13"` trong
# .github/workflows/ci.yml). Trước đây image dùng 3.11 trong khi test chạy 3.13,
# nên "đã kiểm thử" và "đã đóng gói" là hai môi trường khác nhau; chính comment
# trong CI ghi rõ phiên bản cũ từng gây lỗi không tái hiện được.
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
