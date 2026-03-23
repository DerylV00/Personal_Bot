#!/usr/bin/env python3
"""
Deryl VanNostrand — Personal OS Telegram Bot
============================================
A daily accountability agent that knows your books, your plan,
and your personality architecture. Sends morning intentions,
evening reviews, accepts book reflections, and keeps you on track.

SETUP (one-time, ~10 minutes):
1. Message @BotFather on Telegram → /newbot → copy your BOT_TOKEN
2. Message @userinfobot on Telegram → copy your CHAT_ID
3. Get your Anthropic API key from console.anthropic.com
4. pip install python-telegram-bot anthropic schedule
5. Fill in the three variables below
6. python bot.py

KEEP IT RUNNING:
- Local: just run python bot.py in a terminal window
- Free cloud: deploy to Railway.app or Render.com (free tier)
  → Connect your GitHub repo, set env vars, deploy
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

# ═══════════════════════════════════════════════════════
# CONFIGURATION — fill these in
# ═══════════════════════════════════════════════════════

BOT_TOKEN     = os.environ.get("BOT_TOKEN", "")
CHAT_ID       = os.environ.get("CHAT_ID", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")     # from console.anthropic.com

# ═══════════════════════════════════════════════════════
# DERYL'S IDENTITY & CONTEXT
# This is the brain of the bot — everything it knows about you
# ═══════════════════════════════════════════════════════

DERYL_CONTEXT = """
You are Deryl VanNostrand's personal accountability agent and thinking partner.
You know everything about his life architecture, personality, and goals.

IDENTITY ARCHITECTURE (4 frameworks, all converging):
- Blaze Genius (Millionaire Master Plan): People-smart, Summer energy, WHO not HOW
  Winning formula: leverage through magnification — relationships, not systems
  Losing formula: getting stuck in spreadsheets and detail work
  Needs: variety, new people, new places — never behind a desk all day
- ENFJ-A Protagonist (16Personalities): 83% Extraverted, 75% Intuitive, 79% Assertive
  Strengths: charismatic leadership, empathetic communication, strategic vision
  Watch for: overextending, sensitivity to criticism, idealizing people, avoiding conflict
- Gene Key 13 — The Guide: Power in deep listening, sees everyone as a hero in their story
  Purpose (Key 2): pull others toward the future, not maintain the status quo  
  Prosperity (Key 3): unlock wealth through innovation; Shadow = Chaos (scattered attention)
  Watch for: Key 13 Shadow = Discord; Key 54 Shadow = Greed/grasping for recognition
- Start With Why: Core WHY = "People are more powerful when connected to something real 
  — land, community, each other, and themselves."

CURRENT LIFE PLAN:
- Location: Lake Ozark, Missouri
- Age: ~26, former collegiate athlete (football + wrestling)
- Current: Bartending + pursuing MO real estate license (state exam coming up Saturday)
- Brokerage: Legacy Real Estate, broker/mentor Nathan Maurer (developer/investor)
  Nathan's son Landen Maurer = salesperson, receives referrals from Deryl this summer
- Summer strategy: bartend + be a lead magnet + build relationships + refer to Landen
- End of summer goal: F-150 EcoBoost + camper trailer (~$25K setup)
- Winter plan: dead season = AI integration + marketing + personal brand building
- 2027 goal: first STR property + first land flip (raw parcel → well → electric → relist)
- 10-year vision: STR portfolio, Mayor of Lake Ozark, connected community platform,
  wrestling coaching, Bitcoin base layer, wife + family, lifestyle of time and autonomy

HEALTH & BODY:
- Current weight: ~225 lbs, goal 205 lbs
- Protocol: Push/Pull/Legs split, stationary bike, intermittent fasting (1-2 meals/day)
- Peptide protocol starting April 20: BPC-157 + TB-500, Semax, Retatrutide (GLP-3)
- MU Health Care evaluation in progress
- Bilateral ankle issues, cervical spine concerns, right lower back — all being managed

BOOKS IN HIS LIBRARY (18 total):
Core 5: Millionaire Master Plan (Hamilton), Start With Why (Sinek), Almanac of Naval 
Ravikant, Laws of Success / Outwitting the Devil (Hill), Gene Keys (Rudd)

New 12: The Coming Wave (Suleyman), The Field (McTaggart), The Creative Act (Rubin),
High Performance Habits (Burchard), Change Your Thoughts Change Your Life (Dyer),
Psycho-Cybernetics (Maltz), Way of the Peaceful Warrior (Millman), Beyond Order (Peterson),
The Way of the Superior Man (Deida), A New Earth (Tolle), We Who Wrestle with God (Peterson)

KEY PRINCIPLES TO REINFORCE:
1. Build the brand before you need it — post, show up, document
2. Hire your opposite genius early — delegate Steel work
3. Real estate is the vehicle, community is the purpose  
4. Bitcoin is sovereignty, not speculation — accumulate and hold
5. Politics flows from reputation, not resume — build now
6. The body is part of the brand — the physical transformation IS the proof
7. Never confuse activity with flow — check: is this resistance or misalignment?
8. Partner before you scale — Gene Keys confirms: thrive in partnership
9. Mastermind by delivering value first — bring deals to Nathan before asking for anything
10. Long-term games only — every referral, every council meeting, every post compounds

PERSONALITY & COMMUNICATION:
- Speak to him like a thinking partner who knows him deeply, not a coach talking down
- Be direct and specific — he responds to concrete, strategic thinking
- Reference his specific plan, people (Nathan, Landen), and context when relevant
- Call out Blaze/ENFJ patterns when you see them (in a useful, not preachy way)
- Celebrate wins with genuine energy — he's an ENFJ and energy matters
- When he's drifting (Hill: Outwitting the Devil), name it gently and redirect to the plan
- Keep responses focused and actionable — not long lectures
"""

# ═══════════════════════════════════════════════════════
# DAILY CONTENT LIBRARY
# ═══════════════════════════════════════════════════════

MORNING_PROMPTS = [
    ("Start With Why", "What is your WHY today? Say it out loud before you leave the house."),
    ("Millionaire Master Plan", "Are you in Blaze mode today — or are you scheduling Steel work? Delegate what drains you."),
    ("Napoleon Hill", "Read your 10-year target state. Feel it, don't just read it. The subconscious needs the emotional input."),
    ("Naval Ravikant", "Are you playing a long-term game today — or optimizing for today's comfort?"),
    ("Gene Keys", "Which frequency are you starting in? Shadow (reactive), Gift (creative), or flow? Name it."),
    ("High Performance Habits", "What is your PQO today — your Prolific Quality Output? Relationships + content + deals. Everything else is secondary."),
    ("Psycho-Cybernetics", "Take 2 minutes to mentally rehearse the day going well. See it vividly. The nervous system prepares."),
    ("Way of the Peaceful Warrior", "There are no ordinary moments. The person across from you today matters completely."),
    ("A New Earth", "Can you bring full presence to your first interaction today — not performing it, but actually being there?"),
    ("Outwitting the Devil", "Are you drifting today — moving by default — or moving with definite purpose?"),
    ("The Field", "Your morning ritual is coherence calibration. Before the noise starts, you're tuning your signal. Hold that state as long as you can."),
    ("The Creative Act", "Notice what you notice today. The things that catch your attention are signals. Trust them."),
]

EVENING_PROMPTS = [
    ("Start With Why", "Did you lead with WHY today — or with what you do? Every interaction you led from belief is a deposit."),
    ("Millionaire Master Plan", "Value vs. leverage audit: did you create value today (new relationships, trust, knowledge) or leverage existing value?"),
    ("Gene Keys", "Key 3 check: did Chaos show up? Did you scatter attention or chase a new idea? No judgment — just note it and reset tomorrow."),
    ("Napoleon Hill", "Were you operating in harmony today — with Nathan, Landen, your community? Any friction worth addressing before it festers?"),
    ("Naval Ravikant", "Did you build anything that compounds today? A conversation that deepens trust, a post that builds audience, a relationship that may become a mastermind node."),
    ("High Performance Habits", "Energy audit: did you generate energy today (sleep, movement, nutrition) or just spend it?"),
    ("Way of the Superior Man", "Did you hold your direction today — or did you drift toward approval, distraction, or comfort?"),
    ("Beyond Order", "What fog did you illuminate today — or avoid? Name the thing you're not looking at clearly."),
    ("Psycho-Cybernetics", "Did your performance match your self-image — or did the thermostat kick you back to baseline somewhere?"),
    ("A New Earth", "Were you present with people today — or running the commentary, the comparison, the agenda?"),
    ("The Peaceful Warrior", "What mental trash showed up today? Name it. Now throw it out. Start fresh tomorrow."),
    ("We Who Wrestle with God", "What are you currently wrestling with? What's the blessing available on the other side of this struggle?"),
]

MENTAL_MODELS = [
    ("Lead With WHY — The Golden Circle", "Before your next conversation, ask: am I starting from the inside of the circle (belief) or the outside (what I do)?"),
    ("Blaze Genius Magnification", "Ask yourself: WHO needs to meet WHO today? You are a connector first. The referral is the product."),
    ("Mastermind Harmony", "Is every key relationship operating in harmony right now? If not — what action restores it today?"),
    ("Definite Chief Aim", "Read your 10-year target state paragraph from the Future Vision doc. Today."),
    ("Shadow → Gift", "You're in the Shadow when you're reactive, grasping, or performing. You're in the Gift when you're genuinely curious and at ease. Which one is running right now?"),
    ("Specific Knowledge Accumulation", "What did you learn today that only YOU could have learned — given your specific position, relationships, and curiosity?"),
    ("Long-Term Game Check", "Are you playing for today's win or the 10-year compound? Reframe one decision you're about to make through the long lens."),
    ("Psycho-Cybernetics: Self-Image", "Close your eyes for 90 seconds. See yourself as the person in your 10-year target state — physically, financially, in your community. Hold it clearly."),
    ("The Chaos Shadow", "You are most vulnerable to Key 3 Shadow (Chaos) when you're understimulated or when the plan feels too slow. Name it when it comes. Return to Phase 0."),
    ("Leverage Through Media", "Every post you don't publish in winter is a media asset that doesn't compound. The audience won't exist in summer if you don't build it in winter."),
]

BOOK_QUOTE_OF_DAY = [
    ("Millionaire Master Plan", "\"When you follow your genius, you end up doing what you love, and loving what you do.\""),
    ("Start With Why", "\"People don't buy what you do — they buy why you do it.\""),
    ("Naval Ravikant", "\"All returns in life — money, relationships, knowledge — come from compound interest.\""),
    ("Napoleon Hill", "\"No mind is complete by itself. It needs contact and association with other minds to grow and expand.\""),
    ("Gene Keys", "\"Your Life's Work is to help others see the hero in their own story.\""),
    ("High Performance Habits", "\"You can't get ahead on your goals if you're always behind on your energy.\""),
    ("Psycho-Cybernetics", "\"Your nervous system cannot distinguish between a real experience and one that is vividly imagined.\""),
    ("The Coming Wave", "\"The people who master the tools of the coming wave will help shape what it builds — and what it destroys.\""),
    ("A New Earth", "\"Enthusiasm is joy with a goal — the deep aliveness of doing what you were made for.\""),
    ("Way of the Peaceful Warrior", "\"There are no ordinary moments.\""),
    ("Beyond Order", "\"Take on the maximum amount of responsibility you can bear. Then a little more.\""),
    ("The Way of the Superior Man", "\"Live at your edge. The moment you stop growing your edge, you begin contracting.\""),
    ("Outwitting the Devil", "\"Definiteness of purpose is the starting point of all achievement.\""),
    ("The Field", "\"Coherent intention — held by multiple minds in harmony — has measurable effects on the physical world.\""),
    ("The Creative Act", "\"An artist is someone who notices things. Your first job is to pay attention.\""),
    ("Wayne Dyer", "\"When you change the way you look at things, the things you look at change.\""),
    ("We Who Wrestle with God", "\"The blessing comes from the struggle — not from avoiding it.\""),
    ("Peaceful Warrior", "\"The secret of change is to focus all of your energy, not on fighting the old, but on building the new.\""),
]

# State storage (simple JSON file — persists between restarts)
STATE_FILE = "bot_state.json"

def load_state():
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "book_notes": {},       # book_id: [list of notes]
        "goals": [],            # list of active goals
        "wins": [],             # list of logged wins
        "day_counter": 0,       # for rotating daily content
        "conversation_history": [],  # for multi-turn with Claude
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

state = load_state()
client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ═══════════════════════════════════════════════════════
# CLAUDE API — the thinking partner
# ═══════════════════════════════════════════════════════

def ask_claude(user_message: str, conversation_history: list = None) -> str:
    """Send a message to Claude with full Deryl context."""
    messages = []
    
    # Add conversation history for context (last 6 exchanges max)
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

# ═══════════════════════════════════════════════════════
# SCHEDULED MESSAGES
# ═══════════════════════════════════════════════════════

async def send_morning_message():
    """6:30 AM — Morning intention set."""
    bot = Bot(token=BOT_TOKEN)
    state = load_state()
    
    day = state["day_counter"] % len(MORNING_PROMPTS)
    book, prompt = MORNING_PROMPTS[day]
    
    quote_idx = state["day_counter"] % len(BOOK_QUOTE_OF_DAY)
    quote_book, quote = BOOK_QUOTE_OF_DAY[quote_idx]
    
    model_idx = state["day_counter"] % len(MENTAL_MODELS)
    model_title, model_action = MENTAL_MODELS[model_idx]
    
    today = datetime.now().strftime("%A, %B %d")
    
    text = f"""☀️ *Good morning, Deryl.*
_{today}_

━━━━━━━━━━━━━━━━━━
📖 *Quote — {quote_book}*
{quote}

━━━━━━━━━━━━━━━━━━
🎯 *Morning Prompt — {book}*
{prompt}

━━━━━━━━━━━━━━━━━━
🧠 *Mental Model Check — {model_title}*
{model_action}

━━━━━━━━━━━━━━━━━━
_Reply with anything on your mind. I'm here._
_Commands: /goals /wins /books /help_"""

    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")
    
    state["day_counter"] += 1
    save_state(state)

async def send_evening_message():
    """8:30 PM — Evening reflection."""
    bot = Bot(token=BOT_TOKEN)
    state = load_state()
    
    day = (state["day_counter"] - 1) % len(EVENING_PROMPTS)
    book, prompt = EVENING_PROMPTS[day]
    
    today = datetime.now().strftime("%A, %B %d")
    
    text = f"""◑ *Evening Review — {today}*

━━━━━━━━━━━━━━━━━━
🔍 *Reflection — {book}*
{prompt}

━━━━━━━━━━━━━━━━━━
*Three quick questions:*
1. What was today's biggest WIN?
2. Where did you drift or operate below your genius?
3. One thing to carry into tomorrow?

━━━━━━━━━━━━━━━━━━
_Reply freely — I'll engage with whatever's on your mind._
_Log a win: /win [what happened]_
_Add a book note: /booknote [book title] [your insight]_"""

    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")

def run_async(coro):
    """Run async function from sync scheduler."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coro)
    loop.close()

def schedule_morning():
    run_async(send_morning_message())

def schedule_evening():
    run_async(send_evening_message())

# ═══════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *Personal OS — Online*\n\n"
        "I'm your accountability agent. I know your plan, your books, and your wiring.\n\n"
        "I'll message you every morning at 6:30 AM and every evening at 8:30 PM.\n\n"
        "*Commands:*\n"
        "/goals — view + add goals\n"
        "/win — log a win\n"
        "/books — view your library\n"
        "/booknote — add a reflection from a book\n"
        "/model — get a random mental model\n"
        "/check — how are you doing vs. the plan?\n"
        "/morning — trigger morning message now\n"
        "/evening — trigger evening message now\n"
        "/help — full command list\n\n"
        "_Just talk to me freely anytime — I'll respond as your thinking partner._",
        parse_mode="Markdown"
    )

async def cmd_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    args = context.args
    
    if args:
        # Adding a new goal
        new_goal = " ".join(args)
        state["goals"].append({
            "text": new_goal,
            "added": str(date.today()),
            "status": "active"
        })
        save_state(state)
        await update.message.reply_text(f"✅ Goal locked in:\n_{new_goal}_\n\nBlaze Genius reminder: goals are achieved through WHO, not HOW. Who needs to know about this?", parse_mode="Markdown")
    else:
        # Show current goals
        if not state["goals"]:
            await update.message.reply_text("No goals logged yet. Add one: /goals [your goal]")
            return
        
        active = [g for g in state["goals"] if g.get("status") == "active"]
        done = [g for g in state["goals"] if g.get("status") == "done"]
        
        text = "🎯 *Active Goals:*\n"
        for i, g in enumerate(active, 1):
            text += f"{i}. {g['text']} _(added {g['added']})_\n"
        
        if done:
            text += f"\n✅ *Completed ({len(done)}):*\n"
            for g in done[-3:]:
                text += f"• ~~{g['text']}~~\n"
        
        text += "\n_Add goal: /goals [text] | Complete: /done [number]_"
        await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    args = context.args
    active = [g for g in state["goals"] if g.get("status") == "active"]
    
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /done [goal number from /goals]")
        return
    
    idx = int(args[0]) - 1
    if 0 <= idx < len(active):
        active[idx]["status"] = "done"
        active[idx]["completed"] = str(date.today())
        goal_text = active[idx]["text"]
        save_state(state)
        
        # Get a celebratory Claude response
        reply = ask_claude(f"Deryl just completed a goal: '{goal_text}'. Give him a short, genuine acknowledgment that connects this win to his bigger vision. Keep it under 100 words — energetic but not over the top.")
        await update.message.reply_text(f"🏆 *Goal complete:* _{goal_text}_\n\n{reply}", parse_mode="Markdown")
    else:
        await update.message.reply_text("Goal number not found. Check /goals for the list.")

async def cmd_win(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    args = context.args
    
    if not args:
        # Show recent wins
        if not state["wins"]:
            await update.message.reply_text("No wins logged yet. Log one: /win [what happened]")
            return
        text = "🏆 *Recent Wins:*\n"
        for w in state["wins"][-7:]:
            text += f"• {w['text']} _{w['date']}_\n"
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        win = " ".join(args)
        state["wins"].append({"text": win, "date": str(date.today())})
        save_state(state)
        
        reply = ask_claude(f"Deryl logged this win: '{win}'. Acknowledge it briefly and connect it to one principle from his books or plan. Under 80 words.")
        await update.message.reply_text(f"⚡ *Win logged:* _{win}_\n\n{reply}", parse_mode="Markdown")

async def cmd_booknote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /booknote [book] [your insight]\n\n"
            "Example: /booknote naval The specific knowledge insight hit different — my Lake Ozark community connection IS my moat.\n\n"
            "Books: mmp, swy, naval, hill, genekeys, wave, field, rubin, hph, dyer, psycho, warrior, peterson, dieda, tolle, wrestle, outwitting"
        )
        return
    
    book_key = args[0].lower()
    note = " ".join(args[1:])
    
    if book_key not in state["book_notes"]:
        state["book_notes"][book_key] = []
    
    state["book_notes"][book_key].append({
        "note": note,
        "date": str(date.today())
    })
    save_state(state)
    
    # Get Claude to synthesize the note with his plan
    reply = ask_claude(f"Deryl just added this reflection from '{book_key}': '{note}'. In 2-3 sentences, connect this insight to something specific in his life plan or current phase. Be concrete.")
    await update.message.reply_text(f"📖 *Note saved for {book_key}:*\n_{note}_\n\n💡 {reply}", parse_mode="Markdown")

async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import random
    state = load_state()
    model_title, model_action = random.choice(MENTAL_MODELS)
    
    # Claude adds a specific application
    reply = ask_claude(f"The mental model is: '{model_title}'. The practice prompt is: '{model_action}'. Add one very specific way this applies to Deryl's life RIGHT NOW — this week, this phase. Under 60 words.")
    
    await update.message.reply_text(
        f"🧠 *Mental Model: {model_title}*\n\n"
        f"_{model_action}_\n\n"
        f"*Right now for you:* {reply}",
        parse_mode="Markdown"
    )

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    today = datetime.now().strftime("%A, %B %d")
    
    # Build a context summary for Claude
    wins_summary = f"{len(state['wins'])} wins logged" if state["wins"] else "no wins logged yet"
    goals_summary = f"{len([g for g in state['goals'] if g.get('status') == 'active'])} active goals" if state["goals"] else "no goals set yet"
    notes_count = sum(len(v) for v in state["book_notes"].values())
    
    reply = ask_claude(
        f"Today is {today}. Give Deryl a quick honest check-in on where he is vs. his plan. "
        f"Context: {wins_summary}, {goals_summary}, {notes_count} book notes logged. "
        f"He's currently in Phase 0 (Foundation) — MO RE exam Saturday, peptide protocol starts April 20, summer bartending strategy. "
        f"Be direct, specific, and encourage the next concrete action. Under 150 words."
    )
    
    await update.message.reply_text(f"📊 *Check-in — {today}*\n\n{reply}", parse_mode="Markdown")

async def cmd_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_morning_message()
    
async def cmd_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_evening_message()

async def cmd_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    
    book_list = [
        ("📕 MMP", "Millionaire Master Plan"),
        ("📙 SWY", "Start With Why"),
        ("📘 NAVAL", "Almanac of Naval Ravikant"),
        ("📗 HILL", "Laws of Success / Outwitting the Devil"),
        ("📓 GK", "Gene Keys"),
        ("🌊 WAVE", "The Coming Wave"),
        ("✨ FIELD", "The Field"),
        ("🎨 RUBIN", "The Creative Act"),
        ("⚡ HPH", "High Performance Habits"),
        ("🌿 DYER", "Change Your Thoughts Change Your Life"),
        ("🔵 PSYCHO", "Psycho-Cybernetics"),
        ("⚔️ WARRIOR", "Way of the Peaceful Warrior"),
        ("📐 PETERSON", "Beyond Order / We Who Wrestle with God"),
        ("🔴 DIEDA", "Way of the Superior Man"),
        ("🌍 TOLLE", "A New Earth"),
    ]
    
    text = "📚 *Your Library (18 books)*\n\n"
    for emoji_key, title in book_list:
        key = emoji_key.split(" ")[1].lower()
        notes = len(state["book_notes"].get(key, []))
        note_str = f" _{notes} notes_" if notes > 0 else ""
        text += f"{emoji_key}: {title}{note_str}\n"
    
    text += "\n_Add a note: /booknote [key] [insight]_\n_Example: /booknote naval ..._"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *Deryl's Personal OS — Commands*\n\n"
        "*/start* — restart and see welcome\n"
        "*/goals* — view active goals\n"
        "*/goals [text]* — add a new goal\n"
        "*/done [number]* — mark goal complete\n"
        "*/win [text]* — log a win\n"
        "*/win* — view recent wins\n"
        "*/books* — view full library + note counts\n"
        "*/booknote [book] [insight]* — save a book reflection\n"
        "*/model* — get a random mental model + application\n"
        "*/check* — honest check-in vs. your plan\n"
        "*/morning* — send morning message now\n"
        "*/evening* — send evening message now\n"
        "*/help* — this list\n\n"
        "*Or just talk.* Message anything — I'll respond as your thinking partner.\n\n"
        "_Morning messages: 6:30 AM | Evening: 8:30 PM_",
        parse_mode="Markdown"
    )

# ═══════════════════════════════════════════════════════
# FREE-FORM CONVERSATION HANDLER
# ═══════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any non-command message — thinking partner conversation."""
    user_text = update.message.text
    state = load_state()
    
    # Add to conversation history
    state["conversation_history"].append({"role": "user", "content": user_text})
    
    # Keep history manageable
    if len(state["conversation_history"]) > 20:
        state["conversation_history"] = state["conversation_history"][-20:]
    
    # Get Claude response
    reply = ask_claude(user_text, state["conversation_history"][:-1])
    
    # Add assistant reply to history
    state["conversation_history"].append({"role": "assistant", "content": reply})
    save_state(state)
    
    await update.message.reply_text(reply)

# ═══════════════════════════════════════════════════════
# SCHEDULER — runs in background thread
# ═══════════════════════════════════════════════════════

def run_scheduler():
    schedule.every().day.at("06:30").do(schedule_morning)
    schedule.every().day.at("20:30").do(schedule_evening)
    
    print("⏰ Scheduler running — morning 6:30 AM, evening 8:30 PM")
    while True:
        schedule.run_pending()
        time.sleep(60)

# ═══════════════════════════════════════════════════════
# MAIN — start the bot
# ═══════════════════════════════════════════════════════

def main():
    print("🔥 Deryl's Personal OS Bot — Starting...")
    
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Build Telegram app
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Register handlers
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
    
    print("✅ Bot online. Listening for messages...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
