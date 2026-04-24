# 🥊 UBG Economy Bot — Untitled Boxing Game

Bot de Discord focado em economia, apostas e ranking para servidores de UBG.

---

## 📁 Estrutura de Arquivos

```
ubg_bot/
├── bot.py            # Entry point principal
├── database.py       # Camada de dados (SQLite)
├── utils.py          # Utilitários e helpers compartilhados
├── requirements.txt  # Dependências Python
├── .env.example      # Template de configuração
└── cogs/
    ├── __init__.py
    ├── economia.py   # /saldo, /daily, /transferir
    ├── apostas.py    # /criar_aposta, /apostar, /fechar_aposta, /apostas_abertas
    ├── ranking.py    # /ranking, /registrar_vitoria
    └── perfil.py     # /perfil
```

---

## ⚙️ Como Configurar

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Criar o Bot no Discord Developer Portal

1. Acesse https://discord.com/developers/applications
2. Clique em **New Application** → dê um nome
3. Vá em **Bot** → clique em **Add Bot**
4. Em **Privileged Gateway Intents**, ative:
   - **Server Members Intent**
   - **Message Content Intent**
5. Copie o **Token** do bot

### 3. Configurar o Token

Copie `.env.example` para `.env` e preencha:

```bash
cp .env.example .env
```

Edite o `.env`:
```
DISCORD_TOKEN=SEU_TOKEN_AQUI
```

Ou simplesmente exporte como variável de ambiente:
```bash
export DISCORD_TOKEN="seu_token_aqui"
```

### 4. Convidar o Bot para o Servidor

Use a URL abaixo, substituindo `SEU_CLIENT_ID` pelo Client ID da aplicação:

```
https://discord.com/oauth2/authorize?client_id=SEU_CLIENT_ID&permissions=2147483648&scope=bot+applications.commands
```

A permissão `2147483648` = **Administrator** (recomendado para testes).  
Em produção, use permissões mínimas: `Send Messages`, `Embed Links`, `Read Messages`.

### 5. Rodar o Bot

```bash
# Com .env (recomendado)
python bot.py

# Ou com variável exportada
DISCORD_TOKEN="seu_token" python bot.py
```

> **Nota:** Os slash commands podem demorar até **1 hora** para aparecer globalmente no Discord após a primeira sincronização. Para servidores de teste, é instantâneo.

---

## 📋 Lista Completa de Comandos

### 💰 Economia

| Comando | Descrição | Quem pode usar |
|---------|-----------|----------------|
| `/saldo [@usuario]` | Vê o saldo atual (seu ou de outro) | Todos |
| `/daily` | Coleta recompensa diária (600–1200 coins, 1x/24h) | Todos |
| `/transferir @usuario valor` | Envia coins para outro jogador | Todos |

### 🥊 Apostas

| Comando | Descrição | Quem pode usar |
|---------|-----------|----------------|
| `/criar_aposta lutador1 lutador2` | Cria nova aposta entre dois lutadores | Admin |
| `/apostar aposta_id lutador valor` | Aposta coins em um lutador | Todos |
| `/fechar_aposta aposta_id vencedor` | Encerra aposta e distribui prêmios | Admin |
| `/apostas_abertas` | Lista todas as apostas ativas | Todos |

### 🏆 Ranking

| Comando | Descrição | Quem pode usar |
|---------|-----------|----------------|
| `/ranking [top]` | Exibe ranking por vitórias (padrão top 10) | Todos |
| `/registrar_vitoria @vencedor @perdedor` | Registra resultado manualmente | Admin |

### 👤 Perfil

| Comando | Descrição | Quem pode usar |
|---------|-----------|----------------|
| `/perfil [@usuario]` | Exibe saldo, vitórias, derrotas, apostas e rank | Todos |

---

## 🔒 Segurança Implementada

- Apostas com valor negativo ou zero são bloqueadas
- Usuários não podem apostar acima do saldo disponível
- Cada usuário só pode apostar uma vez por aposta
- Daily tem cooldown rigoroso de 24h
- Transferências para bots e para si mesmo são bloqueadas
- Todos os inputs são validados antes de qualquer operação no banco

---

## 🗄️ Banco de Dados

O bot usa **SQLite** (`ubg_data.db`) criado automaticamente na pasta do bot.  
Não é necessária nenhuma configuração adicional.

---

## ❓ Problemas Comuns

**Comandos não aparecem no Discord:**
- Aguarde até 1h para propagação global
- Verifique se o bot tem permissão `applications.commands` no servidor

**Erro de token inválido:**
- Confirme que o `.env` está preenchido corretamente
- Regenere o token no Developer Portal se necessário

**Bot offline mesmo rodando:**
- Verifique os intents: `Server Members` e `Message Content` devem estar ativos
