"""
UBG Bot - Módulo de Banco de Dados (SQLite)
Gerencia todas as operações de dados do bot.
"""

import sqlite3
import threading
import logging
import os
from datetime import datetime

log = logging.getLogger("UBG-DB")

# Usa /data se existir (Persistent Disk no Render), senão usa pasta local
DB_DIR  = "/data" if os.path.isdir("/data") else "."
DB_PATH = os.path.join(DB_DIR, "ubg_data.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        log.info(f"Banco de dados em: {self.db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_conn()

    def _init_db(self):
        c = self.conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                user_id       INTEGER PRIMARY KEY,
                saldo         REAL    NOT NULL DEFAULT 1000.0,
                vitorias      INTEGER NOT NULL DEFAULT 0,
                derrotas      INTEGER NOT NULL DEFAULT 0,
                total_apostas INTEGER NOT NULL DEFAULT 0,
                daily_last    TEXT    DEFAULT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS apostas (
                aposta_id  TEXT    PRIMARY KEY,
                lutador1   TEXT    NOT NULL,
                lutador2   TEXT    NOT NULL,
                status     TEXT    NOT NULL DEFAULT 'aberta',
                vencedor   TEXT    DEFAULT NULL,
                criador_id INTEGER NOT NULL,
                criada_em  TEXT    NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS palpites (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                aposta_id TEXT    NOT NULL,
                user_id   INTEGER NOT NULL,
                lutador   TEXT    NOT NULL,
                valor     REAL    NOT NULL,
                FOREIGN KEY (aposta_id) REFERENCES apostas(aposta_id),
                UNIQUE(aposta_id, user_id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS loja (
                cargo_id  TEXT PRIMARY KEY,
                nome      TEXT NOT NULL,
                preco     REAL NOT NULL,
                descricao TEXT DEFAULT ''
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS compras (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                cargo_id TEXT    NOT NULL,
                UNIQUE(user_id, cargo_id)
            )
        """)

        self.conn.commit()
        log.info("Banco de dados inicializado.")

    # ─────────────────────────────────────────────
    # Usuários
    # ─────────────────────────────────────────────

    def get_usuario(self, user_id: int) -> dict | None:
        c = self.conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return dict(row) if row else None

    def criar_usuario(self, user_id: int) -> dict:
        c = self.conn.cursor()
        c.execute("INSERT OR IGNORE INTO usuarios (user_id) VALUES (?)", (user_id,))
        self.conn.commit()
        return self.get_usuario(user_id)

    def get_or_create_usuario(self, user_id: int) -> dict:
        return self.get_usuario(user_id) or self.criar_usuario(user_id)

    def atualizar_saldo(self, user_id: int, delta: float) -> float:
        self.get_or_create_usuario(user_id)
        c = self.conn.cursor()
        c.execute("UPDATE usuarios SET saldo = saldo + ? WHERE user_id = ?", (delta, user_id))
        self.conn.commit()
        return self.get_usuario(user_id)["saldo"]

    def set_daily(self, user_id: int, timestamp: str):
        c = self.conn.cursor()
        c.execute("UPDATE usuarios SET daily_last = ? WHERE user_id = ?", (timestamp, user_id))
        self.conn.commit()

    def incrementar_stat(self, user_id: int, campo: str):
        campos_validos = {"vitorias", "derrotas", "total_apostas"}
        if campo not in campos_validos:
            raise ValueError(f"Campo inválido: {campo}")
        c = self.conn.cursor()
        c.execute(f"UPDATE usuarios SET {campo} = {campo} + 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def decrementar_stat(self, user_id: int, campo: str):
        campos_validos = {"vitorias", "derrotas", "total_apostas"}
        if campo not in campos_validos:
            raise ValueError(f"Campo inválido: {campo}")
        c = self.conn.cursor()
        c.execute(f"UPDATE usuarios SET {campo} = MAX(0, {campo} - 1) WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_ranking(self, limite: int = 10) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM usuarios ORDER BY vitorias DESC, saldo DESC LIMIT ?", (limite,))
        return [dict(row) for row in c.fetchall()]

    # ─────────────────────────────────────────────
    # Apostas
    # ─────────────────────────────────────────────

    def criar_aposta(self, aposta_id: str, lutador1: str, lutador2: str, criador_id: int) -> dict:
        c = self.conn.cursor()
        agora = datetime.utcnow().isoformat()
        c.execute(
            "INSERT INTO apostas (aposta_id, lutador1, lutador2, criador_id, criada_em) VALUES (?, ?, ?, ?, ?)",
            (aposta_id, lutador1, lutador2, criador_id, agora)
        )
        self.conn.commit()
        return self.get_aposta(aposta_id)

    def get_aposta(self, aposta_id: str) -> dict | None:
        c = self.conn.cursor()
        c.execute("SELECT * FROM apostas WHERE aposta_id = ?", (aposta_id,))
        row = c.fetchone()
        return dict(row) if row else None

    def get_apostas_abertas(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM apostas WHERE status = 'aberta'")
        return [dict(row) for row in c.fetchall()]

    def fechar_aposta(self, aposta_id: str, vencedor: str):
        c = self.conn.cursor()
        c.execute("UPDATE apostas SET status = 'fechada', vencedor = ? WHERE aposta_id = ?", (vencedor, aposta_id))
        self.conn.commit()

    def registrar_palpite(self, aposta_id: str, user_id: int, lutador: str, valor: float) -> bool:
        c = self.conn.cursor()
        try:
            c.execute(
                "INSERT INTO palpites (aposta_id, user_id, lutador, valor) VALUES (?, ?, ?, ?)",
                (aposta_id, user_id, lutador, valor)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_palpites_da_aposta(self, aposta_id: str) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM palpites WHERE aposta_id = ?", (aposta_id,))
        return [dict(row) for row in c.fetchall()]

    def get_palpite_usuario(self, aposta_id: str, user_id: int) -> dict | None:
        c = self.conn.cursor()
        c.execute("SELECT * FROM palpites WHERE aposta_id = ? AND user_id = ?", (aposta_id, user_id))
        row = c.fetchone()
        return dict(row) if row else None

    # ─────────────────────────────────────────────
    # Loja
    # ─────────────────────────────────────────────

    def get_itens_loja(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM loja ORDER BY preco ASC")
        return [dict(row) for row in c.fetchall()]

    def get_item_loja(self, cargo_id: str) -> dict | None:
        c = self.conn.cursor()
        c.execute("SELECT * FROM loja WHERE cargo_id = ?", (cargo_id,))
        row = c.fetchone()
        return dict(row) if row else None

    def adicionar_item_loja(self, cargo_id: str, nome: str, preco: float, descricao: str = ""):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO loja (cargo_id, nome, preco, descricao) VALUES (?, ?, ?, ?)",
            (cargo_id, nome, preco, descricao)
        )
        self.conn.commit()

    def remover_item_loja(self, cargo_id: str):
        c = self.conn.cursor()
        c.execute("DELETE FROM loja WHERE cargo_id = ?", (cargo_id,))
        self.conn.commit()

    def usuario_tem_item(self, user_id: int, cargo_id: str) -> bool:
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM compras WHERE user_id = ? AND cargo_id = ?", (user_id, cargo_id))
        return c.fetchone() is not None

    def registrar_compra(self, user_id: int, cargo_id: str):
        c = self.conn.cursor()
        c.execute("INSERT OR IGNORE INTO compras (user_id, cargo_id) VALUES (?, ?)", (user_id, cargo_id))
        self.conn.commit()

    def remover_compra(self, user_id: int, cargo_id: str):
        c = self.conn.cursor()
        c.execute("DELETE FROM compras WHERE user_id = ? AND cargo_id = ?", (user_id, cargo_id))
        self.conn.commit()
