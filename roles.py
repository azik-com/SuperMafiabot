# =============================================
#  MAFIA BOT — Rol logikasi
# =============================================
from texts import ROLES

# O'yinchi soniga qarab rollar taqsimoti
ROLE_DISTRIBUTION = {
    4:  {"mafia": 1, "sherif": 1, "doktor": 0, "don": 0, "detektiv": 0, "sevgilisi": 0, "maniac": 0, "terrorchi": 0},
    5:  {"mafia": 1, "sherif": 1, "doktor": 1, "don": 0, "detektiv": 0, "sevgilisi": 0, "maniac": 0, "terrorchi": 0},
    6:  {"mafia": 1, "sherif": 1, "doktor": 1, "don": 0, "detektiv": 0, "sevgilisi": 1, "maniac": 0, "terrorchi": 0},
    7:  {"mafia": 1, "sherif": 1, "doktor": 1, "don": 1, "detektiv": 0, "sevgilisi": 1, "maniac": 0, "terrorchi": 0},
    8:  {"mafia": 1, "sherif": 1, "doktor": 1, "don": 1, "detektiv": 1, "sevgilisi": 1, "maniac": 0, "terrorchi": 0},
    9:  {"mafia": 2, "sherif": 1, "doktor": 1, "don": 1, "detektiv": 0, "sevgilisi": 1, "maniac": 0, "terrorchi": 1},
    10: {"mafia": 2, "sherif": 1, "doktor": 1, "don": 1, "detektiv": 1, "sevgilisi": 1, "maniac": 1, "terrorchi": 0},
    11: {"mafia": 2, "sherif": 1, "doktor": 1, "don": 1, "detektiv": 1, "sevgilisi": 1, "maniac": 1, "terrorchi": 1},
    12: {"mafia": 3, "sherif": 1, "doktor": 1, "don": 1, "detektiv": 1, "sevgilisi": 1, "maniac": 1, "terrorchi": 0},
    15: {"mafia": 3, "sherif": 1, "doktor": 2, "don": 1, "detektiv": 1, "sevgilisi": 1, "maniac": 1, "terrorchi": 1},
}

def get_role_distribution(player_count: int) -> dict:
    """O'yinchi soniga mos rollar taqsimotini qaytaradi."""
    best = max((k for k in ROLE_DISTRIBUTION if k <= player_count), default=4)
    dist = dict(ROLE_DISTRIBUTION[best])
    # Qolgan o'yinchilar tinch aholi bo'ladi
    special_count = sum(dist.values())
    dist["tinch"] = player_count - special_count
    return dist

def build_roles_list(player_count: int) -> list[str]:
    """Rollar ro'yxatini (str) qaytaradi, aralashtirish uchun."""
    dist = get_role_distribution(player_count)
    roles = []
    for role, count in dist.items():
        roles.extend([role] * count)
    return roles

def role_info(role_key: str) -> dict:
    """Rol ma'lumotlarini qaytaradi."""
    return ROLES.get(role_key, {"nom": "Noma'lum", "emoji": "❓", "fraksiya": "tinch"})

def is_mafia(role_key: str) -> bool:
    return ROLES.get(role_key, {}).get("fraksiya") == "mafia"

def is_town(role_key: str) -> bool:
    return ROLES.get(role_key, {}).get("fraksiya") == "tinch"

def is_maniac(role_key: str) -> bool:
    return role_key == "maniac"

def can_act_at_night(role_key: str) -> bool:
    """Kecha harakat qila oladigan rollar."""
    return role_key in {"mafia", "don", "sherif", "doktor", "detektiv", "maniac"}

def get_sheriff_result(role_key: str) -> str:
    """Sherif tekshiruvi natijasi."""
    if role_key in {"mafia"}:
        return "mafia"
    # Don "tinch" ko'rinadi
    return "tinch"

def get_detective_result(role_key: str) -> str:
    """Detektiv tekshiruvi — aniq rol nomini qaytaradi."""
    return role_key
