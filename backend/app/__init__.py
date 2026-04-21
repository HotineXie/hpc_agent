import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///hpc_agent.db"
)
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
CORS(
    app,
    supports_credentials=True,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:5173",
                "http://localhost:4173",
                "http://localhost:3100",
                frontend_url,
            ]
        }
    },
)

db = SQLAlchemy(app)

with app.app_context():
    from app.models import Task, Endpoint, Agent, AgentRun, NodeHourBudget, NodeHourUsage
    db.create_all()

from app.database import Database

g_database = Database()

from app.routes import tasks, endpoints, agents, budget
