
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


def _mysql_uri():
    # Prefer Railway's DATABASE_URL, then MYSQL_URL
    database_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("MYSQL_URL")
    )

    if database_url:
        # Make sure SQLAlchemy uses PyMySQL
        if database_url.startswith("mysql://"):
            database_url = database_url.replace(
                "mysql://", "mysql+pymysql://", 1
            )
        return database_url

    # Local development fallback
    user = os.environ.get("MYSQLUSER", os.environ.get("MYSQL_USER", "root"))
    password = quote_plus(
        os.environ.get("MYSQLPASSWORD", os.environ.get("MYSQL_PASSWORD", ""))
    )
    host = os.environ.get("MYSQLHOST", os.environ.get("MYSQL_HOST", "localhost"))
    port = os.environ.get("MYSQLPORT", os.environ.get("MYSQL_PORT", "3306"))
    name = os.environ.get(
        "MYSQLDATABASE",
        os.environ.get("MYSQL_DB", "booknest")
    )

    return (
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
        "?charset=utf8mb4"
    )


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "booknest-dev-secret-change-me"
    )

    SQLALCHEMY_DATABASE_URI = _mysql_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280
    }
