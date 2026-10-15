from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import init_db
from app.routers import users, groups, expenses, balances, settlements, demo

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables are created
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## Decentro SDE Intern Assignment — Expense Sharing Service
    A high-performance backend service with modern UI to track shared expenses,
    calculate pairwise balances, settle debts, and optimize transactions using
    Smart Debt Simplification.
    
    ### Key Features:
    - **User Management**: Create and list users.
    - **Group Management**: Group creation, membership management.
    - **Expense Management**: Equal split & custom exact splits with penny-rounding precision.
    - **Balance Calculation**: Structured pairwise debt format matching assignment requirements.
    - **Product Enhancements**: 
      - Smart Settlement Suggestions (Splitwise-style Min-Cash-Flow algorithm)
      - Expense Categorization & Spending Analytics
      - Search & Filtering
      - CSV & JSON Export
    - **Bonus Features**:
      - Balance Settlements (recording payments to clear debts)
      - Unequal / Custom Expense Splits
      - Complete Unit Test Suite
      - Docker & Docker Compose setup
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")
templates_dir = os.path.join(current_dir, "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include Routers
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(expenses.router)
app.include_router(balances.router)
app.include_router(settlements.router)
app.include_router(demo.router)

@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serves the rich modern interactive web dashboard."""
    index_path = os.path.join(templates_dir, "index.html")
    return FileResponse(index_path)

@app.get("/health", tags=["Health"])
def health_check():
    """Service health check."""
    return {"status": "healthy", "service": settings.APP_NAME, "version": settings.APP_VERSION}
