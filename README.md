# Bot de Votação Sexy Prime — V3 Webhook Free Render

Esta versão foi adaptada para rodar como **Web Service grátis** no Render usando webhook.

## Arquivos

- `main.py`
- `database.py`
- `config.py`
- `requirements.txt`
- `Procfile`
- `README.md`

## Render

Crie como:

```txt
New
Web Service
```

Não use Background Worker se quiser rodar grátis.

## Configuração no Render

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
python main.py
```

Instance Type:

```txt
Free
```

## Environment Variables

Adicione:

```txt
BOT_TOKEN=token_do_bot
ADMIN_IDS=7156813235,ID_DO_AMIGO
AGENCY_NAME=Sexy Prime
DB_PATH=bot_votacao.db
```

Você não precisa adicionar `WEBHOOK_URL` se o Render preencher automaticamente `RENDER_EXTERNAL_URL`.

Se o webhook não funcionar, adicione manualmente:

```txt
WEBHOOK_URL=https://nome-do-seu-servico.onrender.com
```

## Importante

No plano grátis do Render, o serviço pode dormir quando fica sem tráfego.
Quando dormir, banco SQLite local e jobs automáticos podem ser perdidos ou atrasar.
Para produção real, use plano pago com disco persistente ou banco externo.
