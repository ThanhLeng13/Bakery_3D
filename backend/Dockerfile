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

# Chạy bằng người dùng KHÔNG phải root.
#
# Mặc định container chạy root, nên một lỗ hổng trong ứng dụng hoặc một thư viện
# là quyền root bên trong container. Tạo user riêng và chuyển quyền sở hữu thư
# mục ứng dụng để tiến trình chỉ ghi được nơi cần ghi.
#
# UID/GID cố định (10001) thay vì để Docker tự cấp: khi chạy với volume, quyền
# trên host phải khớp một con số biết trước.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app \
    && chown -R app:app /app

USER app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
