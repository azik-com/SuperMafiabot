# =============================================
#  MAFIA BOT — Handlerlar (python-telegram-bot)
# =============================================
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from game import Game
from roles import role_info, can_act_at_night, get_sheriff_result, get_detective_result
from texts import *

# Aktiv o'yinlar: chat_id → Game
GAMES: dict[int, Game] = {}


# ── Yordamchi funksiyalar ──────────────────────
def build_player_keyboard(game: Game, exclude_id: int = None, include_skip: bool = False):
    """Tirik o'yinchilardan inline keyboard."""
    buttons = []
    for p in game.alive_players():
        if p.user_id == exclude_id:
            continue
        buttons.append([InlineKeyboardButton(
            f"{p.mention()}",
            callback_data=f"select_{p.user_id}"
        )])
    if include_skip:
        buttons.append([InlineKeyboardButton(BTN_SKIP, callback_data="select_skip")])
    return InlineKeyboardMarkup(buttons)


def get_game(chat_id: int) -> Game | None:
    return GAMES.get(chat_id)


async def send_role_to_player(context: ContextTypes.DEFAULT_TYPE, game: Game, uid: int):
    """Rol va tavsiflini shaxsiy xabar orqali yuborish."""
    from texts import ROL_TAVSIFLARI, ROLE_ASSIGNED, MAFIA_TEAM, LOVERS_NOTIFY
    player = game.players[uid]
    role_key = player.role
    description = ROL_TAVSIFLARI.get(role_key, "")

    text = ROLE_ASSIGNED.format(description=description)
    await context.bot.send_message(
        chat_id=uid,
        text=text,
        parse_mode=ParseMode.HTML
    )

    # Mafia a'zolariga jamoa ro'yxatini yuborish
    if role_key in {"mafia", "don"}:
        team = [p for p in game.players.values() if p.role in {"mafia", "don"}]
        members = "\n".join(f"  {role_info(p.role)['emoji']} {p.mention()} — {p.role_display()}" for p in team)
        await context.bot.send_message(
            chat_id=uid,
            text=MAFIA_TEAM.format(members=members),
            parse_mode=ParseMode.HTML
        )

    # Sevgilisi uchun partner xabari
    if role_key == "sevgilisi" and player.lover_id:
        partner = game.players.get(player.lover_id)
        if partner:
            await context.bot.send_message(
                chat_id=uid,
                text=LOVERS_NOTIFY.format(partner=partner.mention()),
                parse_mode=ParseMode.HTML
            )
    # Partner ga ham xabar
    if player.lover_id:
        partner = game.players.get(player.lover_id)
        if partner and partner.role != "sevgilisi":
            # Partner ga ham sevgilisi borligini xabar qilish
            from texts import LOVERS_NOTIFY
            await context.bot.send_message(
                chat_id=player.lover_id,
                text=LOVERS_NOTIFY.format(partner=player.mention()),
                parse_mode=ParseMode.HTML
            )


# ── Buyruq Handlerlari ─────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shaxsiy chatda /start"""
    if update.effective_chat.type == "private":
        await update.message.reply_text(START_MSG, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(ONLY_PRIVATE)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_MSG, parse_mode=ParseMode.HTML)


async def cmd_newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruhda yangi o'yin yaratish."""
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text(ONLY_GROUP)
        return

    if chat_id in GAMES:
        await update.message.reply_text(GAME_ALREADY)
        return

    admin_id = update.effective_user.id
    game = Game(chat_id, admin_id)
    GAMES[chat_id] = game

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(BTN_JOIN, callback_data="join_game")],
        [InlineKeyboardButton(BTN_PLAYERS, callback_data="show_players"),
         InlineKeyboardButton(BTN_RULES, callback_data="show_rules")]
    ])

    await update.message.reply_text(
        LOBBY_CREATED.format(count=0, min_count=Game.MIN_PLAYERS),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yinga qo'shilish."""
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text(ONLY_GROUP)
        return

    game = get_game(chat_id)
    if not game:
        await update.message.reply_text(NO_GAME)
        return
    if game.phase != "lobby":
        await update.message.reply_text(GAME_RUNNING)
        return

    user = update.effective_user
    added = game.add_player(user.id, user.full_name, user.username)
    if not added:
        await update.message.reply_text(PLAYER_ALREADY)
        return

    await update.message.reply_text(
        PLAYER_JOINED.format(name=user.full_name, count=game.player_count()),
        parse_mode=ParseMode.HTML
    )


async def cmd_start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yinni boshlash (faqat admin)."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    game = get_game(chat_id)
    if not game:
        await update.message.reply_text(NO_GAME)
        return
    if game.phase != "lobby":
        await update.message.reply_text(GAME_RUNNING)
        return
    if user_id != game.admin_id:
        await update.message.reply_text(ONLY_ADMIN)
        return
    if game.player_count() < Game.MIN_PLAYERS:
        await update.message.reply_text(
            NOT_ENOUGH.format(min=Game.MIN_PLAYERS, count=game.player_count())
        )
        return

    # Rollarni taqsimlash
    game.assign_roles()
    await update.message.reply_text(
        GAME_STARTING.format(count=game.player_count()),
        parse_mode=ParseMode.HTML
    )

    # Har bir o'yinchiga rolni yuborish
    for uid in game.players:
        try:
            await send_role_to_player(context, game, uid)
            await asyncio.sleep(0.3)
        except Exception:
            pass  # Shaxsiy chat ochilmagan bo'lishi mumkin

    await asyncio.sleep(2)
    await start_night_phase(chat_id, context, game)


async def cmd_cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yinni bekor qilish."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    game = get_game(chat_id)
    if not game:
        await update.message.reply_text(NO_GAME)
        return
    if user_id != game.admin_id:
        await update.message.reply_text(ONLY_ADMIN)
        return

    del GAMES[chat_id]
    await update.message.reply_text(GAME_CANCELLED)


async def cmd_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yinchilar ro'yxati."""
    chat_id = update.effective_chat.id
    game = get_game(chat_id)
    if not game:
        await update.message.reply_text(NO_GAME)
        return

    if game.phase == "lobby":
        count = game.player_count()
        ready = count >= Game.MIN_PLAYERS
        players_text = "\n".join(
            f"{i}. {p.mention()}" for i, p in enumerate(game.players.values(), 1)
        )
        text = (
            f"👥 <b>O'yinchilar ({count} ta):</b>\n\n"
            f"{players_text}\n\n"
            f"{'✅ O'yin boshlanishi mumkin!' if ready else f'⏳ Kamida {Game.MIN_PLAYERS} ta kerak.'}"
        )
    else:
        text = (
            f"👥 <b>Tirik o'yinchilar ({game.alive_count()} ta):</b>\n\n"
            f"{game.alive_list_text()}"
        )

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ── Kecha fazasi ───────────────────────────────

async def start_night_phase(chat_id: int, context: ContextTypes.DEFAULT_TYPE, game: Game):
    """Kecha boshlash."""
    game.start_night()

    await context.bot.send_message(
        chat_id=chat_id,
        text=NIGHT_START.format(round=game.round, timeout=Game.NIGHT_TIMEOUT),
        parse_mode=ParseMode.HTML
    )

    # Harakat qila oladigan o'yinchilarga shaxsiy xabar yuborish
    for p in game.alive_players():
        if can_act_at_night(p.role):
            prompt = NIGHT_ACTION_PROMPT.get(p.role)
            if not prompt:
                continue
            # Sherif/Detektiv/Doktor/Maniac o'zini tanlay olmaydi
            exclude = p.user_id if p.role in {"sherif", "doktor", "detektiv", "maniac"} else None
            keyboard = build_player_keyboard(game, exclude_id=exclude)
            try:
                await context.bot.send_message(
                    chat_id=p.user_id,
                    text=prompt,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
            except Exception:
                pass

    # Timeout dan keyin kechalikni yopish
    context.job_queue.run_once(
        night_timeout_job,
        when=Game.NIGHT_TIMEOUT,
        data={"chat_id": chat_id},
        name=f"night_{chat_id}"
    )


async def night_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    """Kecha vaqti tugagach avtomatik natija."""
    chat_id = context.job.data["chat_id"]
    game = GAMES.get(chat_id)
    if not game or game.phase != "night":
        return
    await process_night_results(chat_id, context, game)


async def process_night_results(chat_id: int, context: ContextTypes.DEFAULT_TYPE, game: Game):
    """Kecha natijalarini e'lon qilib kunduz boshlash."""
    events = game.process_night()

    summary = "\n".join(events) if events else NIGHT_SUMMARY_NOBODY
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🌅 <b>Tong otdi!</b>\n\n{summary}",
        parse_mode=ParseMode.HTML
    )

    # G'olib tekshiruvi
    winner = game.check_winner()
    if winner:
        await announce_winner(chat_id, context, game)
        return

    await asyncio.sleep(2)
    await start_day_phase(chat_id, context, game)


# ── Kunduz fazasi ──────────────────────────────

async def start_day_phase(chat_id: int, context: ContextTypes.DEFAULT_TYPE, game: Game):
    """Kunduz boshlash — ovoz berish."""
    game.start_day()

    keyboard = build_player_keyboard(game, include_skip=True)
    await context.bot.send_message(
        chat_id=chat_id,
        text=VOTE_PROMPT.format(timeout=Game.DAY_TIMEOUT),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

    context.job_queue.run_once(
        day_timeout_job,
        when=Game.DAY_TIMEOUT,
        data={"chat_id": chat_id},
        name=f"day_{chat_id}"
    )


async def day_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data["chat_id"]
    game = GAMES.get(chat_id)
    if not game or game.phase != "day":
        return
    await process_day_results(chat_id, context, game)


async def process_day_results(chat_id: int, context: ContextTypes.DEFAULT_TYPE, game: Game):
    result = game.process_day_vote()

    if result["type"] == "exile" and result["player"]:
        p = result["player"]
        text = VOTE_RESULT_EXILED.format(
            name=p.mention(),
            count=result["votes"],
            role_emoji=role_info(p.role)["emoji"],
            role_name=role_info(p.role)["nom"]
        )
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)

        # Sevgilisi effekti
        for lover in result.get("lover_died", []):
            await context.bot.send_message(
                chat_id=chat_id,
                text=LOVER_DIES.format(name=lover.mention()),
                parse_mode=ParseMode.HTML
            )

    elif result["type"] == "tie":
        await context.bot.send_message(chat_id=chat_id, text=VOTE_RESULT_TIE, parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id=chat_id, text=VOTE_RESULT_SKIP, parse_mode=ParseMode.HTML)

    winner = game.check_winner()
    if winner:
        await announce_winner(chat_id, context, game)
        return

    await asyncio.sleep(2)
    await start_night_phase(chat_id, context, game)


# ── G'olib e'lon qilish ────────────────────────

async def announce_winner(chat_id: int, context: ContextTypes.DEFAULT_TYPE, game: Game):
    import time
    duration_sec = int(time.time() - (game.start_time or time.time()))
    minutes, seconds = divmod(duration_sec, 60)
    duration_str = f"{minutes} daqiqa {seconds} soniya"

    stats = GAME_STATS.format(
        duration=duration_str,
        rounds=game.round,
        total=len(game.players),
        roles_list=game.final_roles_text()
    )

    winner_msgs = {
        "town": WIN_TOWN,
        "mafia": WIN_MAFIA,
        "maniac": WIN_MANIAC,
        "nobody": WIN_NOBODY,
    }
    msg_template = winner_msgs.get(game.winner, WIN_NOBODY)
    await context.bot.send_message(
        chat_id=chat_id,
        text=msg_template.format(stats=stats),
        parse_mode=ParseMode.HTML
    )

    del GAMES[chat_id]


# ── Callback Query Handler ─────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    chat_id = query.message.chat_id

    # ── Lobby tugmalari ──
    if data == "join_game":
        game = get_game(chat_id)
        if not game:
            await query.answer(NO_GAME, show_alert=True)
            return
        if game.phase != "lobby":
            await query.answer(GAME_RUNNING, show_alert=True)
            return
        added = game.add_player(user.id, user.full_name, user.username)
        if not added:
            await query.answer(PLAYER_ALREADY, show_alert=True)
            return
        await context.bot.send_message(
            chat_id=chat_id,
            text=PLAYER_JOINED.format(name=user.full_name, count=game.player_count()),
            parse_mode=ParseMode.HTML
        )

    elif data == "show_players":
        game = get_game(chat_id)
        if not game:
            await query.answer(NO_GAME, show_alert=True)
            return
        players_text = "\n".join(
            f"{i}. {p.mention()}" for i, p in enumerate(game.players.values(), 1)
        ) or "Hali hech kim yo'q"
        await query.answer(
            f"👥 O'yinchilar ({game.player_count()}):\n{players_text}",
            show_alert=True
        )

    elif data == "show_rules":
        await query.answer(
            "🎭 Mafia o'yini:\n"
            "Kecha — maxsus rollar harakat qiladi\n"
            "Kunduz — aholi ovoz beradi\n"
            "Mafia tinch aholini kamaytiradi\n"
            "Tinch aholi mafiachini haydaydi!",
            show_alert=True
        )

    # ── Kecha harakatlari (shaxsiy chatdan) ──
    elif data.startswith("select_"):
        # Bu shaxsiy chatda bo'ladi
        if query.message.chat.type != "private":
            return

        uid = user.id
        # Qaysi o'yinda qatnashayotganini topish
        game = None
        for g in GAMES.values():
            if uid in g.players:
                game = g
                break
        if not game:
            await query.answer(NOT_IN_GAME, show_alert=True)
            return

        player = game.players.get(uid)
        if not player or not player.alive:
            return

        if data == "select_skip":
            target_id = -1
        else:
            target_id = int(data.split("_")[1])

        # ── Kecha va kunduz farqlash ──
        if game.phase == "night":
            if player.night_action is not None:
                await query.answer(ALREADY_VOTED_NIGHT, show_alert=True)
                return

            if target_id == -1:
                player.night_action = -1
            else:
                success = game.set_night_action(uid, target_id)
                if not success:
                    await query.answer(CANT_TARGET_DEAD, show_alert=True)
                    return

            await query.answer(VOTE_ACCEPTED, show_alert=True)
            await query.edit_message_reply_markup(reply_markup=None)

            # Sherif / Detektiv — shaxsiy natija
            if player.role == "sherif" and target_id != -1:
                target = game.players.get(target_id)
                if target:
                    result = get_sheriff_result(target.role)
                    if result == "mafia":
                        text = SHERIF_RESULT_MAFIA.format(name=target.mention())
                    else:
                        text = SHERIF_RESULT_CLEAN.format(name=target.mention())
                    await context.bot.send_message(chat_id=uid, text=text, parse_mode=ParseMode.HTML)

            elif player.role == "detektiv" and target_id != -1:
                target = game.players.get(target_id)
                if target:
                    role_key = get_detective_result(target.role)
                    info = role_info(role_key)
                    await context.bot.send_message(
                        chat_id=uid,
                        text=DETEKTIV_RESULT.format(
                            name=target.mention(),
                            role_emoji=info["emoji"],
                            role_name=info["nom"]
                        ),
                        parse_mode=ParseMode.HTML
                    )

            # Mafia hammasi ovoz berdimi?
            if player.role in {"mafia", "don"}:
                if game.mafia_night_actions_done():
                    # Boshqa ish qolmagan bo'lsa kutiladi — timeout hal qiladi
                    pass

        elif game.phase == "day":
            if player.day_vote is not None:
                await query.answer(ALREADY_VOTED_NIGHT, show_alert=True)
                return
            success = game.set_day_vote(uid, target_id if target_id != -1 else None)
            if not success:
                await query.answer(NOT_IN_GAME, show_alert=True)
                return
            await query.answer(VOTE_ACCEPTED, show_alert=True)
            await query.edit_message_reply_markup(reply_markup=None)

            target = game.players.get(target_id) if target_id != -1 else None
            if target:
                await context.bot.send_message(
                    chat_id=game.chat_id,
                    text=VOTE_CAST.format(voter=player.mention(), target=target.mention()),
                    parse_mode=ParseMode.HTML
                )

            if game.all_voted_day():
                # Barcha ovoz berdi — yakunlash
                jobs = context.job_queue.get_jobs_by_name(f"day_{game.chat_id}")
                for job in jobs:
                    job.schedule_removal()
                await process_day_results(game.chat_id, context, game)
