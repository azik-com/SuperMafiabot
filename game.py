# =============================================
#  MAFIA BOT — O'yin holati va logikasi
# =============================================
import random
from dataclasses import dataclass, field
from typing import Optional
from roles import build_roles_list, role_info, is_mafia, is_town, is_maniac


@dataclass
class Player:
    user_id: int
    name: str
    username: Optional[str]
    role: str = ""
    alive: bool = True
    lover_id: Optional[int] = None          # Sevgilisi o'yinchisi
    night_action: Optional[int] = None       # Kechasi tanlagan o'yinchi ID
    day_vote: Optional[int] = None           # Kunduz ovozi

    def mention(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.name

    def role_display(self) -> str:
        info = role_info(self.role)
        return f"{info['emoji']} {info['nom']}"


class Game:
    MIN_PLAYERS = 4
    MAX_PLAYERS = 15
    NIGHT_TIMEOUT = 45    # soniya
    DAY_TIMEOUT = 90      # soniya

    def __init__(self, chat_id: int, admin_id: int):
        self.chat_id = chat_id
        self.admin_id = admin_id
        self.players: dict[int, Player] = {}  # user_id → Player
        self.phase = "lobby"      # lobby | night | day | ended
        self.round = 0
        self.winner: Optional[str] = None     # town | mafia | maniac | nobody
        self.night_log: list[str] = []        # Kecha voqealari (xabar uchun)
        self.start_time: Optional[float] = None

    # ── Lobby ──────────────────────────────────
    def add_player(self, user_id: int, name: str, username: Optional[str]) -> bool:
        if user_id in self.players:
            return False
        if len(self.players) >= self.MAX_PLAYERS:
            return False
        self.players[user_id] = Player(user_id, name, username)
        return True

    def player_count(self) -> int:
        return len(self.players)

    def alive_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.alive]

    def alive_count(self) -> int:
        return sum(1 for p in self.players.values() if p.alive)

    def get_player(self, uid: int) -> Optional[Player]:
        return self.players.get(uid)

    # ── Rollar taqsimoti ───────────────────────
    def assign_roles(self):
        import time
        self.start_time = time.time()
        uids = list(self.players.keys())
        roles = build_roles_list(len(uids))
        random.shuffle(roles)
        random.shuffle(uids)
        for uid, role in zip(uids, roles):
            self.players[uid].role = role

        # Sevgilisi juftini tanlash
        sevgililar = [p for p in self.players.values() if p.role == "sevgilisi"]
        if sevgililar:
            others = [p for p in self.players.values() if p.user_id != sevgililar[0].user_id]
            if others:
                partner = random.choice(others)
                sevgililar[0].lover_id = partner.user_id
                partner.lover_id = sevgililar[0].user_id  # ikki tomonlama

    # ── Kecha ─────────────────────────────────
    def start_night(self):
        self.phase = "night"
        self.round += 1
        # Kecha ovozlarini tozalash
        for p in self.players.values():
            p.night_action = None
        self.night_log = []

    def set_night_action(self, actor_id: int, target_id: int) -> bool:
        actor = self.players.get(actor_id)
        target = self.players.get(target_id)
        if not actor or not actor.alive:
            return False
        if not target or not target.alive:
            return False
        actor.night_action = target_id
        return True

    def mafia_night_actions_done(self) -> bool:
        """Barcha mafia ovoz berdimi?"""
        mafia = [p for p in self.alive_players() if p.role in {"mafia", "don"}]
        return all(p.night_action is not None for p in mafia)

    def process_night(self) -> list[str]:
        """
        Kecha natijalarini hisoblaydi.
        Qaytaradi: voqealar ro'yxati (guruhga yuborish uchun matnlar)
        """
        events = []
        alive = {p.user_id: p for p in self.alive_players()}

        # 1. Doktor tanlovi
        healed_id = None
        for p in self.alive_players():
            if p.role == "doktor" and p.night_action:
                healed_id = p.night_action

        # 2. Mafia tanlovi (ko'pchilik ovoz)
        mafia_votes: dict[int, int] = {}
        for p in self.alive_players():
            if p.role in {"mafia", "don"} and p.night_action:
                mafia_votes[p.night_action] = mafia_votes.get(p.night_action, 0) + 1
        mafia_target_id = max(mafia_votes, key=mafia_votes.get) if mafia_votes else None

        # 3. Maniac tanlovi
        maniac_target_id = None
        for p in self.alive_players():
            if p.role == "maniac" and p.night_action:
                maniac_target_id = p.night_action

        to_kill: set[int] = set()
        killer_of: dict[int, int] = {}  # killed_id → killer_id (terrorchi uchun)

        if mafia_target_id and mafia_target_id != healed_id:
            to_kill.add(mafia_target_id)
            # Terrorchi: mafiadan birinchisi killer
            mafia_members = [p.user_id for p in self.alive_players() if p.role in {"mafia", "don"}]
            if mafia_members:
                killer_of[mafia_target_id] = mafia_members[0]

        if maniac_target_id and maniac_target_id != healed_id:
            to_kill.add(maniac_target_id)
            maniac_p = next((p for p in self.alive_players() if p.role == "maniac"), None)
            if maniac_p:
                killer_of[maniac_target_id] = maniac_p.user_id

        # 4. O'ldirishni amalga oshirish
        actually_dead: list[Player] = []
        for uid in list(to_kill):
            victim = alive.get(uid)
            if not victim:
                continue
            # Terrorchi effekti
            if victim.role == "terrorchi":
                killer_id = killer_of.get(uid)
                if killer_id and killer_id in alive:
                    killer = alive[killer_id]
                    killer.alive = False
                    actually_dead.append(killer)
                    events.append(f"💥 {victim.mention()} Terrorchi edi! Portlash natijasida {killer.mention()} ham halok bo'ldi!")
            victim.alive = False
            actually_dead.append(victim)

        if not actually_dead:
            if healed_id and (mafia_target_id or maniac_target_id):
                events.append("✨ Kechasi hujum bo'ldi, lekin doktor qutqardi!")
            else:
                events.append("😴 Kechasi hech kim o'lmadi.")
        else:
            for p in actually_dead:
                if p.role != "terrorchi":  # terrorchi alohida yozildi
                    events.append(f"💀 {p.mention()} ({p.role_display()}) o'ldirildi!")

        # 5. Sevgilisi effekti
        for dead in list(actually_dead):
            if dead.lover_id and dead.lover_id in alive:
                lover = alive[dead.lover_id]
                if lover.alive:
                    lover.alive = False
                    events.append(f"💔 {lover.mention()} sevgilisiz yasha olmasdi... u ham o'tib ketdi.")
                    actually_dead.append(lover)

        self.night_log = events
        return events

    # ── Kunduz ─────────────────────────────────
    def start_day(self):
        self.phase = "day"
        for p in self.players.values():
            p.day_vote = None

    def set_day_vote(self, voter_id: int, target_id: Optional[int]) -> bool:
        voter = self.players.get(voter_id)
        if not voter or not voter.alive:
            return False
        voter.day_vote = target_id  # None = skip
        return True

    def all_voted_day(self) -> bool:
        return all(
            p.day_vote is not None
            for p in self.alive_players()
        )

    def process_day_vote(self) -> dict:
        """
        Kunduz ovoz berish natijasini hisoblaydi.
        Qaytaradi: {"type": "exile"/"tie"/"skip", "player": Player|None, "votes": int}
        """
        tally: dict[int, int] = {}
        skip_votes = 0
        for p in self.alive_players():
            if p.day_vote is None or p.day_vote == -1:
                skip_votes += 1
            else:
                tally[p.day_vote] = tally.get(p.day_vote, 0) + 1

        if not tally:
            return {"type": "skip", "player": None, "votes": skip_votes}

        max_votes = max(tally.values())
        top = [uid for uid, v in tally.items() if v == max_votes]

        if len(top) > 1:
            return {"type": "tie", "player": None, "votes": max_votes}

        exiled_id = top[0]
        exiled = self.players.get(exiled_id)
        if exiled:
            exiled.alive = False
            # Terrorchi: kim ovoz berganini topish
            if exiled.role == "terrorchi":
                # eng ko'p ovoz bergan
                pass  # kunduz ovozida terrorchi effekti yo'q (faqat kechasi)
            # Sevgilisi effekti
            events = []
            if exiled.lover_id:
                lover = self.players.get(exiled.lover_id)
                if lover and lover.alive:
                    lover.alive = False
                    events.append(lover)
        return {"type": "exile", "player": exiled, "votes": max_votes, "lover_died": events if exiled else []}

    # ── G'olib tekshiruvi ──────────────────────
    def check_winner(self) -> Optional[str]:
        alive = self.alive_players()
        if not alive:
            self.winner = "nobody"
            return "nobody"

        alive_mafia = [p for p in alive if p.role in {"mafia", "don"}]
        alive_town = [p for p in alive if is_town(p.role)]
        alive_maniac = [p for p in alive if is_maniac(p.role)]

        # Maniac yolg'iz qolganda yutadi
        if alive_maniac and len(alive) == 1:
            self.winner = "maniac"
            return "maniac"

        # Mafia yo'q → shahar yutadi
        if not alive_mafia:
            # Lekin maniac ham yo'q bo'lishi kerak
            if not alive_maniac:
                self.winner = "town"
                return "town"

        # Mafia soni tinch + maniac dan kam bo'lmasa → mafia yutadi
        non_mafia = len(alive) - len(alive_mafia)
        if len(alive_mafia) >= non_mafia:
            self.winner = "mafia"
            return "mafia"

        return None

    # ── Yordamchi ─────────────────────────────
    def players_list_text(self) -> str:
        lines = []
        for i, p in enumerate(self.players.values(), 1):
            status = "💀" if not p.alive else "✅"
            lines.append(f"{status} {i}. {p.mention()}")
        return "\n".join(lines)

    def alive_list_text(self) -> str:
        lines = []
        for i, p in enumerate(self.alive_players(), 1):
            lines.append(f"🔵 {i}. {p.mention()}")
        return "\n".join(lines)

    def final_roles_text(self) -> str:
        lines = []
        for p in self.players.values():
            status = "💀" if not p.alive else "✅"
            lines.append(f"{status} {p.mention()} — {p.role_display()}")
        return "\n".join(lines)
