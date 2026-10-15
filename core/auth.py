from datetime import datetime, timezone
from contextlib import contextmanager
import getpass
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time

from dotenv import load_dotenv

from core.waste_taxonomy import PROJECT_ROOT


PASSWORD_LENGTH_MIN = 12
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_WINDOW_SECONDS = 15 * 60


class AuthService:
    def __init__(self, db_path=None, bootstrap_from_env=True):
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        configured_db = os.getenv("ECOTWIN_AUTH_DB")
        self.db_path = Path(db_path or configured_db or PROJECT_ROOT / "data" / "auth.sqlite3")
        if not self.db_path.is_absolute():
            self.db_path = PROJECT_ROOT / self.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.bootstrap_error = None
        self._initialize_database()
        if bootstrap_from_env:
            self._bootstrap_admin()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize_database(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    username_norm TEXT NOT NULL UNIQUE,
                    password_salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'operator')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username_norm TEXT NOT NULL,
                    attempted_at INTEGER NOT NULL,
                    succeeded INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_login_attempts_user_time
                    ON login_attempts(username_norm, attempted_at, succeeded);
                """
            )
            connection.execute(
                "DELETE FROM login_attempts WHERE attempted_at < ?",
                (int(time.time()) - 30 * 24 * 60 * 60,),
            )

    def _bootstrap_admin(self):
        if self.user_count:
            return
        username = os.getenv("ECOTWIN_ADMIN_USERNAME", "").strip()
        password = os.getenv("ECOTWIN_ADMIN_PASSWORD", "")
        if not username and not password:
            return
        if not username or not password:
            self.bootstrap_error = "Both ECOTWIN_ADMIN_USERNAME and ECOTWIN_ADMIN_PASSWORD must be configured."
            return
        created, message = self.create_user(username, password, role="admin")
        if not created:
            self.bootstrap_error = message

    @property
    def user_count(self):
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    @staticmethod
    def _normalize_username(username):
        return username.strip().casefold()

    @staticmethod
    def _hash_password(password, salt):
        return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)

    def create_user(self, username, password, role="operator"):
        username = username.strip()
        username_norm = self._normalize_username(username)
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", username):
            return False, "Username must be 3-40 characters using letters, numbers, dot, dash, or underscore."
        if len(password) < PASSWORD_LENGTH_MIN:
            return False, f"Password must be at least {PASSWORD_LENGTH_MIN} characters."
        if len(password) > 1024:
            return False, "Password is too long."
        if role not in {"admin", "operator"}:
            return False, "Invalid account role."

        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt)
        created_at = datetime.now(timezone.utc).isoformat()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO users (username, username_norm, password_salt, password_hash, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (username, username_norm, salt, password_hash, role, created_at),
                )
        except sqlite3.IntegrityError:
            return False, "An account with that username already exists."
        return True, "Account created."

    def authenticate(self, username, password):
        username_norm = self._normalize_username(username)
        if not username_norm or not password:
            return None, "Enter your username and password."

        now = int(time.time())
        cutoff = now - LOGIN_WINDOW_SECONDS
        with self._connect() as connection:
            recent_failures = connection.execute(
                """
                SELECT COUNT(*) FROM login_attempts
                WHERE username_norm = ? AND succeeded = 0 AND attempted_at >= ?
                """,
                (username_norm, cutoff),
            ).fetchone()[0]
            if recent_failures >= LOGIN_ATTEMPT_LIMIT:
                return None, "Too many failed attempts. Try again in 15 minutes."
            user = connection.execute(
                """
                SELECT username, username_norm, password_salt, password_hash, role
                FROM users WHERE username_norm = ? AND is_active = 1
                """,
                (username_norm,),
            ).fetchone()

        salt = user["password_salt"] if user else b"\0" * 16
        expected_hash = user["password_hash"] if user else b"\0" * 64
        supplied_hash = self._hash_password(password, salt)
        authenticated = user is not None and hmac.compare_digest(supplied_hash, expected_hash)

        with self._connect() as connection:
            connection.execute(
                "INSERT INTO login_attempts (username_norm, attempted_at, succeeded) VALUES (?, ?, ?)",
                (username_norm, now, int(authenticated)),
            )
            if authenticated:
                connection.execute(
                    "DELETE FROM login_attempts WHERE username_norm = ? AND succeeded = 0",
                    (username_norm,),
                )

        if not authenticated:
            return None, "Invalid username or password."
        return {"username": user["username"], "role": user["role"]}, "Signed in."


def create_admin_interactively():
    auth_service = AuthService(bootstrap_from_env=False)
    if auth_service.user_count:
        print("An account already exists. Admins must be provisioned by an existing administrator.")
        return 1

    username = input("Admin username: ").strip()
    password = getpass.getpass("Admin password (12+ characters): ")
    password_confirmation = getpass.getpass("Confirm password: ")
    if not hmac.compare_digest(password, password_confirmation):
        print("Passwords do not match.")
        return 1
    created, message = auth_service.create_user(username, password, role="admin")
    print(message)
    return 0 if created else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Provision EcoTwin local accounts.")
    parser.add_argument("command", choices=["create-admin"])
    args = parser.parse_args()
    if args.command == "create-admin":
        raise SystemExit(create_admin_interactively())