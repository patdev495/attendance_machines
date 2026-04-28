# ==========================================
# STAGE 1: Builder (Compile dependencies)
# ==========================================
FROM python:3.10-slim-bullseye AS builder

WORKDIR /app

# Install build dependencies (Tham khảo từ bản build thành công)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    gcc \
    g++ \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update

RUN pip install --no-cache-dir wheel
COPY requirements.txt .
# Build wheels to avoid needing compilers in the final image
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# ==========================================
# STAGE 2: Runtime stage
# ==========================================
FROM python:3.10-slim-bullseye AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install only runtime dependencies and Microsoft ODBC Driver 18
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc \
    iputils-ping \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    # Fix for older SQL Server TLS versions (unsupported protocol error)
    && sed -i 's/MinProtocol = TLSv1.2/MinProtocol = TLSv1.0/g' /etc/ssl/openssl.cnf \
    && sed -i 's/CipherString = DEFAULT@SECLEVEL=2/CipherString = DEFAULT@SECLEVEL=1/g' /etc/ssl/openssl.cnf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install them
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

# Copy project files (Tương thích với kiến trúc 2 folder hiện tại)
COPY backend/ ./backend/

RUN touch machines.txt employee_work_shift.xlsx
RUN mkdir -p /app/backend/logs /app/backend/static/assets

EXPOSE 8001

# Command to run the application
CMD ["python", "backend/src/main.py", "--host", "0.0.0.0", "--port", "8001"]
