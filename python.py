import os
import io
import PIL.Image
import asyncio
import nest_asyncio
import textwrap
from pyrogram import Client, filters, idle
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Poll,
    CallbackQuery
)
from pyrogram.enums import PollType
import google.generativeai as genai
import google.api_core.exceptions

# ========= Configuration Storage =========
class Config:
    def __init__(self):
        self.AUTHORIZED_USERS = {7145991193}
        self.TARGET_CHANNEL = -1002464876558
        self.PREFIX = "[POLL]"

        self.GOOGLE_API_KEYS = [
            "AIzaSyCrhbN2hWfiXUfeEYiASumL_H0hUcz4aI8",
            "AIzaSyCukxeJuSgs02-I-r7kp6_aYLkdqqfv4h4"
        ]
        self.api_key_index = 0

        self.EXPLANATION_LINK = "t.me/link"
        self.EXPLANATION_ENABLED = True
        self.PREFIX_ENABLED = True

    def get_next_api_key(self):
        """চক্রাকারে তালিকা থেকে পরবর্তী API কী প্রদান কর>
        key = self.GOOGLE_API_KEYS[self.api_key_index]
        self.api_key_index = (self.api_key_index + 1) >
        print(f"Using API key ending with ...{key[-4:]>
        return key

config = Config()      

# ========= Bot Setup =========
API_ID = 26400657
API_HASH = "c20ddfa6c36b3fb15cabc735c180f738"
BOT_TOKEN = "8071512279:AAFJyCv1J33Z2lh_y_DQ2fuaF8Fzt8>
MODEL_NAME = "gemini-2.5-flash"

app = Client("mcq_quiz_bot", api_id=API_ID, api_hash=A>

created_polls = {}

async def is_authorized(user_id):
    return user_id in config.AUTHORIZED_USERS

# ... (Admin Command Handler and Settings handlers rem>
# ========= Admin Command Handler =========
@app.on_message(filters.command(["01869293233"]))
async def manage_authorized_users(client: Client, mess>
    if message.from_user.id not in config.AUTHORIZED_U>
        return await message.reply_text("🚫 এই কমান্ড শু>

    if len(message.command) < 2:
user_list = ", ".join(f"`{uid}`" for uid in co>
        return await message.reply_text(
            f"🔐 অনুমোদিত ব্যবহারকারীগণ:\n{user_list}\n\>
            "**ব্যবহার:**\n"
            "`/01869293233 add <user_id>`\n"
            "`/01869293233 remove <user_id>`"
        )

    action = message.command[1].lower()
    if len(message.command) < 3:
        return await message.reply_text("❌ User ID প্র>

    try:
        user_id_to_manage = int(message.command[2])
    except ValueError:
        return await message.reply_text("❌ User ID অব>

    if action == "add":
        config.AUTHORIZED_USERS.add(user_id_to_manage)
        await message.reply_text(f"✅ ব্যবহারকারী `{use>
    elif action == "remove":
        if user_id_to_manage in config.AUTHORIZED_USER>
            return await message.reply_text("❌ আপনি এ>
        config.AUTHORIZED_USERS.discard(user_id_to_man>
        await message.reply_text(f"✅ ব্যবহারকারী `{use>
    else:
        await message.reply_text("❌ ভুল অ্যাকশন। 'add' >

# ========= Settings Handlers (Updated) =========
async def get_settings_markup_and_text():
    exp_status = "অন" if config.EXPLANATION_ENABLED el>
    prefix_status = "অন" if config.PREFIX_ENABLED else>

    exp_button_text = f"ব্যাখ্যা লিঙ্ক {'অফ' if config.EX>
    prefix_button_text = f"প্রিফিক্স {'অফ' if config.PRE>

    text = (
        f"⚙️ বর্তমান সেটিংস:\n\n"
        f"• চ্যানেল আইডি: `{config.TARGET_CHANNEL}`\n"
        f"• প্রিফিক্স: `{config.PREFIX}` (অবস্থা: **{pref>
        f"• ব্যাখ্যা লিঙ্ক: `{config.EXPLANATION_LINK}` (>
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(exp_button_text, callbac>
        [InlineKeyboardButton(prefix_button_text, call>
        [InlineKeyboardButton("📢 চ্যানেল আইডি পরিবর্তন">
        [InlineKeyboardButton("🏷️ প্রিফিক্স পরিবর্তন", cal>
        [InlineKeyboardButton("🔗 ব্যাখ্যা লিঙ্ক পরিবর্তন">
        [InlineKeyboardButton("❌ বন্ধ করুন", callback_d>
    ])
    return text, markup

@app.on_message(filters.command(["settings"]))
async def settings_cmd(client: Client, message: Messag>
    if not await is_authorized(message.from_user.id): >
    settings_text, settings_markup = await get_setting>
    await message.reply_text(settings_text, reply_mark>

@app.on_callback_query(filters.regex(r"^(toggle_explan>
async def handle_settings_callbacks(client: Client, ca>
    if not await is_authorized(callback.from_user.id):>

    action = callback.data
     if action == "toggle_explanation":
        config.EXPLANATION_ENABLED = not config.EXPLAN>
        await callback.answer(f"ব্যাখ্যা লিঙ্ক এখন {'অন' >

    elif action == "toggle_prefix":
        config.PREFIX_ENABLED = not config.PREFIX_ENAB>
        await callback.answer(f"প্রিফিক্স এখন {'অন' if c>

    elif action in ["set_channel", "set_prefix", "set_>
        prompts = {
            "set_channel": "📢 নতুন চ্যানেল আইডি পাঠান:",
            "set_prefix": "🏷️ নতুন প্রিফিক্স পাঠান:",
            "set_link": "🔗 নতুন ব্যাখ্যা লিঙ্ক পাঠান:",
        }
        await callback.message.edit_text(prompts[actio>
        return await callback.answer()

    elif action == "close_settings":
        await callback.message.delete()
        return await callback.answer("সেটিংস বন্ধ করা হ>

    settings_text, settings_markup = await get_setting>
    await callback.message.edit_text(settings_text, re>


@app.on_message(filters.private & ~filters.command(["s>
async def handle_settings_input(client: Client, messag>
    if not await is_authorized(message.from_user.id): >
    if not message.reply_to_message or not message.rep>

    reply_text = message.reply_to_message.text
    original_message = message.reply_to_message

    if "চ্যানেল আইডি" in reply_text:
        try:
            config.TARGET_CHANNEL = int(message.text.s>
            await message.reply(f"✅ চ্যানেল আইডি আপডেট>
        except ValueError:
            await message.reply("❌ অবৈধ চ্যানেল আইডি!")
    elif "প্রিফিক্স" in reply_text:
        config.PREFIX = message.text.strip()
             await message.reply(f"✅ প্রিফিক্স আপডেট করা হয়ে>
    elif "ব্যাখ্যা লিঙ্ক" in reply_text:
        config.EXPLANATION_LINK = message.text.strip()
        await message.reply(f"✅ ব্যাখ্যা লিঙ্ক আপডেট করা>

    await original_message.delete()


# ========= MCQ Command (Updated with Round-Robin Logi>
@app.on_message(filters.command(["mcq"]))
async def mcq_cmd(client: Client, message: Message):
    global created_polls
    if not await is_authorized(message.from_user.id): >
    if not message.reply_to_message or not message.rep>

    status_msg = await message.reply("🔍 ছবি বিশ্লেষণ ক>
    api_key = "" # ত্রুটি বার্তায় দেখানোর জন্য

    try:
        # প্রতিটি কমান্ডের জন্য পরবর্তী API কী নেওয়া হচ্ছে
        api_key = config.get_next_api_key()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)

        img_data = await client.download_media(message>
        img = PIL.Image.open(io.BytesIO(img_data.getbu>

        prompt = textwrap.dedent("""
            # ভূমিকা:
            আপনি একজন বিশেষজ্ঞ OCR ডেটা এক্সট্র্যাকশন সহকা>
            # আউটপুট ফরম্যাট:
            প্রশ্ন: [প্রশ্নের টেক্সট প্রশ্নের নাম্বার ছাড়া]
            ক) [অপশন ক]
            খ) [অপশন খ]
            গ) [অপশন গ]
            ঘ) [অপশন ঘ]
            ঙ) [অপশন ঙ]- যদি থাকে ছবিতে
            সঠিক উত্তর: [সঠিক উত্তরের বর্ণ]
            # নিয়মাবলী: ...
        """)

        response = await asyncio.to_thread(
            model.generate_content, [prompt, img]
        )

        extracted_text = response.text
        # ... (বাকি কোড আগের মতোই) ...
        question_blocks = []
        current_block = {}
        OPTION_LABELS = ["ক", "খ", "গ", "ঘ", "ঙ"]

        for line in extracted_text.split('\n'):
            line = line.strip()
            if not line: continue
            if line.startswith("প্রশ্ন:"):
                if current_block: question_blocks.appe>
                current_block = {"question": line.repl>
            elif line.startswith(tuple(f"{label})" for>
                current_block["options"][line[0]] = li>
            elif line.startswith("সঠিক উত্তর:"):
                current_block["correct"] = line.replac>

        if current_block: question_blocks.append(curre>
        created_polls.clear()

        for block in question_blocks:
            try:
                found_labels = sorted(block.get("optio>
                if not found_labels: continue

                options_list = [f"{block['options'][la>
                correct_option_id = found_labels.index>

                question_text = block['question']
                if config.PREFIX_ENABLED:
                       question_text = f"{config.PREFIX}\>

                poll_explanation = config.EXPLANATION_>

                poll_message = await client.send_poll(
                    chat_id=message.chat.id,
                    question=question_text,
                    options=options_list,
                    correct_option_id=correct_option_i>
                    type=PollType.QUIZ,
                    explanation=poll_explanation,
                    is_anonymous=True
                )

                poll_data = { "question": question_tex>
                created_polls[poll_message.id] = poll_>

                markup = InlineKeyboardMarkup([
                    [ InlineKeyboardButton("🗑️ ডিলিট", >
                ])
                await poll_message.edit_reply_markup(r>

                await asyncio.sleep(3)

            except Exception as e:
                await message.reply(f"'{block.get('que>
                continue

        await status_msg.edit_text(f"✅ {len(created_p>

    except google.api_core.exceptions.ResourceExhauste>
        await status_msg.edit_text(f"❌ API Key (...{a>
    except Exception as e:
        await status_msg.edit_text(f"❌ একটি মারাত্মক ত্>

# ... (বাকি সকল ফাংশন অপরিবর্তিত) ...
@app.on_callback_query(filters.regex(r"^(delete|edit)_>
async def handle_poll_actions(client: Client, callback>
    if not await is_authorized(callback.from_user.id):
        return await callback.answer("🚫 অননুমোদিত অ্যাক্>

    action = callback.matches[0].group(1)
    message_id = int(callback.matches[0].group(2))

    if action == "delete":
        if message_id in created_polls:
            del created_polls[message_id]
            await callback.message.delete()
                await callback.answer("🗑️ পোলটি ডিলিট করা হ>
        else:
            await callback.answer("❌ এই পোলটি আর উপলব্>

    elif action == "edit":
        if message_id not in created_polls:
            return await callback.answer("❌ এই পোলটি >

        poll_data = created_polls[message_id]
        buttons = []
        for i, label in enumerate(poll_data["option_la>
            buttons.append(
                InlineKeyboardButton(
                    f"{label}",
                    callback_data=f"setcorrect_{messag>
                )
            )

        markup = InlineKeyboardMarkup([buttons[i:i + 2>
        await callback.message.edit_text(
            "✏️ নতুন সঠিক উত্তর নির্বাচন করুন:",
            reply_markup=markup
        )
        await callback.answer()

@app.on_callback_query(filters.regex(r"^setcorrect_(\d>
async def set_correct_answer(client: Client, callback:>
    if not await is_authorized(callback.from_user.id):
        return await callback.answer("🚫 অননুমোদিত অ্যাক্>

    original_message_id = int(callback.matches[0].grou>
    new_correct_index = int(callback.matches[0].group(>

    if original_message_id not in created_polls:
        return await callback.answer("❌ মূল পোলটি খুঁজে >

    await callback.message.delete()
    poll_data = created_polls.pop(original_message_id)
    poll_data["correct_option_id"] = new_correct_index

    try:
        new_poll_message = await client.send_poll(
            chat_id=callback.message.chat.id,
            question=poll_data["question"],
            options=poll_data["options"],
            correct_option_id=poll_data["correct_optio>
            type=PollType.QUIZ,
            explanation=poll_data.get("explanation"),
            is_anonymous=True
        )
        created_polls[new_poll_message.id] = poll_data
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ ডিলিট", callba>
                InlineKeyboardButton("✏️ এডিট", callbac>
            ]
        ])
        await new_poll_message.edit_reply_markup(reply>
        await callback.answer("✅ সঠিক উত্তর আপডেট করা >
    except Exception as e:
        await callback.message.reply_text(f"❌ পোলটি পু>

@app.on_message(filters.command(["send"]))
async def send_to_channel(client: Client, message: Mes>
    global created_polls
    if not await is_authorized(message.from_user.id): >
    if not created_polls: return await message.reply_t>

    status_msg = await message.reply(f"📢 {config.TARG>
    success_count = 0
    polls_to_send = list(created_polls.values())

    for poll in polls_to_send:
        try:
            await client.send_poll(
               chat_id=config.TARGET_CHANNEL,
                question=poll["question"],
                options=poll["options"],
                correct_option_id=poll["correct_option>
                type=PollType.QUIZ,
                explanation=poll.get("explanation"),
                is_anonymous=True
            )
            success_count += 1
            await asyncio.sleep(2)
        except Exception as e:
            await message.reply(f"'{poll['question']}'>
            continue

    await status_msg.edit_text(f"✅ {success_count}/{l>
    created_polls.clear()

@app.on_message(filters.command(["start", "help"]))
async def start_help_command(client: Client, message: >
    if not await is_authorized(message.from_user.id): >
    help_text = textwrap.dedent("""
        **🤖 MCQ Quiz Bot Help**
        - `/mcq`: Reply to an image to create polls.
        - `/send`: Send created polls to the channel.
        - `/settings`: Configure the bot.
    """)
    await message.reply_text(help_text)
# ========= Start Bot =========
async def main():
    await app.start()
    print("🤖 বট সক্রিয় হয়েছে!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
        
