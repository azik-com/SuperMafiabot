# 🎭 Mafia Bot — O'zbek tilidagi Telegram Mafia O'yini

## 📁 Fayllar tuzilmasi

```
mafia_bot/
├── bot.py        ← Ishga tushirish
├── config.py     ← Token va sozlamalar
├── handlers.py   ← Telegram handlerlari
├── game.py       ← O'yin logikasi
├── roles.py      ← Rol taqsimoti
└── texts.py      ← O'zbek tilidagi matnlar
```

## ⚙️ O'rnatish

```bash
pip install python-telegram-bot
```

## 🚀 Ishga tushirish

1. `config.py` faylida `BOT_TOKEN` ni o'z tokeningiz bilan almashtiring
2. Botni @BotFather dan yarating va Privacy Mode ni **o'chiring**
3. Ishga tushiring:

```bash
python bot.py
```

## 🎮 O'yin qoidalari

### Buyruqlar:
| Buyruq | Tavsif |
|--------|--------|
| `/newgame` | Yangi o'yin yaratish (guruhda) |
| `/join` | O'yinga qo'shilish |
| `/start_game` | O'yinni boshlash (admin) |
| `/cancel_game` | O'yinni bekor qilish (admin) |
| `/players` | O'yinchilar ro'yxati |

### Rollar:
| Rol | Fraksiya | Kecha harakati |
|-----|----------|----------------|
| 👤 Tinch aholi | Tinch | — |
| 🔴 Mafia | Mafia | O'ldiradi |
| 👑 Don | Mafia | O'ldiradi (Sherif "tinch" ko'radi) |
| 👮 Sherif | Tinch | Tekshiradi (mafia/tinch) |
| 👨‍⚕️ Doktor | Tinch | Davolaydi |
| 🕵️ Detektiv | Tinch | Aniq rolni biladi |
| 💘 Sevgilisi | Tinch | — (sevgilisi o'lsa, u ham o'ladi) |
| 🔪 Maniac | Yolg'iz | O'ldiradi (hamma dushman) |
| 💣 Terrorchi | Tinch | — (o'ldirilsa, qotil ham o'ladi) |

### O'yinchi soni bo'yicha rollar:
| O'yinchilar | Mafia | Don | Sherif | Doktor | Detektiv | Sevgilisi | Maniac | Terrorchi |
|-------------|-------|-----|--------|--------|----------|-----------|--------|-----------|
| 4 | 1 | — | 1 | — | — | — | — | — |
| 5 | 1 | — | 1 | 1 | — | — | — | — |
| 6 | 1 | — | 1 | 1 | — | 1 | — | — |
| 7 | 1 | 1 | 1 | 1 | — | 1 | — | — |
| 8 | 1 | 1 | 1 | 1 | 1 | 1 | — | — |
| 9 | 2 | 1 | 1 | 1 | — | 1 | — | 1 |
| 10 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | — |
| 11+ | 2+ | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

## 📝 Eslatmalar

- Bot guruhga qo'shilganda Privacy Mode **o'chiq** bo'lishi kerak
- Har bir o'yinchi botga avval `/start` yuborganda bo'lishi kerak (shaxsiy xabar uchun)
- Kecha harakatlari shaxsiy chatda bajariladi
