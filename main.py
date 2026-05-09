import asyncio
import logging
import os
import re
from html import escape

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatType, ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, ADMIN_IDS, AGENCY_NAME
from database import (
    init_db,
    save_group,
    mark_group_inactive,
    get_active_groups,
    save_announcement,
    get_announcement,
    clear_announcement,
    add_model,
    get_active_models,
    get_model,
    delete_model,
    get_user_vote,
    save_vote,
    get_ranking,
    get_total_votes,
    reset_votes,
    save_post_interval_minutes,
    get_post_interval_minutes,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


AUTO_POST_JOB_NAME = "auto_post_announcement"


# ==========================================================
# HELPERS
# ==========================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def private_chat(update: Update) -> bool:
    return update.effective_chat and update.effective_chat.type == ChatType.PRIVATE


def cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancelar", callback_data="admin:cancel")]
    ])


def admin_keyboard():
    interval = get_post_interval_minutes()

    if interval > 0:
        interval_label = f"⏱ Intervalo automático: {format_interval(interval)}"
    else:
        interval_label = "⏱ Definir intervalo automático"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Criar/editar anúncio dos grupos", callback_data="admin:set_ad")],
        [
            InlineKeyboardButton("👀 Ver anúncio atual", callback_data="admin:view_ad"),
            InlineKeyboardButton("🗑 Excluir anúncio", callback_data="admin:delete_ad_confirm"),
        ],
        [InlineKeyboardButton(interval_label, callback_data="admin:auto_interval")],
        [InlineKeyboardButton("➕ Adicionar modelo participante", callback_data="admin:add_model")],
        [InlineKeyboardButton("👑 Ver modelos participantes", callback_data="admin:list_models")],
        [InlineKeyboardButton("🚀 Enviar anúncio agora para grupos", callback_data="admin:send_ad")],
        [InlineKeyboardButton("🏆 Ver resultado da votação", callback_data="admin:ranking")],
        [InlineKeyboardButton("🗑 Resetar votos", callback_data="admin:reset_confirm")],
        [InlineKeyboardButton("👀 Ver votação como usuário", callback_data="admin:view_vote")],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar ao painel", callback_data="admin:menu")]
    ])


def normalize_url(url: str) -> str:
    url = url.strip()

    if url.startswith("t.me/"):
        return "https://" + url

    if url.startswith("@"):
        return "https://t.me/" + url.replace("@", "", 1)

    return url


def is_valid_url(url: str) -> bool:
    url = normalize_url(url)
    return url.startswith("https://") or url.startswith("http://")


def format_interval(minutes: int) -> str:
    minutes = int(minutes)

    if minutes <= 0:
        return "desativado"

    if minutes < 60:
        return f"{minutes} min"

    if minutes % 1440 == 0:
        days = minutes // 1440
        return f"{days} dia(s)"

    if minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours} hora(s)"

    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}min"


def parse_interval_to_minutes(text: str):
    raw = text.strip().lower().replace(" ", "")

    if raw in ("0", "off", "desativar", "desligar", "parar"):
        return 0

    match = re.fullmatch(r"(\d+)(m|min|minuto|minutos)?", raw)
    if match:
        return int(match.group(1))

    match = re.fullmatch(r"(\d+)(h|hora|horas)", raw)
    if match:
        return int(match.group(1)) * 60

    match = re.fullmatch(r"(\d+)(d|dia|dias)", raw)
    if match:
        return int(match.group(1)) * 1440

    return None


async def show_admin_panel(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    interval = get_post_interval_minutes()

    interval_text = (
        f"✅ Automático ativo: a cada <b>{format_interval(interval)}</b>"
        if interval > 0
        else "⏸ Automático desativado"
    )

    text = (
        f"👑 <b>Painel do Criador — {escape(AGENCY_NAME)}</b>\n\n"
        f"{interval_text}\n\n"
        "Escolha uma opção abaixo:\n\n"
        "📢 Criar ou editar o anúncio dos grupos\n"
        "⏱ Definir de quanto em quanto tempo postar\n"
        "📌 O bot fixa a mensagem quando postar no grupo\n"
        "🏆 Ver ranking da votação"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_keyboard(),
    )


async def edit_admin_panel(query):
    interval = get_post_interval_minutes()

    interval_text = (
        f"✅ Automático ativo: a cada <b>{format_interval(interval)}</b>"
        if interval > 0
        else "⏸ Automático desativado"
    )

    text = (
        f"👑 <b>Painel do Criador — {escape(AGENCY_NAME)}</b>\n\n"
        f"{interval_text}\n\n"
        "Escolha uma opção abaixo:\n\n"
        "📢 Criar ou editar o anúncio dos grupos\n"
        "⏱ Definir de quanto em quanto tempo postar\n"
        "📌 O bot fixa a mensagem quando postar no grupo\n"
        "🏆 Ver ranking da votação"
    )

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_keyboard(),
    )


async def send_voting_cards(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    models = get_active_models()

    if not models:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"⚠️ A votação da <b>{escape(AGENCY_NAME)}</b> ainda não tem modelos cadastradas.\n\n"
                "Volte mais tarde."
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    intro = (
        f"🔥 <b>Votação da capa — {escape(AGENCY_NAME)}</b>\n\n"
        "Escolha a modelo que você quer ver como capa da agência.\n\n"
        "⚠️ Cada pessoa pode votar apenas uma vez."
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=intro,
        parse_mode=ParseMode.HTML,
    )

    for model in models:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗳 Votar", callback_data=f"vote:{model['id']}")]
        ])

        caption = (
            f"👑 <b>{escape(model['name'])}</b>\n\n"
            "Clique no botão abaixo para votar nessa participante."
        )

        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=model["photo_file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
        except TelegramError:
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )


async def send_announcement_to_chat(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    announcement,
    pin_message: bool = True,
):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(announcement["button_text"], url=announcement["button_url"])]
    ])

    text = announcement["text"] or ""
    sent_message = None

    if announcement["media_type"] == "photo":
        sent_message = await context.bot.send_photo(
            chat_id=chat_id,
            photo=announcement["media_file_id"],
            caption=text[:1024],
            reply_markup=keyboard,
        )
    elif announcement["media_type"] == "video":
        sent_message = await context.bot.send_video(
            chat_id=chat_id,
            video=announcement["media_file_id"],
            caption=text[:1024],
            reply_markup=keyboard,
        )
    else:
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
        )

    pin_ok = False
    pin_failed = False

    if pin_message and sent_message:
        try:
            await context.bot.pin_chat_message(
                chat_id=chat_id,
                message_id=sent_message.message_id,
                disable_notification=True,
            )
            pin_ok = True
        except TelegramError:
            pin_failed = True

    return {
        "message": sent_message,
        "pin_ok": pin_ok,
        "pin_failed": pin_failed,
    }


async def send_announcement_to_all_groups(context: ContextTypes.DEFAULT_TYPE, pin_message: bool = True):
    announcement = get_announcement()
    groups = get_active_groups()

    if not announcement:
        return 0, 0, 0, 0, "Nenhum anúncio foi configurado ainda."

    if not groups:
        return 0, 0, 0, 0, "Nenhum grupo registrado ainda."

    sent = 0
    failed = 0
    pinned = 0
    pin_failed = 0

    for group in groups:
        try:
            result = await send_announcement_to_chat(
                group["chat_id"],
                context,
                announcement,
                pin_message=pin_message,
            )

            sent += 1

            if result["pin_ok"]:
                pinned += 1
            elif result["pin_failed"]:
                pin_failed += 1

        except TelegramError:
            failed += 1

    return sent, failed, pinned, pin_failed, None


async def ranking_text():
    ranking = get_ranking()
    total_votes = get_total_votes()

    if not ranking:
        return "⚠️ Nenhuma modelo participante cadastrada ainda."

    text = "🏆 <b>Resultado da votação</b>\n\n"

    for index, row in enumerate(ranking, start=1):
        if index == 1:
            medal = "🥇"
        elif index == 2:
            medal = "🥈"
        elif index == 3:
            medal = "🥉"
        else:
            medal = "🔹"

        text += f"{medal} <b>{index}º</b> — {escape(row['name'])}: <b>{row['total_votes']}</b> voto(s)\n"

    text += f"\n📊 <b>Total de votos:</b> {total_votes}"
    return text


# ==========================================================
# AGENDAMENTO AUTOMÁTICO
# ==========================================================

def remove_auto_post_jobs(application: Application):
    if not application.job_queue:
        return

    for job in application.job_queue.get_jobs_by_name(AUTO_POST_JOB_NAME):
        job.schedule_removal()


def setup_auto_post_job(application: Application):
    if not application.job_queue:
        print("JobQueue não está disponível. Rode: pip install -r requirements.txt")
        return

    remove_auto_post_jobs(application)

    interval_minutes = get_post_interval_minutes()

    if interval_minutes <= 0:
        print("Postagem automática desativada.")
        return

    interval_seconds = interval_minutes * 60

    application.job_queue.run_repeating(
        auto_post_announcement_job,
        interval=interval_seconds,
        first=interval_seconds,
        name=AUTO_POST_JOB_NAME,
    )

    print(f"Postagem automática ativa a cada {interval_minutes} minuto(s).")


async def auto_post_announcement_job(context: ContextTypes.DEFAULT_TYPE):
    sent, failed, pinned, pin_failed, error = await send_announcement_to_all_groups(
        context,
        pin_message=True,
    )

    if error:
        logging.info("Auto post não enviado: %s", error)
        return

    logging.info(
        "Auto post enviado. Enviados=%s Falhas=%s Fixados=%s Falhas ao fixar=%s",
        sent,
        failed,
        pinned,
        pin_failed,
    )


# ==========================================================
# COMANDOS
# ==========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not chat or not user:
        return

    # Se for grupo, registra e não mostra votação no grupo para evitar bagunça.
    if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        save_group(chat.id, chat.title or str(chat.id))
        return

    payload = context.args[0] if context.args else ""

    # Admin sem payload abre painel. Admin com /start votar vê a votação como usuário.
    if is_admin(user.id) and payload != "votar":
        await show_admin_panel(chat.id, context)
        return

    await send_voting_cards(chat.id, context)


async def painel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat or not private_chat(update):
        return

    if not is_admin(user.id):
        return

    await show_admin_panel(chat.id, context)


async def registrar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if not chat or chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    save_group(chat.id, chat.title or str(chat.id))

    await update.message.reply_text(
        "✅ Grupo registrado com sucesso.\n\n"
        "Agora o criador pode enviar anúncios para este grupo pelo painel privado do bot."
    )


async def resultado_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user or not is_admin(user.id):
        return

    text = await ranking_text()
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def meu_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    await update.message.reply_text(
        f"Seu ID detectado pelo bot é:\n\n{user.id}\n\n"
        f"Username: @{user.username}"
    )


# ==========================================================
# GRUPOS: REGISTRO AUTOMÁTICO AO ADICIONAR O BOT
# ==========================================================

async def track_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member_update = update.my_chat_member

    if not member_update:
        return

    chat = member_update.chat

    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    new_status = member_update.new_chat_member.status

    if new_status in ("member", "administrator"):
        save_group(chat.id, chat.title or str(chat.id))

        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    "✅ Bot conectado e grupo registrado.\n\n"
                    "O criador poderá enviar o anúncio da votação por aqui."
                ),
            )
        except TelegramError:
            pass

    elif new_status in ("left", "kicked"):
        mark_group_inactive(chat.id)


# ==========================================================
# CALLBACKS DOS BOTÕES
# ==========================================================

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data or ""

    if data.startswith("vote:"):
        await vote_callback(query, context)
        return

    await query.answer()

    if not is_admin(user.id):
        return

    if data == "admin:menu":
        context.user_data.pop("flow", None)
        context.user_data.pop("draft", None)
        await edit_admin_panel(query)
        return

    if data == "admin:cancel":
        context.user_data.pop("flow", None)
        context.user_data.pop("draft", None)
        await query.edit_message_text(
            "✅ Ação cancelada.",
            reply_markup=back_keyboard(),
        )
        return

    if data == "admin:set_ad":
        context.user_data["flow"] = "ad_text"
        context.user_data["draft"] = {}
        await query.edit_message_text(
            "📢 <b>Criar/editar anúncio dos grupos</b>\n\n"
            "Envie agora o <b>texto do anúncio</b> que aparecerá nos grupos.\n\n"
            "Obs: ao finalizar, o anúncio antigo será substituído.",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard(),
        )
        return

    if data == "admin:view_ad":
        announcement = get_announcement()

        if not announcement:
            await query.edit_message_text(
                "⚠️ Nenhum anúncio foi configurado ainda.",
                reply_markup=back_keyboard(),
            )
            return

        interval = get_post_interval_minutes()

        await query.edit_message_text(
            "👀 <b>Anúncio atual</b>\n\n"
            f"Botão: <b>{escape(announcement['button_text'])}</b>\n"
            f"Link: {escape(announcement['button_url'])}\n"
            f"Intervalo automático: <b>{format_interval(interval)}</b>\n\n"
            "Prévia enviada abaixo.",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )

        await send_announcement_to_chat(
            query.message.chat_id,
            context,
            announcement,
            pin_message=False,
        )
        return

    if data == "admin:delete_ad_confirm":
        announcement = get_announcement()

        if not announcement:
            await query.edit_message_text(
                "⚠️ Nenhum anúncio configurado para excluir.",
                reply_markup=back_keyboard(),
            )
            return

        await query.edit_message_text(
            "⚠️ Tem certeza que deseja excluir o anúncio atual?\n\n"
            "Isso também desativa a postagem automática.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Sim, excluir anúncio", callback_data="admin:delete_ad_yes")],
                [InlineKeyboardButton("⬅️ Cancelar", callback_data="admin:menu")],
            ]),
        )
        return

    if data == "admin:delete_ad_yes":
        clear_announcement()
        save_post_interval_minutes(0)
        setup_auto_post_job(context.application)

        await query.edit_message_text(
            "✅ Anúncio excluído com sucesso.\n\n"
            "A postagem automática também foi desativada.",
            reply_markup=back_keyboard(),
        )
        return

    if data == "admin:auto_interval":
        interval = get_post_interval_minutes()
        context.user_data["flow"] = "auto_interval"
        context.user_data["draft"] = {}

        await query.edit_message_text(
            "⏱ <b>Definir intervalo automático</b>\n\n"
            f"Intervalo atual: <b>{format_interval(interval)}</b>\n\n"
            "Envie de quanto em quanto tempo o bot deve postar o anúncio nos grupos.\n\n"
            "Exemplos:\n"
            "• <code>30</code> = 30 minutos\n"
            "• <code>2h</code> = 2 horas\n"
            "• <code>1d</code> = 1 dia\n"
            "• <code>0</code> = desativar automático\n\n"
            "Recomendado para grupo movimentado: 30 minutos, 1h ou 2h.",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard(),
        )
        return

    if data == "admin:add_model":
        context.user_data["flow"] = "model_name"
        context.user_data["draft"] = {}
        await query.edit_message_text(
            "➕ <b>Adicionar modelo participante</b>\n\n"
            "Envie agora o <b>nome da modelo</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard(),
        )
        return

    if data == "admin:list_models":
        models = get_active_models()

        if not models:
            await query.edit_message_text(
                "⚠️ Nenhuma modelo participante cadastrada ainda.",
                reply_markup=back_keyboard(),
            )
            return

        text = "👑 <b>Modelos participantes</b>\n\n"
        buttons = []

        for model in models:
            text += f"• ID {model['id']} — <b>{escape(model['name'])}</b>\n"
            buttons.append([
                InlineKeyboardButton(
                    f"🗑 Remover {model['name'][:25]}",
                    callback_data=f"admin:delete_model:{model['id']}",
                )
            ])

        buttons.append([InlineKeyboardButton("⬅️ Voltar ao painel", callback_data="admin:menu")])

        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    if data.startswith("admin:delete_model:"):
        try:
            model_id = int(data.split(":")[-1])
        except ValueError:
            return

        delete_model(model_id)

        await query.edit_message_text(
            "✅ Modelo removida com sucesso.\n\n"
            "Os votos dessa modelo também foram removidos.",
            reply_markup=back_keyboard(),
        )
        return

    if data == "admin:send_ad":
        await query.edit_message_text("⏳ Enviando anúncio para os grupos cadastrados e fixando a mensagem...")

        sent, failed, pinned, pin_failed, error = await send_announcement_to_all_groups(
            context,
            pin_message=True,
        )

        if error:
            await query.message.reply_text(
                f"⚠️ {error}",
                reply_markup=back_keyboard(),
            )
            return

        await query.message.reply_text(
            f"✅ Anúncio enviado.\n\n"
            f"📨 Enviados: {sent}\n"
            f"📌 Fixados: {pinned}\n"
            f"⚠️ Falhas ao enviar: {failed}\n"
            f"⚠️ Falhas ao fixar: {pin_failed}\n\n"
            "Obs: para fixar, o bot precisa ser admin do grupo com permissão de fixar mensagens.",
            reply_markup=back_keyboard(),
        )
        return

    if data == "admin:ranking":
        text = await ranking_text()
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    if data == "admin:reset_confirm":
        await query.edit_message_text(
            "⚠️ Tem certeza que deseja resetar todos os votos?\n\n"
            "Isso não remove as modelos, apenas apaga os votos.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Sim, resetar votos", callback_data="admin:reset_yes")],
                [InlineKeyboardButton("⬅️ Cancelar", callback_data="admin:menu")],
            ]),
        )
        return

    if data == "admin:reset_yes":
        reset_votes()
        await query.edit_message_text(
            "✅ Votos resetados com sucesso.",
            reply_markup=back_keyboard(),
        )
        return

    if data == "admin:view_vote":
        await query.message.reply_text("👀 Visualizando votação como usuário...")
        await send_voting_cards(query.message.chat_id, context)
        return


async def vote_callback(query, context: ContextTypes.DEFAULT_TYPE):
    user = query.from_user

    try:
        model_id = int(query.data.split(":")[1])
    except (ValueError, IndexError):
        await query.answer("Voto inválido.", show_alert=True)
        return

    model = get_model(model_id)

    if not model or int(model["active"]) != 1:
        await query.answer("Essa participante não está mais ativa.", show_alert=True)
        return

    existing_vote = get_user_vote(user.id)

    if existing_vote:
        await query.answer(
            f"⚠️ Você já votou em {existing_vote['model_name']}.",
            show_alert=True,
        )
        return

    save_vote(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        model_id=model_id,
    )

    await query.answer(
        "✅ Obrigado pela sua votação! Sua escolha foi registrada com sucesso.",
        show_alert=True,
    )


# ==========================================================
# MENSAGENS DO PAINEL ADMIN
# ==========================================================

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    message = update.message

    if not user or not chat or not message:
        return

    # No grupo, ignora mensagens comuns.
    if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    # Usuário comum no privado: orienta a usar /start.
    if not is_admin(user.id):
        if message.text and not message.text.startswith("/"):
            await message.reply_text("Use /start para participar da votação.")
        return

    flow = context.user_data.get("flow")

    if not flow:
        return

    draft = context.user_data.setdefault("draft", {})

    # --------------------------
    # FLUXO: INTERVALO AUTOMÁTICO
    # --------------------------
    if flow == "auto_interval":
        if not message.text:
            await message.reply_text(
                "⚠️ Envie um intervalo válido. Exemplo: 30, 1h, 2h ou 0.",
                reply_markup=cancel_keyboard(),
            )
            return

        minutes = parse_interval_to_minutes(message.text)

        if minutes is None:
            await message.reply_text(
                "⚠️ Intervalo inválido.\n\n"
                "Exemplos válidos: 30, 1h, 2h, 1d ou 0 para desativar.",
                reply_markup=cancel_keyboard(),
            )
            return

        if minutes != 0 and minutes < 5:
            await message.reply_text(
                "⚠️ Por segurança, use no mínimo 5 minutos.\n\n"
                "Exemplo: 30, 1h ou 2h.",
                reply_markup=cancel_keyboard(),
            )
            return

        if minutes > 10080:
            await message.reply_text(
                "⚠️ O máximo permitido é 7 dias.\n\n"
                "Exemplo: 1d, 2d ou 7d.",
                reply_markup=cancel_keyboard(),
            )
            return

        save_post_interval_minutes(minutes)
        setup_auto_post_job(context.application)

        context.user_data.pop("flow", None)
        context.user_data.pop("draft", None)

        if minutes == 0:
            await message.reply_text("✅ Postagem automática desativada.")
        else:
            await message.reply_text(
                f"✅ Postagem automática ativada.\n\n"
                f"O bot vai postar e fixar o anúncio nos grupos a cada {format_interval(minutes)}."
            )

        await show_admin_panel(chat.id, context)
        return

    # --------------------------
    # FLUXO: DEFINIR ANÚNCIO
    # --------------------------
    if flow == "ad_text":
        if not message.text:
            await message.reply_text("⚠️ Envie o texto do anúncio.", reply_markup=cancel_keyboard())
            return

        draft["ad_text"] = message.text.strip()
        context.user_data["flow"] = "ad_media"

        await message.reply_text(
            "✅ Texto salvo.\n\n"
            "Agora envie a <b>foto ou vídeo</b> do anúncio.",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard(),
        )
        return

    if flow == "ad_media":
        if message.photo:
            draft["ad_media_type"] = "photo"
            draft["ad_media_file_id"] = message.photo[-1].file_id
        elif message.video:
            draft["ad_media_type"] = "video"
            draft["ad_media_file_id"] = message.video.file_id
        else:
            await message.reply_text(
                "⚠️ Envie uma foto ou vídeo para o anúncio.",
                reply_markup=cancel_keyboard(),
            )
            return

        context.user_data["flow"] = "ad_button_text"

        await message.reply_text(
            "✅ Mídia salva.\n\n"
            "Agora envie o <b>texto do botão</b>.\n\n"
            "Exemplo: 🔥 Votar agora",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard(),
        )
        return

    if flow == "ad_button_text":
        if not message.text:
            await message.reply_text("⚠️ Envie o texto do botão.", reply_markup=cancel_keyboard())
            return

        button_text = message.text.strip()

        if len(button_text) > 60:
            await message.reply_text(
                "⚠️ O texto do botão está muito grande. Envie um texto mais curto.",
                reply_markup=cancel_keyboard(),
            )
            return

        draft["ad_button_text"] = button_text
        context.user_data["flow"] = "ad_button_url"

        await message.reply_text(
            "✅ Texto do botão salvo.\n\n"
            "Agora envie o <b>link do botão</b>.\n\n"
            "Exemplos:\n"
            "https://t.me/SeuBot?start=votar\n"
            "https://seudominio.com",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard(),
        )
        return

    if flow == "ad_button_url":
        if not message.text:
            await message.reply_text("⚠️ Envie o link do botão.", reply_markup=cancel_keyboard())
            return

        url = normalize_url(message.text.strip())

        if not is_valid_url(url):
            await message.reply_text(
                "⚠️ Link inválido. Envie um link começando com https:// ou http://",
                reply_markup=cancel_keyboard(),
            )
            return

        save_announcement(
            text=draft["ad_text"],
            media_type=draft["ad_media_type"],
            media_file_id=draft["ad_media_file_id"],
            button_text=draft["ad_button_text"],
            button_url=url,
        )

        context.user_data.pop("flow", None)
        context.user_data.pop("draft", None)

        await message.reply_text(
            "✅ Anúncio criado/editado com sucesso.\n\n"
            "Agora você pode enviar manualmente ou ativar o intervalo automático."
        )
        await show_admin_panel(chat.id, context)
        return

    # --------------------------
    # FLUXO: ADICIONAR MODELO
    # --------------------------
    if flow == "model_name":
        if not message.text:
            await message.reply_text("⚠️ Envie o nome da modelo.", reply_markup=cancel_keyboard())
            return

        name = message.text.strip()

        if len(name) > 80:
            await message.reply_text(
                "⚠️ Nome muito grande. Envie um nome mais curto.",
                reply_markup=cancel_keyboard(),
            )
            return

        draft["model_name"] = name
        context.user_data["flow"] = "model_photo"

        await message.reply_text(
            "✅ Nome salvo.\n\n"
            "Agora envie a <b>foto da modelo participante</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard(),
        )
        return

    if flow == "model_photo":
        if not message.photo:
            await message.reply_text(
                "⚠️ Envie uma foto da modelo participante.",
                reply_markup=cancel_keyboard(),
            )
            return

        photo_file_id = message.photo[-1].file_id
        model_name = draft["model_name"]

        add_model(
            name=model_name,
            photo_file_id=photo_file_id,
        )

        context.user_data.pop("flow", None)
        context.user_data.pop("draft", None)

        await message.reply_text(
            f"✅ Modelo adicionada com sucesso!\n\n"
            f"👑 Nome: {model_name}",
        )
        await show_admin_panel(chat.id, context)
        return


# ==========================================================
# INICIAR BOT
# ==========================================================

async def run_render_webhook_server(app: Application):
    from aiohttp import web

    port = int(os.getenv("PORT", "10000"))
    webhook_base_url = (
        os.getenv("WEBHOOK_URL")
        or os.getenv("RENDER_EXTERNAL_URL")
        or ""
    ).rstrip("/")

    if not webhook_base_url:
        raise RuntimeError("WEBHOOK_URL ou RENDER_EXTERNAL_URL não encontrado.")

    webhook_path = "/telegram-webhook"
    webhook_url = f"{webhook_base_url}{webhook_path}"

    async def healthcheck(request):
        return web.Response(
            text="OK - Bot de votação ativo",
            status=200,
            content_type="text/plain",
        )

    async def telegram_webhook(request):
        try:
            data = await request.json()
            update = Update.de_json(data, app.bot)
            await app.process_update(update)
            return web.Response(text="OK", status=200)
        except Exception as e:
            logging.exception("Erro ao processar webhook: %s", e)
            return web.Response(text="Erro interno", status=500)

    await app.initialize()
    await app.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )
    await app.start()

    web_app = web.Application()
    web_app.router.add_get("/", healthcheck)
    web_app.router.add_get("/health", healthcheck)
    web_app.router.add_get("/healthz", healthcheck)
    web_app.router.add_post(webhook_path, telegram_webhook)

    runner = web.AppRunner(web_app)
    await runner.setup()

    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    print(f"Servidor web iniciado na porta {port}")
    print(f"Healthcheck ativo em: {webhook_base_url}/")
    print(f"Webhook configurado em: {webhook_url}")

    try:
        await asyncio.Event().wait()
    finally:
        await app.stop()
        await app.shutdown()
        await runner.cleanup()


def build_application() -> Application:
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(ChatMemberHandler(track_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("painel", painel))
    app.add_handler(CommandHandler("registrar_grupo", registrar_grupo))
    app.add_handler(CommandHandler("resultado", resultado_command))
    app.add_handler(CommandHandler("meuid", meu_id))

    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.ALL, message_router))

    setup_auto_post_job(app)

    return app


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Configure BOT_TOKEN nas variáveis de ambiente do Render.")

    app = build_application()

    webhook_base_url = (
        os.getenv("WEBHOOK_URL")
        or os.getenv("RENDER_EXTERNAL_URL")
        or ""
    ).rstrip("/")

    if webhook_base_url:
        asyncio.run(run_render_webhook_server(app))
    else:
        print("WEBHOOK_URL/RENDER_EXTERNAL_URL não encontrado.")
        print("Rodando localmente via polling...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
