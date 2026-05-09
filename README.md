# Bot de Votação Sexy Prime — V4 Healthcheck

Esta versão corrige o problema do cron-job.org mostrando `404 Não Encontrado`.

Agora o bot responde:

```txt
https://SEU-SERVICO.onrender.com/
```

com:

```txt
OK - Bot de votação ativo
```

Assim o cron-job.org deve marcar o teste como sucesso.

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

Environment Variables:

```txt
BOT_TOKEN=token_do_bot
ADMIN_IDS=7156813235,ID_DO_AMIGO
AGENCY_NAME=Sexy Prime
DB_PATH=bot_votacao.db
```

Se precisar, adicione manualmente:

```txt
WEBHOOK_URL=https://nome-do-seu-servico.onrender.com
```

## cron-job.org

Use a URL raiz:

```txt
https://nome-do-seu-servico.onrender.com/
```

Intervalo recomendado:

```txt
Cada 5 minutos
```
