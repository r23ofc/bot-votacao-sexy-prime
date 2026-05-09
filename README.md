# Bot de Votação Sexy Prime — V5 Modelo Sigilosa

Esta versão mantém a correção do healthcheck para cron-job.org e adiciona o modo de **modelo sigilosa**.

## Novidade principal

Ao adicionar uma modelo participante, o bot agora pergunta:

```txt
Essa participante pode aparecer com o rosto no card?
```

Opções:

```txt
✅ Sim, rosto liberado
🙈 Não, usar foto do corpo/sem rosto
```

Se você escolher a opção sigilosa, o card da votação mostra:

```txt
🙈 Modelo sigilosa
Foto publicada sem mostrar o rosto.
```

Assim você pode usar foto do corpo, foto cortada ou foto sem identificar o rosto.

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

Environment Variables permanecem as mesmas:

```txt
BOT_TOKEN=token_do_bot
ADMIN_IDS=7156813235,ID_DO_AMIGO
AGENCY_NAME=Sexy Prime
DB_PATH=bot_votacao.db
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

## Observação

A migração do banco é automática. Se já existir um `bot_votacao.db`, o sistema adiciona as novas colunas sem apagar as tabelas.
