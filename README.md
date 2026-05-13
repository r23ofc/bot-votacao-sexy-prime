# Bot de Votação Sexy Prime — V6 Apagar Último Anúncio

Esta versão mantém tudo da V5 e adiciona:

- Antes de postar um novo anúncio, o bot tenta apagar o último anúncio que ele postou naquele grupo.
- Depois envia o novo anúncio.
- Depois fixa a nova mensagem.
- Novo botão no painel: `🧹 Apagar último anúncio dos grupos`.

## Como funciona

Quando você clicar em:

```txt
🚀 Enviar anúncio agora para grupos
```

o bot faz:

```txt
1. Apaga o último anúncio salvo naquele grupo
2. Envia o anúncio novo
3. Salva o ID da nova mensagem
4. Fixa a nova mensagem
```

No automático acontece a mesma coisa.

## Importante

A primeira postagem depois desta atualização apenas será salva no banco.
A partir da próxima postagem, o bot já conseguirá apagar a anterior automaticamente.

Para apagar/fixar mensagens, o bot precisa estar como admin do grupo com permissões para:

```txt
Enviar mensagens
Apagar mensagens
Fixar mensagens
```

## Arquivos para subir no GitHub

Suba somente estes arquivos soltos:

- `main.py`
- `database.py`
- `config.py`
- `requirements.txt`
- `Procfile`
- `README.md`

Não envie:

- `.zip`
- `.pyc`
- `__pycache__`
- `bot_votacao.db`

## Render

Use como Web Service Free.

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
python main.py
```

Environment Variables continuam iguais:

```txt
BOT_TOKEN=token_do_bot
ADMIN_IDS=7156813235,ID_DO_AMIGO
AGENCY_NAME=Sexy Prime
DB_PATH=bot_votacao.db
```

## Migração automática

O banco será atualizado automaticamente com as novas colunas:

- `last_announcement_message_id`
- `last_announcement_at`
