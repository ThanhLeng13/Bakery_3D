# Cake Shop AI - Web Bán Bánh Kem Tích Hợp AI

Hệ thống thương mại điện tử chuyên biệt cho tiệm bánh kem tại Đà Nẵng, tích hợp AI chatbot tư vấn và công cụ thiết kế bánh kem trực quan.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11 |
| Database | Supabase (PostgreSQL + Auth + Storage) |
| AI | Groq API with model Llama 3.3 70B |
| Deployment | Vercel (frontend), Docker (backend) |

## Project Structure

```
Bakery_3D/
├── frontend/          # Next.js 14 application
├── backend/           # FastAPI application
├── supabase/          # Database migrations and config
└── README.md          # This file
```

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Docker and Docker Compose
- Supabase account (or local Supabase CLI)
- Groq API key (for AI chatbot — free tier available at [console.groq.com](https://console.groq.com))

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd Bakery_3D
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.local.example .env.local

# Edit .env.local with your values:
# - NEXT_PUBLIC_API_URL: Backend API URL (default: http://localhost:8000)
# - NEXT_PUBLIC_SUPABASE_URL: Your Supabase project URL
# - NEXT_PUBLIC_SUPABASE_ANON_KEY: Your Supabase anon key

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Edit .env with your values:
# - SUPABASE_URL: Your Supabase project URL
# - SUPABASE_KEY: Your Supabase anon key
# - SUPABASE_SERVICE_ROLE_KEY: Your Supabase service role key
# - GROQ_API_KEY: Your Groq API key (free at console.groq.com)
# - GROQ_MODEL: Model name (default: llama-3.3-70b-versatile)
# - JWT_SECRET_KEY: A secure random string for JWT signing

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at `http://localhost:8000`.
API docs: `http://localhost:8000/docs`

### 4. Backend with Docker (Alternative)

```bash
cd backend

# Copy environment variables
cp .env.example .env
# Edit .env with your values

# Build and start with Docker Compose
docker-compose up --build
```

### 5. Supabase Setup

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref <your-project-ref>

# Run migrations
supabase db push
```

## Environment Variables

### Frontend (.env.local)

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | Yes |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |

### Backend (.env)

| Variable | Description | Required |
|----------|-------------|----------|
| `APP_ENV` | Environment (development/production) | Yes |
| `DEBUG` | Enable debug mode | No |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_KEY` | Supabase anonymous key | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Yes |
| `GROQ_API_KEY` | Groq API key cho chatbot AI | Yes |
| `GROQ_MODEL` | Groq model (mặc định: `llama-3.3-70b-versatile`) | No |
| `JWT_SECRET_KEY` | Secret key for JWT signing | Yes |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry in minutes | No |

## Deployment

### Frontend (Vercel)

1. Connect your repository to Vercel
2. Set the root directory to `frontend/`
3. Configure environment variables in Vercel dashboard:
   - `NEXT_PUBLIC_API_URL` → Your production backend URL
   - `NEXT_PUBLIC_SUPABASE_URL` → Your Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` → Your Supabase anon key
4. Deploy — Vercel auto-detects Next.js and uses `vercel.json` config

### Backend (Docker)

```bash
cd backend

# Build production image
docker build -t cake-shop-api .

# Run production container
docker run -d \
  --name cake-shop-api \
  -p 8000:8000 \
  --env-file .env \
  cake-shop-api
```

Or with Docker Compose:

```bash
cd backend
docker-compose up -d
```

## Development

### Running Tests

```bash
# Frontend tests
cd frontend
npm test

# Backend tests
cd backend
pip install -r requirements-dev.txt
pytest
```

### Code Quality

```bash
# Frontend linting and formatting
cd frontend
npm run lint
npm run format:check

# Backend linting
cd backend
# (configured via pytest.ini)
```

## Design System

| Token | Value | Usage |
|-------|-------|-------|
| Pink Pastel | `#E8837A` | Primary accent, CTAs |
| Cream | `#FDF6EE` | Background, cards |
| Mocha | `#5C3D2E` | Text, headings |
| Heading Font | Playfair Display | h1-h6 |
| Body Font | DM Sans | Paragraphs, UI text |

## License

Private — All rights reserved.
