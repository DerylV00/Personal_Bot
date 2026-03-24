#!/usr/bin/env python3
"""
Deryl VanNostrand - Personal OS Telegram Bot
============================================
Daily accountability agent. Morning/evening check-ins,
book reflections, goal tracking, mental models.
"""

import os
import json
import asyncio
import schedule
import time
import threading
from datetime import datetime, date
from pathlib import Path
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

# == CONFIGURATION (set these as environment variables on Render) ==
BOT_TOKEN     = os.environ.get("BOT_TOKEN", "")
CHAT_ID       = os.environ.get("CHAT_ID", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")

# == LIVE SITES ==
FUTURE_VISION_URL = "https://personalbotinfo.netlify.app/deryl_vannostrand_future_vision.html"
LIBRARY_URL       = "https://personalbotinfo.netlify.app/deryl_vannostrand_library.html"

# == DERYL CONTEXT ==
DERYL_CONTEXT = """
You are Deryl VanNostrand's personal accountability agent and thinking partner.
You know everything about his life architecture, personality, and goals.

IDENTITY ARCHITECTURE (4 frameworks, all converging):
- Blaze Genius (Millionaire Master Plan): People-smart, Summer energy, WHO not HOW
  Winning formula: leverage through magnification - relationships, not systems
  Losing formula: getting stuck in spreadsheets and detail work
- ENFJ-A Protagonist (16Personalities): 83% Extraverted, 75% Intuitive, 79% Assertive
  Strengths: charismatic leadership, empathetic communication, strategic vision
  Watch for: overextending, sensitivity to criticism, idealizing people
- Gene Key 13 - The Guide: Power in deep listening, sees everyone as a hero
  Purpose (Key 2): pull others toward the future, not maintain the status quo
  Prosperity (Key 3): unlock wealth through innovation; Shadow = Chaos
- Start With Why: Core WHY = "People are more powerful when connected to something real
  - land, community, each other, and themselves."

CURRENT LIFE PLAN:
- Location: Lake Ozark, Missouri
- Age: ~26, former collegiate athlete (football + wrestling)
- Current: Bartending + MO real estate license (exam Saturday March 28)
- Brokerage: Legacy Real Estate, broker/mentor Nathan Maurer (developer/investor)
  Nathan's son Landen Maurer = salesperson, receives referrals from Deryl
- Summer strategy: bartend + be a lead magnet + refer to Landen + build relationships
- End of summer goal: F-150 EcoBoost + camper trailer (~$25K setup)
- Winter plan: AI integration + marketing + personal brand building
- 2027 goal: first STR property + first land flip (raw parcel -> well -> electric -> relist)
- 10-year vision: STR portfolio, Mayor of Lake Ozark, connected community platform,
  wrestling coaching, Bitcoin base layer, wife + family, lifestyle of time and autonomy

HEALTH:
- Current weight: ~225 lbs, goal 205 lbs
- Protocol: Push/Pull/Legs split, stationary bike, intermittent fasting
- Peptide protocol starting April 20: BPC-157 + TB-500, Semax, Retatrutide

BOOKS (18 total):
Millionaire Master Plan, Start With Why, Naval Almanac, Laws of Success,
Outwitting the Devil, Gene Keys, The Coming Wave, The Field, The Creative Act,
High Performance Habits, Change Your Thoughts Change Your Life, Psycho-Cybernetics,
Way of the Peaceful Warrior, Beyond Order, Way of the Superior Man,
A New Earth, We Who Wrestle with God

KEY PRINCIPLES:
1. Build the brand before you need it - post, show up, document
2. Hire your opposite genius early - delegate Steel work
3. Real estate is the vehicle, community is the purpose
4. Bitcoin is sovereignty, not speculation - accumulate and hold
5. Politics flows from reputation, not resume - build now
6. The body is part of the brand
7. Never confuse activity with flow
8. Partner before you scale
9. Mastermind by delivering value first
10. Long-term games only - everything compounds

Live sites:
- Future Vision: https://personalbotinfo.netlify.app/deryl_vannostrand_future_vision.html
- Knowledge Library: https://personalbotinfo.netlify.app/deryl_vannostrand_library.html

Speak to him like a thinking partner who knows him deeply. Be direct and specific.
Reference his specific plan and people (Nathan, Landen) when relevant.
Keep responses focused and actionable.
"""

# == CONTENT LIBRARY ==
MORNING_PROMPTS = [
    ("Start With Why", "What is your WHY today? Say it out loud before you leave the house."),
    ("Millionaire Master Plan", "Are you in Blaze mode today - or are you scheduling Steel work?"),
    ("Napoleon Hill", "Read your 10-year target state. Feel it, don't just read it."),
    ("Naval Ravikant", "Are you playing a long-term game today?"),
    ("Gene Keys", "Which frequency are you starting in? Shadow, Gift, or flow?"),
    ("High Performance Habits", "What is your PQO today? Relationships + content + deals."),
    ("Psycho-Cybernetics", "Take 2 minutes to mentally rehearse the day going well."),
    ("Peaceful Warrior", "There are no ordinary moments. The person across from you matters."),
    ("A New Earth", "Can you bring full presence to your first interaction today?"),
    ("Outwitting the Devil", "Are you drifting today or moving with definite purpose?"),
    ("The Field", "Your morning ritual is coherence calibration. Hold that state."),
    ("The Creative Act", "Notice what you notice today. Trust the signals."),
]

EVENING_PROMPTS = [
    ("Start With Why", "Did you lead with WHY today - or with what you do?"),
    ("Millionaire Master Plan", "Value audit: did you create or leverage value today?"),
    ("Gene Keys", "Key 3 check: did Chaos show up? Note it and reset tomorrow."),
    ("Napoleon Hill", "Were you operating in harmony today with Nathan, Landen, community?"),
    ("Naval Ravikant", "Did you build anything that compounds today?"),
    ("High Performance Habits", "Energy audit: did you generate or just spend energy today?"),
    ("Way of the Superior Man", "Did you hold your direction or drift toward approval?"),
    ("Beyond Order", "What fog did you illuminate today - or avoid?"),
    ("Psycho-Cybernetics", "Did your performance match your self-image today?"),
    ("A New Earth", "Were you present with people or running the commentary?"),
    ("Peaceful Warrior", "What mental trash showed up? Name it. Throw it out."),
    ("We Who Wrestle with God", "What are you wrestling with? What blessing is on the other side?"),
]

MENTAL_MODELS = [
    ("Lead With WHY - The Golden Circle", "Before your next conversation: am I starting from belief or from what I do?"),
    ("Blaze Genius Magnification", "WHO needs to meet WHO today? You are a connector first."),
    ("Mastermind Harmony", "Is every key relationship operating in harmony right now?"),
    ("Definite Chief Aim", "Read your 10-year target state from the Future Vision doc. Today."),
    ("Shadow to Gift", "You're in Shadow when reactive/grasping. Gift when curious and at ease."),
    ("Specific Knowledge", "What did you learn today that only YOU could have learned?"),
    ("Long-Term Game Check", "Are you playing for today or the 10-year compound?"),
    ("Self-Image Reset", "Close your eyes 90 seconds. See yourself as your 10-year target state."),
    ("Chaos Shadow Watch", "Most vulnerable to chaos when understimulated. Name it. Return to Phase 0."),
    ("Media Leverage", "Every post you don't publish in winter is an asset that doesn't compound."),
]

BOOK_QUOTES = [
    ("Millionaire Master Plan", "When you follow your genius, you end up doing what you love, and loving what you do."),
    ("Start With Why", "People don't buy what you do - they buy why you do it."),
    ("Naval Ravikant", "All returns in life come from compound interest - relationships, money, and knowledge."),
    ("Napoleon Hill", "No mind is complete by itself. It needs contact with other minds to grow."),
    ("Gene Keys", "Your Life's Work is to help others see the hero in their own story."),
    ("High Performance Habits", "You can't get ahead on your goals if you're always behind on your energy."),
    ("Psycho-Cybernetics", "Your nervous system cannot distinguish between a real and a vividly imagined experience."),
    ("A New Earth", "Enthusiasm is joy with a goal - the deep aliveness of doing what you were made for."),
    ("Peaceful Warrior", "There are no ordinary moments."),
    ("Beyond Order", "Take on the maximum amount of responsibility you can bear. Then a little more."),
    ("Way of the Superior Man", "Live at your edge. The moment you stop growing it, you begin contracting."),
    ("Outwitting the Devil", "Definiteness of purpose is the starting point of all achievement."),
    ("The Field", "Coherent intention held by multiple minds in harmony has measurable effects."),
    ("The Creative Act", "An artist is someone who notices things. Your first job is to pay attention."),
    ("Wayne Dyer", "When you change the way you look at things, the things you look at change."),
    ("We Who Wrestle with God", "The blessing comes from the struggle - not from avoiding it."),
]

WEEK_PRINCIPLES = [
    "Know your genius, and you find your path of least resistance to wealth. - Roger Hamilton",
    "People don't buy what you do - they buy why you do it. - Simon Sinek",
    "All returns in life come from compound interest. - Naval Ravikant",
    "No mind is complete by itself. It needs contact with other minds to grow. - Napoleon Hill",
    "Your Life's Work is to guide others - to see every person's story as myth. - Gene Keys, Key 13",
]

# == STATE ==
STATE_FILE = "bot_state.json"

def load_state():
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "book_notes": {},
        "goals": [],
        "wins": [],
        "day_counter": 0,
        "conversation_history": [],
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

state = load_state()
client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# == CLAUDE ==
def ask_claude(user_message: str, conversation_history: list = None) -> str:
    messages = []
    if conversation_history:
        for msg in conversation_history[-12:]:
            messages.append(msg)
    messages.append({"role": "user", "content": user_message})
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=DERYL_CONTEXT,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        return f"[Claude unavailable: {str(e)[:100]}]"

# == SCHEDULED MESSAGES ==
async def send_morning_message():
    bot = Bot(token=BOT_TOKEN)
    state = load_state()
    day = state["day_counter"] % len(MORNING_PROMPTS)
    book, prompt = MORNING_PROMPTS[day]
    quote_idx = state["day_counter"] % len(BOOK_QUOTES)
    quote_book, quote = BOOK_QUOTES[quote_idx]
    model_idx = state["day_counter"] % len(MENTAL_MODELS)
    model_title, model_action = MENTAL_MODELS[model_idx]
    week_idx = state["day_counter"] % len(WEEK_PRINCIPLES)
    today = datetime.now().strftime("%A, %B %d")
    text = (
        "sunshine Good morning, Deryl.\n"
        f"_{today}_\n\n"
        "---\n"
        f"*Quote - {quote_book}*\n"
        f"_{quote}_\n\n"
        "---\n"
        f"*Morning Prompt - {book}*\n"
        f"{prompt}\n\n"
        "---\n"
        f"*Mental Model - {model_title}*\n"
        f"{model_action}\n\n"
        "---\n"
        f"*Active Principle*\n"
        f"_{WEEK_PRINCIPLES[week_idx]}_\n\n"
        "---\n"
        f"[Future Vision]({FUTURE_VISION_URL}) | [Library]({LIBRARY_URL})\n\n"
        "_Reply with anything on your mind._"
    )
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")
    state["day_counter"] += 1
    save_state(state)

async def send_evening_message():
    bot = Bot(token=BOT_TOKEN)
    state = load_state()
    day = (state["day_counter"] - 1) % len(EVENING_PROMPTS)
    book, prompt = EVENING_PROMPTS[day]
    today = datetime.now().strftime("%A, %B %d")
    text = (
        f"*Evening Review - {today}*\n\n"
        "---\n"
        f"*Reflection - {book}*\n"
        f"{prompt}\n\n"
        "---\n"
        "*Three quick questions:*\n"
        "1. What was today's biggest WIN?\n"
        "2. Where did you drift or operate below your genius?\n"
        "3. One thing to carry into tomorrow?\n\n"
        "---\n"
        "_Log a win: /win [what happened]_\n"
        "_Add a book note: /booknote [book] [insight]_"
    )
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coro)
    loop.close()

def schedule_morning():
    run_async(send_morning_message())

def schedule_evening():
    run_async(send_evening_message())

# == COMMAND HANDLERS ==
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "* Personal OS - Online*\n\n"
        "I'm your accountability agent. I know your plan, your books, and your wiring.\n\n"
        "Morning messages: 6:30 AM | Evening: 8:30 PM\n\n"
        "*Your Sites:*\n"
        f"[Future Vision]({FUTURE_VISION_URL})\n"
        f"[Knowledge Library]({LIBRARY_URL})\n\n"
        "*Commands:*\n"
        "/goals - view + add goals\n"
        "/win - log a win\n"
        "/books - view library\n"
        "/booknote [book] [insight] - save a reflection\n"
        "/model - random mental model\n"
        "/check - check-in vs your plan\n"
        "/morning - trigger morning message\n"
        "/evening - trigger evening message\n"
        "/help - full command list\n\n"
        "_Just talk to me freely - I'll respond as your thinking partner._",
        parse_mode="Markdown"
    )

async def cmd_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    args = context.args
    if args:
        new_goal = " ".join(args)
        state["goals"].append({"text": new_goal, "added": str(date.today()), "status": "active"})
        save_state(state)
        await update.message.reply_text(
            f"Goal locked in:\n_{new_goal}_\n\nBlaze reminder: goals are achieved through WHO, not HOW.",
            parse_mode="Markdown"
        )
    else:
        if not state["goals"]:
            await update.message.reply_text("No goals yet. Add one: /goals [your goal]")
            return
        active = [g for g in state["goals"] if g.get("status") == "active"]
        done = [g for g in state["goals"] if g.get("status") == "done"]
        text = "*Active Goals:*\n"
        for i, g in enumerate(active, 1):
            text += f"{i}. {g['text']} _{g['added']}_\n"
        if done:
            text += f"\n*Completed ({len(done)}):*\n"
            for g in done[-3:]:
                text += f"- {g['text']}\n"
        text += "\n_Add: /goals [text] | Complete: /done [number]_"
        await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    active = [g for g in state["goals"] if g.get("status") == "active"]
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /done [goal number]")
        return
    idx = int(args[0]) - 1
    if 0 <= idx < len(active):
        active[idx]["status"] = "done"
        active[idx]["completed"] = str(date.today())
        goal_text = active[idx]["text"]
        save_state(state)
        reply = ask_claude(f"Deryl completed a goal: '{goal_text}'. Short genuine acknowledgment connecting to his bigger vision. Under 80 words.")
        await update.message.reply_text(f"*Goal complete:* _{goal_text}_\n\n{reply}", parse_mode="Markdown")
    else:
        await update.message.reply_text("Goal number not found. Check /goals")

async def cmd_win(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    args = context.args
    if not args:
        if not state["wins"]:
            await update.message.reply_text("No wins yet. Log one: /win [what happened]")
            return
        text = "*Recent Wins:*\n"
        for w in state["wins"][-7:]:
            text += f"- {w['text']} _{w['date']}_\n"
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        win = " ".join(args)
        state["wins"].append({"text": win, "date": str(date.today())})
        save_state(state)
        reply = ask_claude(f"Deryl logged this win: '{win}'. Acknowledge and connect to one principle from his books. Under 80 words.")
        await update.message.reply_text(f"*Win logged:* _{win}_\n\n{reply}", parse_mode="Markdown")

async def cmd_booknote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /booknote [book] [insight]\n\n"
            "Example: /booknote naval The specific knowledge insight hit different today.\n\n"
            "Keys: mmp, swy, naval, hill, genekeys, wave, field, rubin, hph, dyer, psycho, warrior, peterson, dieda, tolle, wrestle, outwitting"
        )
        return
    book_key = args[0].lower()
    note = " ".join(args[1:])
    if book_key not in state["book_notes"]:
        state["book_notes"][book_key] = []
    state["book_notes"][book_key].append({"note": note, "date": str(date.today())})
    save_state(state)
    reply = ask_claude(f"Deryl added this reflection from '{book_key}': '{note}'. Connect to something specific in his current plan. 2-3 sentences.")
    await update.message.reply_text(f"*Note saved - {book_key}:*\n_{note}_\n\n{reply}", parse_mode="Markdown")

async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import random
    model_title, model_action = random.choice(MENTAL_MODELS)
    reply = ask_claude(f"Mental model: '{model_title}'. Practice: '{model_action}'. Add one specific way this applies to Deryl RIGHT NOW this week. Under 60 words.")
    await update.message.reply_text(
        f"*Mental Model: {model_title}*\n\n_{model_action}_\n\n*Right now:* {reply}",
        parse_mode="Markdown"
    )

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    today = datetime.now().strftime("%A, %B %d")
    wins_s = f"{len(state['wins'])} wins logged"
    goals_s = f"{len([g for g in state['goals'] if g.get('status') == 'active'])} active goals"
    notes_c = sum(len(v) for v in state["book_notes"].values())
    reply = ask_claude(
        f"Today is {today}. Quick honest check-in on where Deryl is vs his plan. "
        f"Context: {wins_s}, {goals_s}, {notes_c} book notes. "
        f"He's in Phase 0 - MO RE exam Saturday, peptide protocol April 20, summer bartending strategy. "
        f"Be direct, specific, encourage next concrete action. Under 150 words."
    )
    await update.message.reply_text(f"*Check-in - {today}*\n\n{reply}", parse_mode="Markdown")

async def cmd_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_morning_message()

async def cmd_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_evening_message()

async def cmd_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    book_list = [
        ("MMP", "Millionaire Master Plan"),
        ("SWY", "Start With Why"),
        ("NAVAL", "Almanac of Naval Ravikant"),
        ("HILL", "Laws of Success"),
        ("OUTWITTING", "Outwitting the Devil"),
        ("GENEKEYS", "Gene Keys"),
        ("WAVE", "The Coming Wave"),
        ("FIELD", "The Field"),
        ("RUBIN", "The Creative Act"),
        ("HPH", "High Performance Habits"),
        ("DYER", "Change Your Thoughts Change Your Life"),
        ("PSYCHO", "Psycho-Cybernetics"),
        ("WARRIOR", "Way of the Peaceful Warrior"),
        ("PETERSON", "Beyond Order / We Who Wrestle with God"),
        ("DIEDA", "Way of the Superior Man"),
        ("TOLLE", "A New Earth"),
    ]
    text = "*Your Library (18 books)*\n\n"
    for key, title in book_list:
        notes = len(state["book_notes"].get(key.lower(), []))
        note_str = f" _{notes} notes_" if notes > 0 else ""
        text += f"*{key}:* {title}{note_str}\n"
    text += "\n_Add a note: /booknote [key] [insight]_"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Deryl's Personal OS - Commands*\n\n"
        "/start - welcome + site links\n"
        "/goals - view active goals\n"
        "/goals [text] - add a goal\n"
        "/done [number] - complete a goal\n"
        "/win [text] - log a win\n"
        "/win - view recent wins\n"
        "/books - full library\n"
        "/booknote [book] [insight] - save reflection\n"
        "/model - random mental model\n"
        "/check - honest check-in vs plan\n"
        "/morning - trigger morning message\n"
        "/evening - trigger evening message\n\n"
        f"[Future Vision]({FUTURE_VISION_URL})\n"
        f"[Knowledge Library]({LIBRARY_URL})\n\n"
        "_Morning: 6:30 AM | Evening: 8:30 PM_",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    state = load_state()
    state["conversation_history"].append({"role": "user", "content": user_text})
    if len(state["conversation_history"]) > 20:
        state["conversation_history"] = state["conversation_history"][-20:]
    reply = ask_claude(user_text, state["conversation_history"][:-1])
    state["conversation_history"].append({"role": "assistant", "content": reply})
    save_state(state)
    await update.message.reply_text(reply)

# == SCHEDULER ==
def run_scheduler():
    schedule.every().day.at("06:30").do(schedule_morning)
    schedule.every().day.at("20:30").do(schedule_evening)
    print("Scheduler running - morning 6:30 AM, evening 8:30 PM")
    while True:
        schedule.run_pending()
        time.sleep(60)

# == MAIN ==
def main():
    print("Deryl's Personal OS Bot - Starting...")
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("goals", cmd_goals))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("win", cmd_win))
    app.add_handler(CommandHandler("booknote", cmd_booknote))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("morning", cmd_morning))
    app.add_handler(CommandHandler("evening", cmd_evening))
    app.add_handler(CommandHandler("books", cmd_books))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot online. Listening for messages...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
