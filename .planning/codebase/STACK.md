# Technology Stack

## Backend
- **Language**: Python 3.x
- **Framework**: FastAPI
- **Web Server**: Uvicorn
- **ORM**: SQLAlchemy
- **Database Driver**: PyODBC (SQL Server connectivity)
- **Attendance SDK**: PyZK (Integration with ZKTeco devices)
- **Validation**: Pydantic
- **Environment Management**: python-dotenv

## Frontend
- **Framework**: Vue 3 (Composition API)
- **Build Tool**: Vite
- **State Management**: Pinia
- **Routing**: Vue Router
- **HTTP Client**: Native `fetch` (verified from previous interactions or assumed standard for simple Vite/Vue setups)

## Infrastructure
- **Operating System**: Windows (target production server environment)
- **Database**: Microsoft SQL Server (ver 2008 indicated in history)
- **Runtime**: `uv` or `pip` for Python dependency management

## Tools & Documentation
- **API Documentation**: Swagger/OpenAPI (built-in to FastAPI)
- **Build Scripts**: Custom Python scripts for initialization and database sync
