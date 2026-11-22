import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


def _mysql_uri():
    """Builds the MySQL connection string from environment variables (with local defaults).

    Set these before running the app (only MYSQL_PASSWORD is normally needed):
        MYSQL_USER      default: root
        MYSQL_PASSWORD  default: (empty)
        MYSQL_HOST      default: localhost
        MYSQL_PORT      default: 3306
        MYSQL_DB        default: booknest
    Or set DATABASE_URL to a full SQLAlchemy URL, e.g.
        mysql+pymysql://root:secret@localhost:3306/booknest?charset=utf8mb4
    """
    user = os.environ.get("MYSQL_USER", "root")
    password = quote_plus(os.environ.get("MYSQL_PASSWORD", ""))  # quote_plus makes symbols like @ or # safe
    host = os.environ.get("MYSQL_HOST", "localhost")
    port = os.environ.get("MYSQL_PORT", "3306")
    name = os.environ.get("MYSQL_DB", "booknest")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "booknest-dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or _mysql_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Re-checks a connection before using it, so a MySQL restart does not break the running app.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
