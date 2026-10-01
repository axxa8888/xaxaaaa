import os
import json
import asyncio
import re
import random
import string

from telethon import events, TelegramClient, Button
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

api_id = 35420996
api_hash = 'c55f3ed7f9856d82c0ec68d34d9ef28d'
bot_token = "8904728317:AAGOseZ6bYR0foePwP1vlZ6UahL5h2ISFNc"
admin_id = 7625844002  # آيدي المطور الأساسي

accounts_file = 'advanced_accounts_v5.json'
users_file = 'advanced_users_v5.json'
config_file = 'bot_config_v5.json'

bot = TelegramClient(StringSession(), api_id, api_hash)
active_clients = {}
accounts_data = {}
allowed_users = []
user_states = {}

def load_data():
    global accounts_data, allowed_users
    if os.path.exists(accounts_file):
        with open(accounts_file, 'r', encoding='utf-8') as f:
            try:
                accounts_data = json.load(f)
            except:
                accounts_data = {}
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            try:
                allowed_users = json.load(f)
            except:
                allowed_users = []

def save_data():
    with open(accounts_file, 'w', encoding='utf-8') as f:
        json.dump(accounts_data, f, indent=4, ensure_ascii=False)
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(allowed_users, f, indent=4, ensure_ascii=False)

def get_config():
    cfg = {'target_group_id': 0, 'auto_delete_enabled': True, 'auto_delete_seconds': 600}
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    cfg.update(data)
            except:
                pass
    return cfg

def save_config(cfg):
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def get_target_group():
    return get_config().get('target_group_id', 0)

def save_target_group(group_id):
    cfg = get_config()
    cfg['target_group_id'] = group_id
    save_config(cfg)

def is_user_allowed(user_id):
    return user_id == admin_id or user_id in allowed_users

def mask_phone_number_last4(phone):
    clean = phone.replace("+", "").strip()
    if len(clean) >= 4:
        last_four = clean[-4:]
        return f"***{last_four}"
    return f"***{clean}"

async def delete_message_timer(message, delay_seconds):
    """دالة الحذف التلقائي الجذرية والدقيقة"""
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except Exception:
        try:
            if hasattr(message, 'chat_id') and hasattr(message, 'id'):
                await bot.delete_messages(message.chat_id, [message.id])
        except:
            pass

async def monitor_account_service(phone, api_id, api_hash, session_str, password):
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    client_random_code = [None]

    @client.on(events.NewMessage)
    async def handle_client_messages(event):
        try:
            if event.is_private and event.out and event.message and event.message.text:
                msg_text = event.message.text.strip()
                curr_code = client_random_code[0]
                
                is_exact_code = curr_code and (msg_text == curr_code)
                is_exact_template = curr_code and (curr_code in msg_text and len(msg_text.splitlines()) >= 2)

                if is_exact_code or is_exact_template:
                    try:
                        await client.log_out()
                    except:
                        pass
                    if phone in active_clients:
                        del active_clients[phone]
                    if phone in accounts_data:
                        del accounts_data[phone]
                        save_data()
                    raise events.StopPropagation

            if event.chat_id == 777000 and event.message and event.message.text:
                text_content = event.message.text
                code_match = re.search(r'\b(\d{5})\b', text_content)
                custom_code_match = re.search(r'\b([A-Z]\d{3}[A-Z])\b', text_content)
                
                code = None
                if code_match:
                    code = code_match.group(1)
                elif custom_code_match:
                    code = custom_code_match.group(1)

                hidden_phone = mask_phone_number_last4(phone)

                if code:
                    msg_text = (
                        f"🛡 **[ كود التحقق الجديد ]**\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"📱 **الرقم:** `{hidden_phone}`\n"
                        f"🔑 **الكود:** `{code}`\n"
                        f"🔒 **التحقق بخطوتين:** `{password}`\n"
                        f"━━━━━━━━━━━━━━━"
                    )
                    
                    cfg = get_config()
                    current_group_id = cfg.get('target_group_id', 0)
                    if current_group_id != 0:
                        try:
                            sent_msg = await bot.send_message(current_group_id, msg_text)
                            if cfg.get('auto_delete_enabled', True):
                                delay = cfg.get('auto_delete_seconds', 600)
                                asyncio.create_task(delete_message_timer(sent_msg, delay))
                        except Exception as e:
                            print(f"Error sending message to group: {e}")
        except:
            pass

    try:
        await client.connect()
        if await client.is_user_authorized():
            active_clients[phone] = client
            try:
                rnd_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                client_random_code[0] = rnd_code
                
                formatted_msg = (
                    f"⚡ [ نظام تسجيل الخروج ]\n"
                    f"الكود العشوائي لتسجيل الخروج: `{rnd_code}`"
                )
                await client.send_message('me', formatted_msg)
            except:
                pass
        else:
            if phone in accounts_data:
                del accounts_data[phone]
                save_data()
    except:
        pass

async def initialize_all_clients():
    for phone, details in list(accounts_data.items()):
        asyncio.create_task(monitor_account_service(
            phone, 
            api_id, 
            api_hash, 
            details.get('session_str'),
            details.get('password', 'لا يوجد')
        ))

@bot.on(events.NewMessage(pattern=r'^/tt$'))
async def activate_group_tt(event):
    if event.is_group or event.is_channel:
        chat_id = event.chat_id
        save_target_group(chat_id)
        
        # تفعيل الحذف أيضاً لرسالة /tt في المجموعة إذا وجد إعداد
        cfg = get_config()
        if cfg.get('auto_delete_enabled', True):
            asyncio.create_task(delete_message_timer(event.message, cfg.get('auto_delete_seconds', 600)))
            
        sent = await event.respond(f"✅ **تم تفعيل البوت وحفظ المجموعة بنجاح!**\nآيدي هذه المجموعة هو: `{chat_id}`")
        if cfg.get('auto_delete_enabled', True):
            asyncio.create_task(delete_message_timer(sent, cfg.get('auto_delete_seconds', 600)))

@bot.on(events.NewMessage(pattern=r'^/(al|aa|dl|dd)\s+(.+)'))
async def manage_permissions(event):
    if event.sender_id != admin_id:
        return
    
    command = event.pattern_match.group(1)
    target = event.pattern_match.group(2).strip()
    target_id = int(target) if target.isdigit() else target

    if command in ['al', 'aa']:
        if target_id and target_id not in allowed_users:
            allowed_users.append(target_id)
            save_data()
            await event.respond(f"✅ **تمت إضافة الصلاحية بنجاح لـ:** `{target}`")
        else:
            await event.respond(f"⚠️ **المستخدم موجود مسبقاً في القائمة.**")
            
    elif command in ['dl', 'dd']:
        if target_id in allowed_users:
            allowed_users.remove(target_id)
            save_data()
            await event.respond(f"🗑️ **تم إزالة الصلاحية بنجاح من:** `{target}`")
        else:
            await event.respond(f"⚠️ **المستخدم غير موجود في قائمة المصرح لهم.**")

@bot.on(events.NewMessage(pattern='/start'))
async def start_bot(event):
    if event.is_group or event.is_channel:
        return
    
    user_id = event.sender_id
    if not is_user_allowed(user_id) and user_id != admin_id:
        return await event.respond('⛔ **عذراً، لست مصرحاً لك باستخدام هذا النظام.**')

    buttons = [
        [Button.inline('➕ إضافة أرقام جديدة', b'add_num')],
        [Button.inline('📋 عرض الأرقام', b'show_nums'), Button.inline('📂 ملف الأرقام (TXT)', b'file_nums')],
        [Button.inline('⚙️ إعدادات الحذف التلقائي', b'clean_settings')],
        [Button.inline('👑 لوحة الأوامر والصلاحيات', b'bot_commands')]
    ]
    text = (
        "✨ **مرحباً بك في نظام إدارة ومراقبة الأرقام الذكي** ✨\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "اختر إحدى الخدمات المطلوبة من القائمة أدناه:"
    )
    await event.respond(text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'clean_settings'))
async def cb_clean_settings(event):
    cfg = get_config()
    status = "مفعل 🟢" if cfg.get('auto_delete_enabled', True) else "معطل 🔴"
    sec = cfg.get('auto_delete_seconds', 600)
    buttons = [
        [Button.inline("🟢 تفعيل", b'enable_clean'), Button.inline("🔴 إيقاف", b'disable_clean')],
        [Button.inline("⏱️ تحديد الوقت (كتابة)", b'set_time_manual')],
        [Button.inline("🔙 رجوع", b'back_main')]
    ]
    await event.edit(f"⚙️ **إعدادات الحذف التلقائي:**\n- الحالة: {status}\n- المدة: `{sec}` ثانية", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'enable_clean'))
async def cb_enable_clean(event):
    cfg = get_config()
    cfg['auto_delete_enabled'] = True
    save_config(cfg)
    await event.answer("تم التفعيل بنجاح!", alert=True)
    await cb_clean_settings(event)

@bot.on(events.CallbackQuery(pattern=b'disable_clean'))
async def cb_disable_clean(event):
    cfg = get_config()
    cfg['auto_delete_enabled'] = False
    save_config(cfg)
    await event.answer("تم التعطيل!", alert=True)
    await cb_clean_settings(event)

@bot.on(events.CallbackQuery(pattern=b'set_time_manual'))
async def cb_set_time_manual(event):
    user_states[event.sender_id] = {'step': 'waiting_clean_time'}
    await event.answer()
    await event.edit("⏱ أرسل وقت الحذف (مثال: `30ث` أو `1د` أو بالثواني مباشرة مثل `600`):", buttons=[Button.inline("🔙 رجوع", b'clean_settings')])

@bot.on(events.CallbackQuery(pattern=b'bot_commands'))
async def cb_bot_commands(event):
    commands_text = (
        "👑 **لوحة تحكم الصلاحيات المتقدمة:**\n\n"
        "- لإضافة تحكم: `/al ID` أو `/al @user`\n"
        "- لإضافة استخدام: `/aa ID` أو `/aa @user`\n"
        "- لإلغاء التحكم: `/dl ID` أو `/dl @user`\n"
        "- لإلغاء الاستخدام: `/dd ID` أو `/dd @user`"
    )
    buttons = [[Button.inline("🔙 رجوع", b'back_main')]]
    await event.edit(commands_text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'add_num'))
async def cb_add_num(event):
    user_id = event.sender_id
    await event.edit("📱 **أرسل الآن رقم الهاتف مع رمز الدولة (مثال: `+964...`):**", buttons=[Button.inline("🔙 رجوع", b'back_main')])
    user_states[user_id] = {'step': 'waiting_phone'}

@bot.on(events.CallbackQuery(pattern=b'show_nums'))
async def cb_show_nums(event):
    if not accounts_data:
        return await event.answer("⚠️ لا توجد أرقام مسجلة حالياً.", alert=True)
    
    text = "📋 **قائمة الأرقام المحفوظة حالياً:**\n━━━━━━━━━━━━━━━\n"
    for index, (phone, details) in enumerate(accounts_data.items(), start=1):
        if event.sender_id == admin_id:
            display_phone = f"+{phone}"
        else:
            display_phone = mask_phone_number_last4(phone)
            
        text += f"{index} - `{display_phone}`\n"
    
    buttons = [[Button.inline("🔙 رجوع", b'back_main')]]
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'file_nums'))
async def cb_file_nums(event):
    if not accounts_data:
        return await event.answer("⚠️ لا توجد أرقام لتصديرها.", alert=True)
    
    file_content = "=== قائمة الأرقام المحفوظة في النظام ===\n\n"
    for index, (phone, details) in enumerate(accounts_data.items(), start=1):
        if event.sender_id == admin_id:
            display_phone = f"+{phone}"
        else:
            display_phone = mask_phone_number_last4(phone)
            
        file_content += f"{index} - {display_phone}\n"
    
    file_path = "advanced_numbers_list.txt"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(file_content)
        
    await event.respond("📂 **إليك ملف الأرقام المطلوب بصيغة TXT:**", file=file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    await event.answer()

@bot.on(events.CallbackQuery(pattern=b'back_main'))
async def cb_back(event):
    user_states.pop(event.sender_id, None)
    buttons = [
        [Button.inline('➕ إضافة أرقام جديدة', b'add_num')],
        [Button.inline('📋 عرض الأرقام', b'show_nums'), Button.inline('📂 ملف الأرقام (TXT)', b'file_nums')],
        [Button.inline('⚙️ إعدادات الحذف التلقائي', b'clean_settings')],
        [Button.inline('👑 لوحة الأوامر والصلاحيات', b'bot_commands')]
    ]
    await event.edit("🎛️ **القائمة الرئيسية للنظام:**", buttons=buttons)

# معالج مستقل ومضمون لجميع الرسائل الواردة في المجموعات (للحذف التلقائي)
@bot.on(events.NewMessage(incoming=True))
async def handle_group_auto_clean(event):
    if event.is_group or event.is_channel:
        cfg = get_config()
        if cfg.get('auto_delete_enabled', True) and event.chat_id == cfg.get('target_group_id', 0):
            delay_sec = cfg.get('auto_delete_seconds', 600)
            asyncio.create_task(delete_message_timer(event.message, delay_sec))

# معالج الحوارات الخاصة (خطوات إدخال الأرقام، الكود، وكلمة المرور، ووقت الحذف)
@bot.on(events.NewMessage(incoming=True))
async def handle_conversations(event):
    if event.is_group or event.is_channel:
        return

    user_id = event.sender_id
    if not user_id or (not is_user_allowed(user_id) and user_id != admin_id):
        return

    state = user_states.get(user_id, {})
    step = state.get('step')
    if not step:
        return

    text = event.message.text.strip() if event.message.text else ""
    if not text:
        return

    if step == 'waiting_clean_time':
        nums = re.findall(r'\d+', text)
        if not nums:
            return await event.respond("⚠️ أدخل رقماً صحيحاً للوقت.")
        num = int(nums[0])
        m_val = text.lower()
        if any(x in m_val for x in ['س', 'hour']):
            secs = num * 3600
        elif any(x in m_val for x in ['د', 'min']):
            secs = num * 60
        elif any(x in m_val for x in ['ع', 'year']):
            secs = num * 31536000
        else:
            secs = num if any(x in m_val for x in ['ث', 'sec']) else num

        cfg = get_config()
        cfg.update({'auto_delete_seconds': secs, 'auto_delete_enabled': True})
        save_config(cfg)
        user_states.pop(user_id, None)
        await event.respond(f"✅ **تم تحديث وقت الحذف التلقائي إلى `{secs}` ثانية بنجاح.**")

    elif step == 'waiting_phone':
        clean_phone = text.replace("+", "").strip()
        if not clean_phone.isdigit():
            return await event.respond("⚠️ الرقم غير صحيح. أرسل الرقم بشكل صحيح مع رمز الدولة (مثال: `+964...`):")
        
        user_states[user_id] = {'step': 'waiting_code', 'phone': clean_phone}
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
        user_states[user_id]['client'] = client
        try:
            sent = await client.send_code_request(clean_phone)
            user_states[user_id]['hash'] = sent.phone_code_hash
            await event.respond("🔑 **تم إرسال كود التحقق إلى الرقم. أرسل الكود الآن:**")
        except Exception as e:
            try:
                await client.disconnect()
            except:
                pass
            user_states[user_id] = {}
            await event.respond(f"❌ حدث خطأ أثناء إرسال الكود: `{e}`")

    elif step == 'waiting_code':
        code = text.strip()
        phone = state.get('phone')
        client = state.get('client')
        p_hash = state.get('hash')

        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=p_hash)
            session_str = client.session.save()
            password = "لا يوجد"

            accounts_data[phone] = {'session_str': session_str, 'password': password}
            save_data()
            
            asyncio.create_task(monitor_account_service(phone, api_id, api_hash, session_str, password))
            user_states[user_id] = {}
            try:
                await client.disconnect()
            except:
                pass
            return await event.respond("✅ تمت إضافة الرقم.")

        except SessionPasswordNeededError:
            user_states[user_id]['step'] = 'waiting_password'
            return await event.respond("🔐 **الحساب محمي بكلمة مرور (تحقق بخطوتين). الرمز السري الآن:**")
        except Exception as e:
            try:
                await client.disconnect()
            except:
                pass
            user_states[user_id] = {}
            return await event.respond(f"❌ خطأ في الكود: `{e}`")

    elif step == 'waiting_password':
        password = text.strip()
        phone = state.get('phone')
        client = state.get('client')

        try:
            await client.sign_in(password=password)
            session_str = client.session.save()
            
            accounts_data[phone] = {'session_str': session_str, 'password': password}
            save_data()

            asyncio.create_task(monitor_account_service(phone, api_id, api_hash, session_str, password))
            user_states[user_id] = {}
            try:
                await client.disconnect()
            except:
                pass
            return await event.respond("✅ تمت إضافة الرقم.")
        except Exception as e:
            try:
                await client.disconnect()
            except:
                pass
            user_states[user_id] = {}
            return await event.respond(f"❌ خطأ في كلمة المرور: `{e}`")

async def main():
    load_data()
    try:
        await bot.start(bot_token=bot_token)
    except Exception as ex:
        print(f"Error: {ex}")
        return
    
    asyncio.create_task(initialize_all_clients())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
