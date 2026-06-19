#!/usr/bin/env python3
"""
Database module - SQLite para FullTrack Manager
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fulltrack.db')


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self):
        """Inicializa o schema do banco de dados"""
        with self.get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS serials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT UNIQUE NOT NULL,
                    contrato TEXT DEFAULT '',
                    cliente TEXT DEFAULT '',
                    observacao TEXT DEFAULT '',
                    status TEXT DEFAULT 'pendente',
                    mensagem TEXT DEFAULT '',
                    resultado TEXT DEFAULT '',
                    criado_em TEXT,
                    atualizado_em TEXT
                );

                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial_id INTEGER,
                    nivel TEXT DEFAULT 'INFO',
                    mensagem TEXT,
                    timestamp TEXT
                );

                CREATE TABLE IF NOT EXISTS configuracoes (
                    chave TEXT PRIMARY KEY,
                    valor TEXT DEFAULT ''
                );

                INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES
                    ('login_url', 'https://12308-htm-indust-de-equip-eletro-eletronicos-ltda.fulltrackapp.com/emp/12308-htm-indust-de-equip-eletro-eletronicos-ltda'),
                    ('fulltrack_url', 'https://12308-htm-indust-de-equip-eletro-eletronicos-ltda.fulltrackapp.com/mapaGeral_v3/#/'),
                    ('username', ''),
                    ('password', ''),
                    ('headless', 'true'),
                    ('timeout', '20'),
                    ('delay_between', '1'),
                    ('search_selector', '');
            """)
            existing_columns = [row['name'] for row in conn.execute("PRAGMA table_info(serials)").fetchall()]
            if 'contrato' not in existing_columns:
                conn.execute("ALTER TABLE serials ADD COLUMN contrato TEXT DEFAULT ''")
            if 'cliente' not in existing_columns:
                conn.execute("ALTER TABLE serials ADD COLUMN cliente TEXT DEFAULT ''")
            if 'observacao' not in existing_columns:
                conn.execute("ALTER TABLE serials ADD COLUMN observacao TEXT DEFAULT ''")

    # ─── Serials ────────────────────────────────────────────────────────────────

    def add_serial(self, numero: str, contrato: str = '', cliente: str = '', observacao: str = '') -> bool:
        """Adiciona um serial. Retorna True se inserido, False se duplicado."""
        try:
            with self.get_conn() as conn:
                now = datetime.now().isoformat()
                conn.execute(
                    "INSERT INTO serials (numero, contrato, cliente, observacao, status, criado_em, atualizado_em) VALUES (?, ?, ?, ?, 'pendente', ?, ?)",
                    (numero.strip(), contrato.strip(), cliente.strip(), observacao.strip(), now, now),
                )
                return True
        except sqlite3.IntegrityError:
            return False

    def get_serials(self, status: str = None):
        with self.get_conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM serials WHERE status = ? ORDER BY criado_em DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM serials ORDER BY criado_em DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_serial_by_id(self, serial_id: int):
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM serials WHERE id = ?", (serial_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_serial_status(
        self, serial_id: int, status: str, mensagem: str = "", resultado: str = ""
    ):
        with self.get_conn() as conn:
            conn.execute(
                "UPDATE serials SET status=?, mensagem=?, resultado=?, atualizado_em=? WHERE id=?",
                (status, mensagem, resultado, datetime.now().isoformat(), serial_id),
            )

    def delete_serial(self, serial_id: int):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM serials WHERE id=?", (serial_id,))

    def clear_serials(self, status: str = None):
        with self.get_conn() as conn:
            if status:
                conn.execute("DELETE FROM serials WHERE status=?", (status,))
            else:
                conn.execute("DELETE FROM serials")

    def reset_serials_status(self, from_status: str, to_status: str = "pendente"):
        """Reseta serials travados (ex: 'processando' → 'pendente')"""
        with self.get_conn() as conn:
            conn.execute(
                "UPDATE serials SET status=?, atualizado_em=? WHERE status=?",
                (to_status, datetime.now().isoformat(), from_status),
            )

    # ─── Logs ───────────────────────────────────────────────────────────────────

    def add_log(self, nivel: str, mensagem: str, serial_id: int = None):
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO logs (serial_id, nivel, mensagem, timestamp) VALUES (?, ?, ?, ?)",
                (serial_id, nivel, mensagem, datetime.now().isoformat()),
            )

    def get_logs(self, limit: int = 200):
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def clear_logs(self):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM logs")

    # ─── Configurações ───────────────────────────────────────────────────────────

    def get_setting(self, chave: str, default: str = "") -> str:
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT valor FROM configuracoes WHERE chave=?", (chave,)
            ).fetchone()
            return row["valor"] if row else default

    def set_setting(self, chave: str, valor: str):
        with self.get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
                (chave, valor),
            )

    def get_config(self) -> dict:
        return {
            "login_url": self.get_setting("login_url"),
            "fulltrack_url": self.get_setting("fulltrack_url"),
            "headless": self.get_setting("headless", "true").lower() == "true",
            "timeout": int(self.get_setting("timeout", "20")),
            "delay_between": int(self.get_setting("delay_between", "1")),
            "search_selector": self.get_setting("search_selector", ""),
        }

    def get_credentials(self) -> dict:
        return {
            "username": self.get_setting("username"),
            "password": self.get_setting("password"),
        }

    # ─── Estatísticas ────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        with self.get_conn() as conn:
            stats = {}
            for s in ["pendente", "bloqueado", "erro", "nao_encontrado", "processando"]:
                row = conn.execute(
                    "SELECT COUNT(*) as c FROM serials WHERE status=?", (s,)
                ).fetchone()
                stats[s] = row["c"]
            row = conn.execute("SELECT COUNT(*) as c FROM serials").fetchone()
            stats["total"] = row["c"]
        return stats
