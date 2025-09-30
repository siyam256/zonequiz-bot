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

# ========= Configuration Storage =========
class Config:
    def __init__(self):
        self.AUTHORIZED_USERS = {7145991193}
        self.TARGET_CHANNEL = -1002464876558
        self.PREFIX = "[YOUR POLL]"
        self.GOOGLE_API_KEY = "AIzaSyDgGsCUaG3SaoEZ0R8XYlRneRNNSyJExUU"
        self.EXPLANATION_LINK = "t.me/link" # এই লাইনটি আবার যুক্ত করা হয়েছে

config = Config()

# ========= Bot Setup =========
API_ID = 26400657
API_HASH = "c20ddfa6c36b3fb15cabc735c180f738"
BOT_TOKEN = "8071512279:AAFJyCv1J33Z2lh_y_DQ2fuaF8Fzt8O1N7I"
MODEL_NAME = "gemini-1.5-flash"

app = Client("mcq_quiz_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

created_polls = {}

async def is_authorized(user_id):
    return user_id in config.AUTHORIZED_USERS

# ========= Admin Command Handler =========
@app.on_message(filters.command(["01869293233"]))
async def manage_authorized_users(client: Client, message: Message):
    if message.from_user.id not in config.AUTHORIZED_USERS:
        return await message.reply_text("🚫 এই কমান্ড শুধুমাত্র অনুমোদিত ব্যবহারকারীগণ ব্যবহার করতে পারবেন।")

    if len(message.command) < 2:
        user_list = ", ".join(f"`{uid}`" for uid in config.AUTHORIZED_USERS)
        return await message.reply_text(
            f"🔐 অনুমোদিত ব্যবহারকারীগণ:\n{user_list}\n\n"
            "**ব্যবহার:**\n"
            "`/01869293233 add <user_id>`\n"
            "`/01869293233 remove <user_id>`"
        )

    action = message.command[1].lower()
    if len(message.command) < 3:
        return await message.reply_text("❌ User ID প্রয়োজন।")

    try:
        user_id_to_manage = int(message.command[2])
    except ValueError:
        return await message.reply_text("❌ User ID অবশ্যই একটি সংখ্যা হতে হবে।")

    if action == "add":
        config.AUTHORIZED_USERS.add(user_id_to_manage)
        await message.reply_text(f"✅ ব্যবহারকারী `{user_id_to_manage}`-কে যুক্ত করা হয়েছে।")
    elif action == "remove":
        if user_id_to_manage in config.AUTHORIZED_USERS and len(config.AUTHORIZED_USERS) == 1:
            return await message.reply_text("❌ আপনি একমাত্র অ্যাডমিনকে সরাতে পারবেন না।")
        config.AUTHORIZED_USERS.discard(user_id_to_manage)
        await message.reply_text(f"✅ ব্যবহারকারী `{user_id_to_manage}`-কে সরিয়ে দেওয়া হয়েছে।")
    else:
        await message.reply_text("❌ ভুল অ্যাকশন। 'add' অথবা 'remove' ব্যবহার করুন।")

# ========= Settings Handlers (Simplified) =========
async def get_settings_markup_and_text():
    text = (
        f"⚙️ বর্তমান সেটিংস:\n\n"
        f"• চ্যানেল আইডি: `{config.TARGET_CHANNEL}`\n"
        f"• প্রিফিক্স: `{config.PREFIX}`\n"
        f"• ব্যাখ্যা লিঙ্ক: `{config.EXPLANATION_LINK}`"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 চ্যানেল আইডি পরিবর্তন", callback_data="set_channel")],
        [InlineKeyboardButton("🏷️ প্রিফিক্স পরিবর্তন", callback_data="set_prefix")],
        [InlineKeyboardButton("🔗 ব্যাখ্যা লিঙ্ক পরিবর্তন", callback_data="set_link")],
        [InlineKeyboardButton("❌ বন্ধ করুন", callback_data="close_settings")]
    ])
    return text, markup

@app.on_message(filters.command(["settings"]))
async def settings_cmd(client: Client, message: Message):
    if not await is_authorized(message.from_user.id): return await message.reply_text("🚫 অননুমোদিত অ্যাক্সেস")
    settings_text, settings_markup = await get_settings_markup_and_text()
    await message.reply_text(settings_text, reply_markup=settings_markup)

@app.on_callback_query(filters.regex(r"^(set_channel|set_prefix|set_link|close_settings)$"))
async def handle_settings_callbacks(client: Client, callback: CallbackQuery):
    if not await is_authorized(callback.from_user.id): return await callback.answer("🚫 অননুমোদিত অ্যাক্সেস", show_alert=True)

    action = callback.data

    if action in ["set_channel", "set_prefix", "set_link"]:
        prompts = {
            "set_channel": "📢 নতুন চ্যানেল আইডি পাঠান (উদাহরণ: -100123456789):",
            "set_prefix": "🏷️ নতুন প্রিফিক্স পাঠান (উদাহরণ: [QUIZ]):",
            "set_link": "🔗 নতুন ব্যাখ্যা লিঙ্ক পাঠান (উদাহরণ: t.me/yourchannel):",
        }
        await callback.message.edit_text(prompts[action])
        await callback.answer()

    elif action == "close_settings":
        await callback.message.delete()
        await callback.answer("সেটিংস বন্ধ করা হয়েছে")

@app.on_message(filters.private & ~filters.command(["start", "help", "mcq", "send", "settings", "01869293233"]))
async def handle_settings_input(client: Client, message: Message):
    if not await is_authorized(message.from_user.id): return
    if not message.reply_to_message or not message.reply_to_message.from_user.is_self: return

    reply_text = message.reply_to_message.text
    original_message = message.reply_to_message

    if "চ্যানেল আইডি" in reply_text:
        try:
            config.TARGET_CHANNEL = int(message.text.strip())
            await message.reply(f"✅ চ্যানেল আইডি আপডেট করা হয়েছে: `{config.TARGET_CHANNEL}`")
            await original_message.delete()
        except ValueError:
            await message.reply("❌ অবৈধ চ্যানেল আইডি! শুধু সংখ্যা ব্যবহার করুন।")
    elif "প্রিফিক্স" in reply_text:
        config.PREFIX = message.text.strip()
        await message.reply(f"✅ প্রিফিক্স আপডেট করা হয়েছে: `{config.PREFIX}`")
        await original_message.delete()
    elif "ব্যাখ্যা লিঙ্ক" in reply_text:
        config.EXPLANATION_LINK = message.text.strip()
        await message.reply(f"✅ ব্যাখ্যা লিঙ্ক আপডেট করা হয়েছে: `{config.EXPLANATION_LINK}`")
        await original_message.delete()


# ========= MCQ Command =========
@app.on_message(filters.command(["mcq"]))
async def mcq_cmd(client: Client, message: Message):
    global created_polls
    if not await is_authorized(message.from_user.id): return await message.reply_text("🚫 অননুমোদিত অ্যাক্সেস")
    if not message.reply_to_message or not message.reply_to_message.photo: return await message.reply_text("❌ একটি MCQ ছবিতে রিপ্লাই করুন")

    status_msg = await message.reply("🔍 ছবি বিশ্লেষণ করা হচ্ছে...")

    try:
        genai.configure(api_key=config.GOOGLE_API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)

        img_data = await client.download_media(message.reply_to_message, in_memory=True)
        img = PIL.Image.open(io.BytesIO(img_data.getbuffer()))

        prompt = textwrap.dedent("""
            # ভূমিকা:
            আপনি একজন বিশেষজ্ঞ OCR ডেটা এক্সট্র্যাকশন সহকারী।
            # আউটপুট ফরম্যাট:
            প্রশ্ন: [প্রশ্নের টেক্সট প্রশ্নের নাম্বার ছাড়া]
            ক) [অপশন ক]
            খ) [অপশন খ]
            গ) [অপশন গ]
            ঘ) [অপশন ঘ]
            ঙ) [অপশন ঙ]- যদি থাকে ছবিতে
            সঠিক উত্তর: [সঠিক উত্তরের বর্ণ]
            # নিয়মাবলী:
            ১.প্রশ্ন হুবহু কপি করবে শুধু প্রশ্নের নম্বর ও অপসনগুলো ছাড়া। কোনো অনুবাদ বা পরিবর্তন করবে না।
            ২. **সম্পূর্ণ প্রশ্ন কপি:** প্রশ্নের মূল অংশের সাথে যদি বহুপদী অংশ (যেমন: i, ii, iii) থাকে, তাহলে **অবশ্যই** সেই সবগুলোকে মূল প্রশ্নের সাথে একই লাইনে স্পেস না দিয়ে যুক্ত করতে হবে। তবে অপসন গুলো কপি করবেনা। 
            ৩. ইউনিকোড (এই ফরম্যাট কঠোরভাবে অনুসরণ করবে):
            - সাধারণ সাবস্ক্রিপ্ট: `H2O` হবে `H₂O`
            - একাধিক সাবস্ক্রিপ্ট: `C3H8` হবে `C₃H₈`
            - সাধারণ সুপারস্ক্রিপ্ট: `a^2` বা `a2` হবে `a²`
            - একাধিক অক্ষরের সুপারস্ক্রিপ্ট: `Ca2+` হবে `Ca²⁺`
            - ঋণাত্মক সুপারস্ক্রিপ্ট: `10^-3` হবে `10⁻³`
        """)
        response = await asyncio.to_thread(
            model.generate_content,
            [prompt, img],
        )

        extracted_text = response.text
        question_blocks = []
        current_block = {}
        OPTION_LABELS = ["ক", "খ", "গ", "ঘ", "ঙ"]

        for line in extracted_text.split('\n'):
            line = line.strip()
            if not line: continue
            if line.startswith("প্রশ্ন:"):
                if current_block: question_blocks.append(current_block)
                current_block = {"question": line.replace("প্রশ্ন:", "").strip(), "options": {}, "correct": ""}
            elif line.startswith(tuple(f"{label})" for label in OPTION_LABELS)):
                current_block["options"][line[0]] = line[2:].strip()
            elif line.startswith("সঠিক উত্তর:"):
                current_block["correct"] = line.replace("সঠিক উত্তর:", "").strip()
        
        if current_block: question_blocks.append(current_block)
        created_polls.clear()

        for block in question_blocks:
            try:
                found_labels = sorted(block.get("options", {}).keys())
                if not found_labels: continue

                options_list = [f"{block['options'][label]}" for label in found_labels]
                correct_option_id = found_labels.index(block['correct'])
                question_text = f"{config.PREFIX}\n{block['question']}"
                
                # ব্যাখ্যা হিসেবে কনফিগারেশন থেকে লিঙ্ক ব্যবহার
                poll_explanation = config.EXPLANATION_LINK

                poll_message = await client.send_poll(
                    chat_id=message.chat.id,
                    question=question_text,
                    options=options_list,
                    correct_option_id=correct_option_id,
                    type=PollType.QUIZ,
                    explanation=poll_explanation,
                    is_anonymous=True
                )

                poll_data = {
                    "question": question_text,
                    "options": options_list,
                    "correct_option_id": correct_option_id,
                    "option_labels": found_labels,
                    "explanation": poll_explanation # ডাটার মধ্যে ব্যাখ্যা লিঙ্ক সেভ করা
                }
                created_polls[poll_message.id] = poll_data

                markup = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🗑️ ডিলিট", callback_data=f"delete_{poll_message.id}"),
                        InlineKeyboardButton("✏️ এডিট", callback_data=f"edit_{poll_message.id}")
                    ]
                ])
                await poll_message.edit_reply_markup(reply_markup=markup)
                await asyncio.sleep(2)
            except Exception as e:
                await message.reply(f"'{block.get('question', 'একটি প্রশ্ন')}' তৈরিতে ত্রুটি: {e}")
                continue

        await status_msg.edit_text(f"✅ {len(created_polls)}টি পোল তৈরি হয়েছে!\n\n📢 চ্যানেলে পাঠাতে /send দিন")
    except Exception as e:
        await status_msg.edit_text(f"❌ একটি মারাত্মক ত্রুটি হয়েছে: {e}")

# ========= New Callback Handlers for Edit/Delete =========
@app.on_callback_query(filters.regex(r"^(delete|edit)_(\d+)"))
async def handle_poll_actions(client: Client, callback: CallbackQuery):
    if not await is_authorized(callback.from_user.id):
        return await callback.answer("🚫 অননুমোদিত অ্যাক্সেস", show_alert=True)

    action = callback.matches[0].group(1)
    message_id = int(callback.matches[0].group(2))

    if action == "delete":
        if message_id in created_polls:
            del created_polls[message_id]
            await callback.message.delete()
            await callback.answer("🗑️ পোলটি ডিলিট করা হয়েছে।", show_alert=False)
        else:
            await callback.answer("❌ এই পোলটি আর উপলব্ধ নেই।", show_alert=True)

    elif action == "edit":
        if message_id not in created_polls:
            return await callback.answer("❌ এই পোলটি আর উপলব্ধ নেই।", show_alert=True)

        poll_data = created_polls[message_id]
        buttons = []
        for i, label in enumerate(poll_data["option_labels"]):
            buttons.append(
                InlineKeyboardButton(
                    f"{label}",
                    callback_data=f"setcorrect_{message_id}_{i}"
                )
            )

        markup = InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])
        await callback.message.edit_text(
            "✏️ নতুন সঠিক উত্তর নির্বাচন করুন:",
            reply_markup=markup
        )
        await callback.answer()

@app.on_callback_query(filters.regex(r"^setcorrect_(\d+)_(\d+)"))
async def set_correct_answer(client: Client, callback: CallbackQuery):
    if not await is_authorized(callback.from_user.id):
        return await callback.answer("🚫 অননুমোদিত অ্যাক্সেস", show_alert=True)

    original_message_id = int(callback.matches[0].group(1))
    new_correct_index = int(callback.matches[0].group(2))

    if original_message_id not in created_polls:
        return await callback.answer("❌ মূল পোলটি খুঁজে পাওয়া যায়নি।", show_alert=True)

    await callback.message.delete()
    poll_data = created_polls.pop(original_message_id)
    poll_data["correct_option_id"] = new_correct_index

    try:
        new_poll_message = await client.send_poll(
            chat_id=callback.message.chat.id,
            question=poll_data["question"],
            options=poll_data["options"],
            correct_option_id=poll_data["correct_option_id"],
            type=PollType.QUIZ,
            explanation=poll_data.get("explanation"),
            is_anonymous=True
        )
        created_polls[new_poll_message.id] = poll_data
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ ডিলিট", callback_data=f"delete_{new_poll_message.id}"),
                InlineKeyboardButton("✏️ এডিট", callback_data=f"edit_{new_poll_message.id}")
            ]
        ])
        await new_poll_message.edit_reply_markup(reply_markup=markup)
        await callback.answer("✅ সঠিক উত্তর আপডেট করা হয়েছে!", show_alert=False)
    except Exception as e:
        await callback.message.reply_text(f"❌ পোলটি পুনরায় তৈরি করতে সমস্যা হয়েছে: {e}")

# ========= Other Handlers =========
@app.on_message(filters.command(["send"]))
async def send_to_channel(client: Client, message: Message):
    global created_polls
    if not await is_authorized(message.from_user.id): return await message.reply_text("🚫 অননুমোদিত অ্যাক্সেস")
    if not created_polls: return await message.reply_text("❌ কোনো পোল তৈরি করা হয়নি।")

    status_msg = await message.reply(f"📢 {config.TARGET_CHANNEL} চ্যানেলে পোল পাঠানো হচ্ছে...")
    success_count = 0
    polls_to_send = list(created_polls.values())

    for poll in polls_to_send:
        try:
            await client.send_poll(
                chat_id=config.TARGET_CHANNEL,
                question=poll["question"],
                options=poll["options"],
                correct_option_id=poll["correct_option_id"],
                type=PollType.QUIZ,
                explanation=poll.get("explanation"),
                is_anonymous=True
            )
            success_count += 1
            await asyncio.sleep(2)
        except Exception as e:
            await message.reply(f"'{poll['question']}' পাঠাতে ত্রুটি: {e}")
            continue

    await status_msg.edit_text(f"✅ {success_count}/{len(polls_to_send)}টি পোল চ্যানেলে পাঠানো হয়েছে")
    created_polls.clear()

@app.on_message(filters.command(["start", "help"]))
async def start_help_command(client: Client, message: Message):
    if not await is_authorized(message.from_user.id): return await message.reply_text("🚫 আপনি এই বট ব্যবহারের জন্য অনুমোদিত নন।")
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