"""
UBG Bot - Módulo de Banco de Dados (Turso / libsql)
Dados persistentes na nuvem — não resetam entre deploys.
"""

import os
import logging
import threading
import libsql_client
from datetime import datetime

log = logging.getLogger("UBG-DB")

TURSO_URL   = os.getenv("TURSO_URL", "")
TURSO_TOKEN = os.getenv("TURSO_TOKEN", "")


class Database:
    def __init__(self):
        self._local = threading.local()
        self._init_db()
        log.info(f"Banco de dados Turso conectado: {TURSO_URL}")

    def _get_conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = libsql_client.create_client_sync(
                url=TURSO_URL,
                auth_token=TURSO_TOKEN
            )
        return self._local.conn

    @property
    def conn(self):
        return self._get_conn()

    def _execute(self, sql: str, params: tuple = ()):
        return self.conn.execute(sql, params)

    def _executemany(self, sql: str, params_list: list):
        for params in params_list:
            self.conn.execute(sql, params)

    def _init_db(self):
        """Cria as tabelas necessárias caso não existam."""
        tabelas = [
            """CREATE TABLE IF NOT EXISTS usuarios (
                user_id       INTEGER PRIMARY KEY,
                saldo         REAL    NOT NULL DEFAULT 1000.0,
                vitorias      INTEGER NOT NULL DEFAULT 0,
                derrotas      INTEGER NOT NULL DEFAULT 0,
                total_apostas INTEGER NOT NULL DEFAULT 0,
                daily_last    TEXT    DEFAULT NULL,
                saldo_banco   REAL    NOT NULL DEFAULT 0.0
            )""",
            """CREATE TABLE IF NOT EXISTS apostas (
                aposta_id  TEXT    PRIMARY KEY,
                lutador1   TEXT    NOT NULL,
                lutador2   TEXT    NOT NULL,
                status     TEXT    NOT NULL DEFAULT 'aberta',
                vencedor   TEXT    DEFAULT NULL,
                criador_id INTEGER NOT NULL,
                criada_em  TEXT    NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS palpites (
                id        INTEGER PRIMARY KEY,
                aposta_id TEXT    NOT NULL,
                user_id   INTEGER NOT NULL,
                lutador   TEXT    NOT NULL,
                valor     REAL    NOT NULL,
                UNIQUE(aposta_id, user_id)
            )""",
            """CREATE TABLE IF NOT EXISTS loja (
                cargo_id  TEXT PRIMARY KEY,
                nome      TEXT NOT NULL,
                preco     REAL NOT NULL,
                descricao TEXT DEFAULT ''
            )""",
            """CREATE TABLE IF NOT EXISTS compras (
                id       INTEGER PRIMARY KEY,
                user_id  INTEGER NOT NULL,
                cargo_id TEXT    NOT NULL,
                UNIQUE(user_id, cargo_id)
            )""",
        ]
        for sql in tabelas:
            self._execute(sql)

        # Migração segura da coluna saldo_banco
        try:
            self._execute("ALTER TABLE usuarios ADD COLUMN saldo_banco REAL NOT NULL DEFAULT 0.0")
        except Exception:
            pass

        log.info("Tabelas inicializadas.")

    # ─────────────────────────────────────────────
    # Usuários
    # ─────────────────────────────────────────────

    def _row_to_dict(self, row, columns) -> dict:
        return dict(zip(columns, row))

    def get_usuario(self, user_id: int) -> dict | None:
        rs = self._execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
        if not rs.rows:
            return None
        return self._row_to_dict(rs.rows[0], [c.name for c in rs.columns])

    def criar_usuario(self, user_id: int) -> dict:
        self._execute("INSERT OR IGNORE INTO usuarios (user_id) VALUES (?)", (user_id,))
        return self.get_usuario(user_id)

    def get_or_create_usuario(self, user_id: int) -> dict:
        return self.get_usuario(user_id) or self.criar_usuario(user_id)

    def atualizar_saldo(self, user_id: int, delta: float) -> float:
        self.get_or_create_usuario(user_id)
        self._execute("UPDATE usuarios SET saldo = saldo + ? WHERE user_id = ?", (delta, user_id))
        return self.get_usuario(user_id)["saldo"]

    def set_daily(self, user_id: int, timestamp: str):
        self._execute("UPDATE usuarios SET daily_last = ? WHERE user_id = ?", (timestamp, user_id))

    def incrementar_stat(self, user_id: int, campo: str):
        campos_validos = {"vitorias", "derrotas", "total_apostas"}
        if campo not in campos_validos:
            raise ValueError(f"Campo inválido: {campo}")
        self._execute(f"UPDATE usuarios SET {campo} = {campo} + 1 WHERE user_id = ?", (user_id,))

    def decrementar_stat(self, user_id: int, campo: str):
        campos_validos = {"vitorias", "derrotas", "total_apostas"}
        if campo not in campos_validos:
            raise ValueError(f"Campo inválido: {campo}")
        self._execute(f"UPDATE usuarios SET {campo} = MAX(0, {campo} - 1) WHERE user_id = ?", (user_id,))

    def get_ranking(self, limite: int = 10) -> list[dict]:
        rs = self._execute("SELECT * FROM usuarios ORDER BY vitorias DESC, saldo DESC LIMIT ?", (limite,))
        cols = [c.name for c in rs.columns]
        return [self._row_to_dict(row, cols) for row in rs.rows]

    # ─────────────────────────────────────────────
    # Banco
    # ─────────────────────────────────────────────

    def get_saldo_banco(self, user_id: int) -> float:
        self.get_or_create_usuario(user_id)
        rs = self._execute("SELECT saldo_banco FROM usuarios WHERE user_id = ?", (user_id,))
        return rs.rows[0][0] if rs.rows else 0.0

    def depositar_banco(self, user_id: int, valor: float) -> tuple[float, float]:
        self.atualizar_saldo(user_id, -valor)
        self._execute("UPDATE usuarios SET saldo_banco = saldo_banco + ? WHERE user_id = ?", (valor, user_id))
        u = self.get_usuario(user_id)
        return u["saldo"], u["saldo_banco"]

    def sacar_banco(self, user_id: int, valor: float) -> tuple[float, float]:
        self._execute("UPDATE usuarios SET saldo_banco = MAX(0, saldo_banco - ?) WHERE user_id = ?", (valor, user_id))
        self.atualizar_saldo(user_id, valor)
        u = self.get_usuario(user_id)
        return u["saldo"], u["saldo_banco"]

    # ─────────────────────────────────────────────
    # Apostas
    # ─────────────────────────────────────────────

    def criar_aposta(self, aposta_id: str, lutador1: str, lutador2: str, criador_id: int) -> dict:
        agora = datetime.utcnow().isoformat()
        self._execute(
            "INSERT INTO apostas (aposta_id, lutador1, lutador2, criador_id, criada_em) VALUES (?, ?, ?, ?, ?)",
            (aposta_id, lutador1, lutador2, criador_id, agora)
        )
        return self.get_aposta(aposta_id)

    def get_aposta(self, aposta_id: str) -> dict | None:
        rs = self._execute("SELECT * FROM apostas WHERE aposta_id = ?", (aposta_id,))
        if not rs.rows:
            return None
        return self._row_to_dict(rs.rows[0], [c.name for c in rs.columns])

    def get_apostas_abertas(self) -> list[dict]:
        rs = self._execute("SELECT * FROM apostas WHERE status = 'aberta'")
        cols = [c.name for c in rs.columns]
        return [self._row_to_dict(row, cols) for row in rs.rows]

    def fechar_aposta(self, aposta_id: str, vencedor: str):
        self._execute(
            "UPDATE apostas SET status = 'fechada', vencedor = ? WHERE aposta_id = ?",
            (vencedor, aposta_id)
        )

    def registrar_palpite(self, aposta_id: str, user_id: int, lutador: str, valor: float) -> bool:
        try:
            self._execute(
                "INSERT INTO palpites (aposta_id, user_id, lutador, valor) VALUES (?, ?, ?, ?)",
                (aposta_id, user_id, lutador, valor)
            )
            return True
        except Exception:
            return False

    def get_palpites_da_aposta(self, aposta_id: str) -> list[dict]:
        rs = self._execute("SELECT * FROM palpites WHERE aposta_id = ?", (aposta_id,))
        cols = [c.name for c in rs.columns]
        return [self._row_to_dict(row, cols) for row in rs.rows]

    def get_palpite_usuario(self, aposta_id: str, user_id: int) -> dict | None:
        rs = self._execute(
            "SELECT * FROM palpites WHERE aposta_id = ? AND user_id = ?",
            (aposta_id, user_id)
        )
        if not rs.rows:
            return None
        return self._row_to_dict(rs.rows[0], [c.name for c in rs.columns])

    # ─────────────────────────────────────────────
    # Loja
    # ─────────────────────────────────────────────

    def get_itens_loja(self) -> list[dict]:
        rs = self._execute("SELECT * FROM loja ORDER BY preco ASC")
        cols = [c.name for c in rs.columns]
        return [self._row_to_dict(row, cols) for row in rs.rows]

    def get_item_loja(self, cargo_id: str) -> dict | None:
        rs = self._execute("SELECT * FROM loja WHERE cargo_id = ?", (cargo_id,))
        if not rs.rows:
            return None
        return self._row_to_dict(rs.rows[0], [c.name for c in rs.columns])

    def adicionar_item_loja(self, cargo_id: str, nome: str, preco: float, descricao: str = ""):
        self._execute(
            "INSERT OR REPLACE INTO loja (cargo_id, nome, preco, descricao) VALUES (?, ?, ?, ?)",
            (cargo_id, nome, preco, descricao)
        )

    def remover_item_loja(self, cargo_id: str):
        self._execute("DELETE FROM loja WHERE cargo_id = ?", (cargo_id,))

    def usuario_tem_item(self, user_id: int, cargo_id: str) -> bool:
        rs = self._execute(
            "SELECT 1 FROM compras WHERE user_id = ? AND cargo_id = ?",
            (user_id, cargo_id)
        )
        return len(rs.rows) > 0

    def registrar_compra(self, user_id: int, cargo_id: str):
        self._execute(
            "INSERT OR IGNORE INTO compras (user_id, cargo_id) VALUES (?, ?)",
            (user_id, cargo_id)
        )

    def remover_compra(self, user_id: int, cargo_id: str):
        self._execute(
            "DELETE FROM compras WHERE user_id = ? AND cargo_id = ?",
            (user_id, cargo_id)
        )
