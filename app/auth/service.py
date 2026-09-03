from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3

from PySide6.QtCore import QSettings

from app.paths import app_data_dir


PBKDF2_ITERATIONS = 600_000
USERNAME_PATTERN = re.compile(r"^[\w.-]{3,24}$", re.UNICODE)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: int
    username: str
    email: str
    game_uid: str = ""


@dataclass(frozen=True, slots=True)
class FriendProfile:
    uid: str
    nickname: str
    level: int
    world_level: int
    profile_icon_url: str = ""


def default_auth_path() -> Path:
    return app_data_dir() / "accounts.db"


class AuthService:
    def __init__(
        self, path: Path | None = None, settings: QSettings | None = None
    ) -> None:
        self.path = path or default_auth_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = settings or QSettings("AstralOptimizer", "AstralOptimizer")
        if settings is None and not self.settings.contains("auth/user_id"):
            legacy = QSettings("HonkaiBuilds", "HonkaiBuilds")
            if legacy.contains("auth/user_id"):
                self.settings.setValue("auth/user_id", legacy.value("auth/user_id"))
        self.current_user: AuthUser | None = None
        self._initialize()
        self._restore_session()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        connection = self.connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    username_normalized TEXT NOT NULL UNIQUE,
                    email TEXT,
                    email_normalized TEXT,
                    game_uid TEXT,
                    password_hash BLOB NOT NULL,
                    salt BLOB NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(users)")
            }
            if "email" not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN email TEXT")
            if "email_normalized" not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN email_normalized TEXT")
            if "game_uid" not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN game_uid TEXT")
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_normalized
                ON users(email_normalized)
                WHERE email_normalized IS NOT NULL AND email_normalized <> ''
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS friends (
                    owner_id INTEGER NOT NULL,
                    uid TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 0,
                    world_level INTEGER NOT NULL DEFAULT 0,
                    profile_icon_url TEXT NOT NULL DEFAULT '',
                    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (owner_id, uid),
                    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _normalize(username: str) -> str:
        return username.strip().casefold()

    @staticmethod
    def _validate(username: str, email: str, password: str) -> None:
        if not USERNAME_PATTERN.fullmatch(username.strip()):
            raise ValueError("Use de 3 a 24 letras, números, ponto, hífen ou sublinhado.")
        if not EMAIL_PATTERN.fullmatch(email.strip()):
            raise ValueError("Digite um endereço de e-mail válido.")
        if len(password) < 8:
            raise ValueError("A senha precisa ter pelo menos 8 caracteres.")

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
        )

    def register(self, username: str, email: str, password: str) -> AuthUser:
        username = username.strip()
        email = email.strip()
        self._validate(username, email, password)
        username_normalized = self._normalize(username)
        email_normalized = email.casefold()
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt)
        connection = self.connect()
        try:
            duplicate = connection.execute(
                """
                SELECT username_normalized, email_normalized FROM users
                WHERE username_normalized = ? OR email_normalized = ?
                """,
                (username_normalized, email_normalized),
            ).fetchone()
            if duplicate:
                if duplicate["username_normalized"] == username_normalized:
                    raise ValueError("Esse nome de usuário já está cadastrado.")
                raise ValueError("Esse e-mail já está cadastrado.")
            cursor = connection.execute(
                """
                INSERT INTO users
                    (username, username_normalized, email, email_normalized, password_hash, salt)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    username_normalized,
                    email,
                    email_normalized,
                    password_hash,
                    salt,
                ),
            )
            connection.commit()
            user = AuthUser(int(cursor.lastrowid), username, email, "")
        except sqlite3.IntegrityError as error:
            raise ValueError("Esse nome de usuário já está cadastrado.") from error
        finally:
            connection.close()
        self._save_session(user)
        return user

    def login(self, identifier: str, password: str) -> AuthUser:
        normalized = self._normalize(identifier)
        connection = self.connect()
        try:
            row = connection.execute(
                """
                SELECT id, username, email, game_uid, password_hash, salt FROM users
                WHERE username_normalized = ? OR email_normalized = ?
                """,
                (normalized, normalized),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise ValueError("Usuário ou senha incorretos.")
        candidate = self._hash_password(password, bytes(row["salt"]))
        if not hmac.compare_digest(candidate, bytes(row["password_hash"])):
            raise ValueError("Usuário ou senha incorretos.")
        user = AuthUser(
            int(row["id"]), str(row["username"]), str(row["email"] or ""),
            str(row["game_uid"] or ""),
        )
        self._save_session(user)
        return user

    def _save_session(self, user: AuthUser) -> None:
        self.current_user = user
        self.settings.setValue("auth/user_id", user.id)
        self.settings.sync()

    def _restore_session(self) -> None:
        user_id = self.settings.value("auth/user_id", 0, int)
        if not user_id:
            return
        connection = self.connect()
        try:
            row = connection.execute(
                "SELECT id, username, email, game_uid FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        finally:
            connection.close()
        if row:
            self.current_user = AuthUser(
                int(row["id"]),
                str(row["username"]),
                str(row["email"] or ""),
                str(row["game_uid"] or ""),
            )
        else:
            self.logout()

    def logout(self) -> None:
        self.current_user = None
        self.settings.remove("auth/user_id")
        self.settings.sync()

    def update_game_uid(self, uid: str) -> AuthUser:
        user = self.current_user
        if user is None:
            raise ValueError("Entre em uma conta antes de salvar a UID.")
        uid = uid.strip()
        if uid and (len(uid) != 9 or not uid.isdigit()):
            raise ValueError("A UID precisa conter exatamente 9 números.")
        connection = self.connect()
        try:
            connection.execute("UPDATE users SET game_uid = ? WHERE id = ?", (uid, user.id))
            connection.commit()
        finally:
            connection.close()
        updated = AuthUser(user.id, user.username, user.email, uid)
        self._save_session(updated)
        return updated

    def friends(self) -> list[FriendProfile]:
        user = self.current_user
        if user is None:
            return []
        connection = self.connect()
        try:
            rows = connection.execute(
                """
                SELECT uid, nickname, level, world_level, profile_icon_url
                FROM friends
                WHERE owner_id = ?
                ORDER BY nickname COLLATE NOCASE, uid
                """,
                (user.id,),
            ).fetchall()
        finally:
            connection.close()
        return [
            FriendProfile(
                uid=str(row["uid"]),
                nickname=str(row["nickname"]),
                level=int(row["level"]),
                world_level=int(row["world_level"]),
                profile_icon_url=str(row["profile_icon_url"] or ""),
            )
            for row in rows
        ]

    def is_friend(self, uid: str) -> bool:
        user = self.current_user
        if user is None:
            return False
        connection = self.connect()
        try:
            row = connection.execute(
                "SELECT 1 FROM friends WHERE owner_id = ? AND uid = ?",
                (user.id, uid),
            ).fetchone()
        finally:
            connection.close()
        return row is not None

    def add_friend(
        self,
        uid: str,
        nickname: str,
        level: int,
        world_level: int,
        profile_icon_url: str = "",
    ) -> FriendProfile:
        user = self.current_user
        if user is None:
            raise ValueError("Entre em uma conta antes de adicionar amigos.")
        uid = uid.strip()
        if len(uid) != 9 or not uid.isdigit():
            raise ValueError("A UID do amigo precisa conter exatamente 9 números.")
        if uid == user.game_uid:
            raise ValueError("Sua UID principal não pode ser adicionada como amiga.")
        profile = FriendProfile(
            uid=uid,
            nickname=nickname.strip() or f"Jogador {uid}",
            level=max(int(level), 0),
            world_level=max(int(world_level), 0),
            profile_icon_url=profile_icon_url.strip(),
        )
        connection = self.connect()
        try:
            connection.execute(
                """
                INSERT INTO friends
                    (owner_id, uid, nickname, level, world_level, profile_icon_url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_id, uid) DO UPDATE SET
                    nickname = excluded.nickname,
                    level = excluded.level,
                    world_level = excluded.world_level,
                    profile_icon_url = excluded.profile_icon_url,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user.id, profile.uid, profile.nickname, profile.level,
                    profile.world_level, profile.profile_icon_url,
                ),
            )
            connection.commit()
        finally:
            connection.close()
        return profile

    def remove_friend(self, uid: str) -> None:
        user = self.current_user
        if user is None:
            return
        connection = self.connect()
        try:
            connection.execute(
                "DELETE FROM friends WHERE owner_id = ? AND uid = ?",
                (user.id, uid.strip()),
            )
            connection.commit()
        finally:
            connection.close()
