# =================================
# دانشجو: مبینا نظری
# شماره دانشجویی: 404131283
# عنوان پروژه: شبیه‌ساز جام جهانی
# تاریخ تحویل : 1405/04/27
# =================================
"""
شبیه‌ساز شیءگرای جام جهانی ۲۰۲۶ (۳۲ تیم).

کتابخانه‌های استفاده شده:
- random, csv, os, math, collections: کتابخانه استاندارد
- matplotlib (اختیاری): نمودار درصد قهرمانی — نمره اضافه
"""

from __future__ import annotations

import csv
import math
import os
import random
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

# matplotlib اختیاری (نمره اضافه)
try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# حداکثر دور sudden death برای جلوگیری از حلقه بی‌نهایت (اصلاح استاد)
SUDDEN_DEATH_MAX_ROUNDS = 50
DEFAULT_CSV = "teams_2026_worldcup.csv"
FALLBACK_CSV = "worldcup_2026_teams.txt"


# ---------------------------------------------------------------------------
# خروجی رنگی (خلاقیت / زیباسازی)
# ---------------------------------------------------------------------------
class Colors:
    """کدهای ANSI برای رنگی‌سازی کنسول."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"

    @staticmethod
    def wrap(text: str, color: str) -> str:
        return f"{color}{text}{Colors.RESET}"


def poisson_sample(lam: float) -> int:
    """نمونه‌گیری از توزیع پواسون (الگوریتم Knuth) بدون NumPy."""
    if lam <= 0:
        return 0
    # جلوگیری از underflow برای lambda بزرگ
    if lam > 100:
        # تقریب نرمال برای lambda خیلی بزرگ (در این پروژه معمولاً رخ نمی‌دهد)
        return max(0, int(round(random.gauss(lam, math.sqrt(lam)))))
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------
class Team:
    """کلاس تیم ملی فوتبال."""

    def __init__(self, name: str, attack: float, defense: float, rank: int) -> None:
        """
        Args:
            name: نام تیم
            attack: قدرت حمله (۱ تا ۱۰۰)
            defense: قدرت دفاع (۱ تا ۱۰۰)
            rank: رتبه فیفا (۱ بهترین)
        """
        self.name = name
        self.attack = float(attack)
        self.defense = float(defense)
        self.rank = int(rank)
        self.for_goals = 0
        self.against_goals = 0
        self.points = 0
        self.group: Optional[str] = None

    def goal_difference(self) -> int:
        """محاسبه تفاضل گل (گل زده − گل خورده)."""
        return self.for_goals - self.against_goals

    def reset_stats(self) -> None:
        """صفر کردن آمار مرحله (گل زده، گل خورده، امتیاز)."""
        self.for_goals = 0
        self.against_goals = 0
        self.points = 0

    def _lambda_against(self, opponent: "Team") -> float:
        """محاسبه lambda برای گل‌های این تیم در برابر حریف (۹۰ دقیقه)."""
        return (self.attack / 100.0) * 1.5 + (1.0 - opponent.defense / 100.0) * 0.8

    def penalty_success_prob(self, opponent: "Team") -> float:
        """احتمال گل شدن پنالتی این تیم در برابر دفاع حریف."""
        p = 0.75 + (self.attack - opponent.defense) / 250.0
        return max(0.6, min(0.9, p))

    def simulate_match(
        self, opponent: "Team", is_knockout: bool = False
    ) -> Tuple[int, int, Optional["Team"]]:
        """
        شبیه‌سازی نتیجه بازی با تیم حریف.

        Args:
            opponent (Team): تیم حریف
            is_knockout (bool): آیا مرحله حذفی است؟

        Returns:
            tuple: (گل_تیم_خودی، گل_تیم_حریف، برنده مسابقه)
        """
        match = Match(self, opponent, is_knockout=is_knockout)
        match.play()
        return match.goals1, match.goals2, match.winner

    def __repr__(self) -> str:
        return f"Team({self.name!r}, rank={self.rank})"


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------
class Match:
    """کلاس یک مسابقه بین دو تیم."""

    def __init__(self, team1: Team, team2: Team, is_knockout: bool = False) -> None:
        """
        Args:
            team1: تیم اول
            team2: تیم دوم
            is_knockout: مسابقه حذفی (وقت اضافه / پنالتی در صورت تساوی)
        """
        self.team1 = team1
        self.team2 = team2
        self.goals1 = 0
        self.goals2 = 0
        self.is_knockout = is_knockout
        self.winner: Optional[Team] = None
        # جزئیات نمایش
        self.extra_time = False
        self.penalties = False
        self.pen_score1 = 0
        self.pen_score2 = 0

    def play(self) -> None:
        """
        انجام مسابقه، محاسبه نتیجه، به‌روزرسانی آمار تیم‌ها و تعیین برنده.

        - گروهی: تساوی مجاز است؛ امتیاز به‌روز می‌شود.
        - حذفی: در صورت تساوی، وقت اضافه و در صورت نیاز پنالتی.
        - گل پنالتی جزو گل‌های بازی نیست.
        """
        # ---- ۹۰ دقیقه ----
        lam1 = self.team1._lambda_against(self.team2)
        lam2 = self.team2._lambda_against(self.team1)
        self.goals1 = poisson_sample(lam1)
        self.goals2 = poisson_sample(lam2)

        # ---- وقت اضافه (فقط حذفی) ----
        if self.is_knockout and self.goals1 == self.goals2:
            self.extra_time = True
            et1 = poisson_sample(0.33 * lam1)
            et2 = poisson_sample(0.33 * lam2)
            self.goals1 += et1
            self.goals2 += et2

        # ---- پنالتی (فقط حذفی پس از وقت اضافه) ----
        if self.is_knockout and self.goals1 == self.goals2:
            self.penalties = True
            self.pen_score1, self.pen_score2 = self._penalty_shootout()

        # ---- برنده ----
        if self.goals1 > self.goals2:
            self.winner = self.team1
        elif self.goals2 > self.goals1:
            self.winner = self.team2
        elif self.penalties:
            self.winner = self.team1 if self.pen_score1 > self.pen_score2 else self.team2
        else:
            self.winner = None  # تساوی گروهی

        # ---- به‌روزرسانی آمار ----
        self.team1.for_goals += self.goals1
        self.team1.against_goals += self.goals2
        self.team2.for_goals += self.goals2
        self.team2.against_goals += self.goals1

        if not self.is_knockout:
            if self.goals1 > self.goals2:
                self.team1.points += 3
            elif self.goals2 > self.goals1:
                self.team2.points += 3
            else:
                self.team1.points += 1
                self.team2.points += 1

    def _penalty_shootout(self) -> Tuple[int, int]:
        """
        اجرای پنالتی: ۵ ضربه اولیه + sudden death.

        Returns:
            (امتیاز پنالتی team1, امتیاز پنالتی team2)
        """
        p1 = self.team1.penalty_success_prob(self.team2)
        p2 = self.team2.penalty_success_prob(self.team1)
        s1 = s2 = 0

        # ۵ ضربه اولیه — با early-stop منطقی (اختیاری ولی خوانا)
        for i in range(5):
            if random.random() < p1:
                s1 += 1
            if random.random() < p2:
                s2 += 1
            # اگر یکی دیگر نتواند جبران کند
            remaining = 4 - i
            if s1 > s2 + remaining or s2 > s1 + remaining:
                break

        # sudden death
        if s1 == s2:
            for _ in range(SUDDEN_DEATH_MAX_ROUNDS):
                r1 = 1 if random.random() < p1 else 0
                r2 = 1 if random.random() < p2 else 0
                s1 += r1
                s2 += r2
                if r1 != r2:
                    break
            else:
                # fallback بسیار نادر: برنده تصادفی با یک گل مجازی
                if random.random() < 0.5:
                    s1 += 1
                else:
                    s2 += 1

        return s1, s2

    def result_str(self) -> str:
        """رشته نتیجه برای نمایش براکت/جدول."""
        if self.penalties:
            return (
                f"{self.team1.name} {self.goals1}-{self.goals2} "
                f"({self.pen_score1}-{self.pen_score2} pens) {self.team2.name}"
            )
        return f"{self.team1.name} {self.goals1}-{self.goals2} {self.team2.name}"

    def display_line(self) -> str:
        """خط نمایش با برنده (قالب PDF)."""
        if self.winner is None:
            return f"{self.result_str()} -> تساوی"
        return f"{self.result_str()} -> برنده: {self.winner.name}"


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------
class Group:
    """کلاس گروه مرحله گروهی (۴ تیم، ۶ مسابقه)."""

    def __init__(self, name: str, teams: List[Team]) -> None:
        """
        Args:
            name: نام گروه (A, B, ...)
            teams: فهرست چهار تیم
        """
        self.name = name
        self.teams = list(teams)
        self.matches: List[Match] = []
        # نتایج رو در رو برای head-to-head (bonus)
        # key: (name_a, name_b) مرتب‌شده -> (pts_a, pts_b) از دید name_a,name_b الفبایی
        self._h2h_points: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    def matches_all_play(self) -> None:
        """برگزاری همه مسابقات گروه (هر تیم یک‌بار با سه تیم دیگر)."""
        self.matches.clear()
        self._h2h_points.clear()
        n = len(self.teams)
        for i in range(n):
            for j in range(i + 1, n):
                m = Match(self.teams[i], self.teams[j], is_knockout=False)
                m.play()
                self.matches.append(m)
                self._record_h2h(m)

    def _record_h2h(self, match: Match) -> None:
        """ثبت امتیاز بازی مستقیم برای رتبه‌بندی head-to-head."""
        a, b = match.team1.name, match.team2.name
        key = tuple(sorted((a, b)))
        if match.goals1 > match.goals2:
            self._h2h_points[key][a] += 3
            self._h2h_points[key][b] += 0
        elif match.goals2 > match.goals1:
            self._h2h_points[key][b] += 3
            self._h2h_points[key][a] += 0
        else:
            self._h2h_points[key][a] += 1
            self._h2h_points[key][b] += 1

    def _h2h_score(self, team: Team, peers: List[Team]) -> int:
        """جمع امتیاز بازی مستقیم تیم در برابر هم‌رتبه‌ها (peers)."""
        total = 0
        for other in peers:
            if other.name == team.name:
                continue
            key = tuple(sorted((team.name, other.name)))
            total += self._h2h_points.get(key, {}).get(team.name, 0)
        return total

    def ranking_get(self) -> List[Team]:
        """
        رتبه‌بندی تیم‌های گروه.

        ترتیب:
            1. امتیاز بیشتر
            2. تفاضل گل بیشتر
            3. گل زده بیشتر
            4. head-to-head (bonus)
            5. قرعه‌کشی تصادفی
        """
        # shuffle اولیه برای شکستن تساوی تصادفی پایدار در یک فراخوانی
        teams = list(self.teams)
        random.shuffle(teams)

        # مرتب‌سازی چندمرحله‌ای با در نظر گرفتن h2h بین تیم‌های هم‌امتیاز
        # ابتدا بر اساس معیارهای اصلی
        teams.sort(
            key=lambda t: (t.points, t.goal_difference(), t.for_goals),
            reverse=True,
        )

        # اعمال head-to-head داخل بلوک‌های هم‌امتیاز / هم‌GD / هم‌GF
        i = 0
        ranked: List[Team] = []
        while i < len(teams):
            j = i + 1
            while j < len(teams) and (
                teams[j].points == teams[i].points
                and teams[j].goal_difference() == teams[i].goal_difference()
                and teams[j].for_goals == teams[i].for_goals
            ):
                j += 1
            block = teams[i:j]
            if len(block) > 1:
                block.sort(
                    key=lambda t: (
                        self._h2h_score(t, block),
                        random.random(),
                    ),
                    reverse=True,
                )
            ranked.extend(block)
            i = j
        return ranked

    def advance_teams(self) -> List[Team]:
        """برگرداندن دو تیم اول گروه."""
        return self.ranking_get()[:2]

    def display_table(self) -> None:
        """نمایش جدول گروه مطابق قالب PDF."""
        print(f"===== Group {self.name} =====")
        for idx, t in enumerate(self.ranking_get(), start=1):
            gd = t.goal_difference()
            gd_str = f"+{gd}" if gd > 0 else str(gd)
            print(
                f"{idx}. {t.name}: {t.points} pts, GD {gd_str}, GF {t.for_goals}"
            )


# ---------------------------------------------------------------------------
# KnockoutStage
# ---------------------------------------------------------------------------
class KnockoutStage:
    """یک مرحله حذفی (یک‌هشتم، یک‌چهارم، نیمه‌نهایی، فینال)."""

    def __init__(self, round_name: str, matches: Optional[List[Match]] = None) -> None:
        """
        Args:
            round_name: نام مرحله
            matches: فهرست مسابقات
        """
        self.round_name = round_name
        self.matches: List[Match] = list(matches) if matches else []

    def round_play(self) -> None:
        """اجرای تمام مسابقات این مرحله."""
        for m in self.matches:
            m.play()

    def winners_get(self) -> List[Team]:
        """استخراج فهرست برندگان به ترتیب مسابقات."""
        winners: List[Team] = []
        for m in self.matches:
            if m.winner is None:
                # نباید در حذفی رخ دهد؛ fallback
                winners.append(m.team1 if random.random() < 0.5 else m.team2)
            else:
                winners.append(m.winner)
        return winners

    def results_display(self) -> None:
        """نمایش خلاصه نتایج مرحله."""
        print(f"===== {self.round_name} =====")
        for m in self.matches:
            print(m.display_line())


# ---------------------------------------------------------------------------
# WorldCupSimulator
# ---------------------------------------------------------------------------
class WorldCupSimulator:
    """شبیه‌ساز کامل جام جهانی: بارگذاری، قرعه، گروهی، حذفی، آمار."""

    GROUP_NAMES = list("ABCDEFGH")

    def __init__(self) -> None:
        self.teams: List[Team] = []
        self.groups: List[Group] = []
        self.round_of_16: Optional[KnockoutStage] = None
        self.quarterfinals: Optional[KnockoutStage] = None
        self.semifinals: Optional[KnockoutStage] = None
        self.final: Optional[KnockoutStage] = None
        self.champion: Optional[Team] = None
        self._drawn = False
        self._group_played = False
        self._last_bracket_ready = False

    # ---- بارگذاری ----
    def load_teams_from_csv(self, filename: str) -> bool:
        """
        بارگذاری ۳۲ تیم از فایل CSV.

        Args:
            filename: مسیر فایل CSV با ستون‌های name,attack,defense,rank

        Returns:
            True در صورت موفقیت
        """
        if not os.path.isfile(filename):
            # تلاش برای نام جایگزین (فایل فعلی پروژه)
            if filename == DEFAULT_CSV and os.path.isfile(FALLBACK_CSV):
                filename = FALLBACK_CSV
            else:
                print(
                    Colors.wrap(
                        f"خطا: فایل «{filename}» یافت نشد.",
                        Colors.RED,
                    )
                )
                return False

        loaded: List[Team] = []
        try:
            with open(filename, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                required = {"name", "attack", "defense", "rank"}
                if not reader.fieldnames or not required.issubset(
                    {h.strip().lower() for h in reader.fieldnames}
                ):
                    # پشتیبانی از هدر با حروف بزرگ/کوچک
                    pass
                # نرمال‌سازی کلیدها
                for row in reader:
                    # map keys case-insensitive
                    norm = {k.strip().lower(): (v.strip() if isinstance(v, str) else v)
                            for k, v in row.items() if k}
                    if not norm.get("name"):
                        continue
                    loaded.append(
                        Team(
                            name=norm["name"],
                            attack=float(norm["attack"]),
                            defense=float(norm["defense"]),
                            rank=int(float(norm["rank"])),
                        )
                    )
        except (OSError, ValueError, KeyError, csv.Error) as exc:
            print(Colors.wrap(f"خطا در خواندن CSV: {exc}", Colors.RED))
            return False

        if len(loaded) != 32:
            print(
                Colors.wrap(
                    f"خطا: انتظار ۳۲ تیم بود؛ {len(loaded)} تیم خوانده شد.",
                    Colors.RED,
                )
            )
            return False

        self.teams = loaded
        self.groups = []
        self.round_of_16 = None
        self.quarterfinals = None
        self.semifinals = None
        self.final = None
        self.champion = None
        self._drawn = False
        self._group_played = False
        self._last_bracket_ready = False
        print(
            Colors.wrap(
                f"✓ {len(self.teams)} تیم با موفقیت از «{filename}» بارگذاری شد.",
                Colors.GREEN,
            )
        )
        return True

    # ---- سیدبندی و قرعه ----
    def groups_draw_and_seed(self) -> bool:
        """
        سیدبندی بر اساس رتبه فیفا و قرعه‌کشی ۸ گروه ۴ تیمی
        (هر گروه یک تیم از هر سید).
        """
        if not self.teams:
            print(Colors.wrap("ابتدا تیم‌ها را بارگذاری کنید (گزینه ۱).", Colors.YELLOW))
            return False

        ordered = sorted(self.teams, key=lambda t: t.rank)
        seeds = [
            ordered[0:8],    # سید ۱
            ordered[8:16],   # سید ۲
            ordered[16:24],  # سید ۳
            ordered[24:32],  # سید ۴
        ]
        for s in seeds:
            random.shuffle(s)

        self.groups = []
        for i, gname in enumerate(self.GROUP_NAMES):
            group_teams = [seeds[s][i] for s in range(4)]
            for t in group_teams:
                t.group = gname
                t.reset_stats()
            self.groups.append(Group(gname, group_teams))

        self._drawn = True
        self._group_played = False
        self._last_bracket_ready = False
        self.champion = None
        self.round_of_16 = self.quarterfinals = self.semifinals = self.final = None

        print(Colors.wrap("✓ قرعه‌کشی گروه‌ها با سیدبندی انجام شد:", Colors.GREEN))
        for g in self.groups:
            names = ", ".join(t.name for t in g.teams)
            print(f"  Group {g.name}: {names}")
        return True

    # ---- مرحله گروهی ----
    def stage_group_run(self) -> bool:
        """اجرای مرحله گروهی و نمایش جدول هر گروه."""
        if not self._drawn or not self.groups:
            print(
                Colors.wrap(
                    "ابتدا قرعه‌کشی گروه‌ها را انجام دهید (گزینه ۲).",
                    Colors.YELLOW,
                )
            )
            return False

        for t in self.teams:
            t.reset_stats()

        for g in self.groups:
            g.matches_all_play()

        self._group_played = True
        print(Colors.wrap("\n===== جداول مرحله گروهی =====", Colors.CYAN))
        for g in self.groups:
            g.display_table()
            print()
        return True

    # ---- براکت حذفی ----
    def bracket_knockout_setup(self) -> bool:
        """
        ساخت براکت یک‌هشتم نهایی مطابق PDF:

        A1-B2, C1-D2, E1-F2, G1-H2, B1-A2, D1-C2, F1-E2, H1-G2
        """
        if not self._group_played:
            print(
                Colors.wrap(
                    "ابتدا مرحله گروهی را اجرا کنید (گزینه ۳ یا ۴).",
                    Colors.YELLOW,
                )
            )
            return False

        by_name = {g.name: g for g in self.groups}
        adv: Dict[str, List[Team]] = {
            g.name: g.advance_teams() for g in self.groups
        }

        def pick(group_letter: str, place: int) -> Team:
            return adv[group_letter][place - 1]

        pairs = [
            (pick("A", 1), pick("B", 2)),
            (pick("C", 1), pick("D", 2)),
            (pick("E", 1), pick("F", 2)),
            (pick("G", 1), pick("H", 2)),
            (pick("B", 1), pick("A", 2)),
            (pick("D", 1), pick("C", 2)),
            (pick("F", 1), pick("E", 2)),
            (pick("H", 1), pick("G", 2)),
        ]
        matches = [Match(a, b, is_knockout=True) for a, b in pairs]
        self.round_of_16 = KnockoutStage("Round of 16", matches)
        self.quarterfinals = None
        self.semifinals = None
        self.final = None
        return True

    def stage_knockout_run(self) -> Optional[Team]:
        """اجرای یک‌هشتم تا فینال و تعیین قهرمان."""
        if self.round_of_16 is None:
            if not self.bracket_knockout_setup():
                return None

        # Round of 16
        self.round_of_16.round_play()
        w16 = self.round_of_16.winners_get()

        # Quarterfinals: 0-1, 2-3, 4-5, 6-7
        qf_matches = [
            Match(w16[0], w16[1], True),
            Match(w16[2], w16[3], True),
            Match(w16[4], w16[5], True),
            Match(w16[6], w16[7], True),
        ]
        self.quarterfinals = KnockoutStage("Quarterfinals", qf_matches)
        self.quarterfinals.round_play()
        wqf = self.quarterfinals.winners_get()

        # Semifinals
        sf_matches = [
            Match(wqf[0], wqf[1], True),
            Match(wqf[2], wqf[3], True),
        ]
        self.semifinals = KnockoutStage("Semifinals", sf_matches)
        self.semifinals.round_play()
        wsf = self.semifinals.winners_get()

        # Final
        final_match = [Match(wsf[0], wsf[1], True)]
        self.final = KnockoutStage("Final", final_match)
        self.final.round_play()
        self.champion = self.final.winners_get()[0]
        self._last_bracket_ready = True
        return self.champion

    def simulation_full_run(self, verbose: bool = True) -> Optional[Team]:
        """
        اجرای کامل جام (گروهی + حذفی) و برگرداندن قهرمان.
        قبل از اجرا آمار همه تیم‌ها reset می‌شود.
        """
        if not self.teams:
            if verbose:
                print(Colors.wrap("تیمی بارگذاری نشده است.", Colors.YELLOW))
            return None
        if not self._drawn:
            if verbose:
                print(Colors.wrap("قرعه‌کشی انجام نشده است.", Colors.YELLOW))
            return None

        for t in self.teams:
            t.reset_stats()

        for g in self.groups:
            g.matches_all_play()
        self._group_played = True

        if verbose:
            print(Colors.wrap("\n===== جداول مرحله گروهی =====", Colors.CYAN))
            for g in self.groups:
                g.display_table()
                print()

        self.bracket_knockout_setup()
        champ = self.stage_knockout_run()

        if verbose and champ is not None and self.final is not None:
            print(Colors.wrap("===== FINAL =====", Colors.MAGENTA))
            fm = self.final.matches[0]
            print(f"{fm.team1.name} {fm.goals1} - {fm.goals2} {fm.team2.name}")
            if fm.penalties:
                print(f"(پنالتی: {fm.pen_score1}-{fm.pen_score2})")
            print(
                Colors.wrap(
                    f"قهرمان جام جهانی: {champ.name}",
                    Colors.GREEN + Colors.BOLD,
                )
            )
            self.display_tournament_stats()
        return champ

    def champion_likely_most(self, simulations_num: int = 1000) -> Dict[str, float]:
        """
        شبیه‌سازی چندباره جام و محاسبه درصد قهرمانی هر تیم.

        Args:
            simulations_num: تعداد شبیه‌سازی (پیش‌فرض ۱۰۰۰)

        Returns:
            دیکشنری نام تیم -> درصد قهرمانی
        """
        if simulations_num <= 0:
            print(Colors.wrap("تعداد شبیه‌سازی باید عدد مثبت باشد.", Colors.RED))
            return {}

        if not self.teams:
            print(Colors.wrap("ابتدا تیم‌ها را بارگذاری کنید (گزینه ۱).", Colors.YELLOW))
            return {}

        win_count: Counter = Counter()
        # برای تکرارپذیری گزینه ۵ می‌توان seed بیرونی تنظیم کرد
        for _ in range(simulations_num):
            # هر بار قرعه و تورنمنت از نو
            self.groups_draw_and_seed()
            for t in self.teams:
                t.reset_stats()
            for g in self.groups:
                g.matches_all_play()
            self._group_played = True
            self.bracket_knockout_setup()
            champ = self.stage_knockout_run()
            if champ is not None:
                win_count[champ.name] += 1

        percentages: Dict[str, float] = {}
        print(
            Colors.wrap(
                f"شبیه سازی {simulations_num} بار انجام شد.",
                Colors.CYAN,
            )
        )
        print("درصد قهرمانی هر تیم:")
        for name, cnt in win_count.most_common():
            pct = 100.0 * cnt / simulations_num
            percentages[name] = pct
            print(f"{name}: {pct:.1f}%")

        # تیم‌هایی که هرگز قهرمان نشدند
        for t in sorted(self.teams, key=lambda x: x.rank):
            if t.name not in percentages:
                percentages[t.name] = 0.0

        if HAS_MATPLOTLIB and percentages:
            self._plot_champion_percentages(percentages, simulations_num)
        elif not HAS_MATPLOTLIB:
            print(
                Colors.wrap(
                    "(matplotlib نصب نیست؛ نمودار رسم نشد.)",
                    Colors.GRAY,
                )
            )

        return percentages

    def _plot_champion_percentages(
        self, percentages: Dict[str, float], n: int
    ) -> None:
        """نمودار میله‌ای عمودی درصد قهرمانی با گرادیان فلزی و عنوان گرادیانی."""
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
        from matplotlib.colors import LinearSegmentedColormap
        import numpy as np # numpy به همراه matplotlib نصب شده است
        
        # فیلتر کردن تیم‌ها با درصد بزرگتر از صفر و مرتب‌سازی
        items = [(k, v) for k, v in percentages.items() if v > 0]
        items.sort(key=lambda x: x[1], reverse=True)
        if not items:
            return
        
        names = [i[0] for i in items]
        vals = [i[1] for i in items]

        # ساخت شکل و محورها
        fig, ax = plt.subplots(figsize=(20, 9))
        fig.patch.set_facecolor('white')
        ax.set_facecolor('#f8f9fa')

        # کاهش ضخامت میله‌ها برای ایجاد فاصله بیشتر
        width = 0.5 
        max_val = max(vals) if vals else 10
        
        # --- ساخت پس‌زمینه گرادیانی سبز برای عنوان ---
        ax_title = fig.add_axes([0.0, 0.93, 1.0, 0.07])
        ax_title.set_xlim(0, 1)
        ax_title.set_ylim(0, 1)
        ax_title.axis('off')
        
        # ایجاد تصویر گرادیان سبز
        grad = np.linspace(0, 1, 256).reshape(1, -1)
        ax_title.imshow(grad, aspect='auto', extent=[0, 1, 0, 1], cmap=LinearSegmentedColormap.from_list('green', ['#064e3b', '#10b981']))
        
        # متن عنوان اصلی (فونت ۱۸، سفید، ضخیم)
        ax_title.text(0.5, 0.65, "🏆 World Cup 2026 Champion Probability 🏆", 
                      ha='center', va='center', fontsize=18, color='white', 
                      fontweight='bold', fontfamily='sans-serif')
        
        # متن داخل پرانتز (فونت ۱۴، ریزتر، سبز روشن، کج)
        ax_title.text(0.5, 0.25, f"({n:,} Simulations Run)", 
                      ha='center', va='center', fontsize=14, color='#ecfdf5', 
                      style='italic', fontfamily='sans-serif')

        for i, (name, val) in enumerate(zip(names, vals)):
            if i < 3:
                # --- گرادیان فلزی برای ۳ تیم اول ---
                if i == 0:
                    colors_list = ['#FFF8DC', '#FFD700', '#DAA520', '#B8860B'] # طلا
                elif i == 1:
                    colors_list = ['#FFFFFF', '#E8E8E8', '#C0C0C0', '#A9A9A9'] # نقره
                else:
                    colors_list = ['#FFE4C4', '#CD7F32', '#8B4513', '#5C3317'] # برنز
                
                cmap = LinearSegmentedColormap.from_list('metal', colors_list)
                # ساخت یک مستطیل گرادیانی و برش آن به شکل میله گرد
                box = FancyBboxPatch(xy=(i - width/2, 0), width=width, height=val, 
                                     boxstyle="round,pad=0,rounding_size=0.04", 
                                     linewidth=1.2, edgecolor='#2c3e50', facecolor='none', zorder=3)
                ax.add_patch(box)
                
                grad_bar = np.linspace(0, 1, 256).reshape(-1, 1)
                im = ax.imshow(grad_bar, extent=[i - width/2, i + width/2, 0, val], aspect='auto', cmap=cmap, zorder=2)
                im.set_clip_path(box)
            else:
                # --- میله‌های معمولی برای بقیه تیم‌ها ---
                ratio = (i - 3) / max(1, (len(names) - 4))
                r = int(31 + (72 - 31) * ratio)
                g = int(58 + (219 - 58) * ratio)
                b = int(147 + (251 - 147) * ratio)
                color = (r/255, g/255, b/255, 1.0)

                box = FancyBboxPatch(xy=(i - width/2, 0), width=width, height=val, 
                                     boxstyle="round,pad=0,rounding_size=0.05", 
                                     linewidth=0.8, edgecolor='#2c3e50', facecolor=color, zorder=2)
                ax.add_patch(box)
            
            # نوشتن درصد دقیقاً بالای هر میله (فونت کوچک‌تر = 9)
            ax.text(i, val + max_val * 0.015, f"{val:.1f}%", 
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='#2c3e50', 
                    fontfamily='sans-serif', zorder=4)

        # تنظیمات محورها
        ax.set_ylabel("Championship Probability (%)", fontsize=14, fontweight='bold', color='#34495e', labelpad=15, fontfamily='sans-serif')
        
        # نام کشورها ریزتر و با فونت زیبا
        ax.set_xlim(-0.4, len(names) - 0.6) 
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha='right', fontsize=10, color='#2c3e50', fontfamily='sans-serif')
        plt.yticks(fontsize=11, color='#7f8c8d', fontfamily='sans-serif')

        # حذف خطوط حاشیه (اسپاین‌ها)
        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        ax.spines['bottom'].set_color('#bdc3c7')

        # شبکه‌بندی محور Y
        ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#bdc3c7')
        ax.set_axisbelow(True)
        ax.set_ylim(0, max_val + max_val * 0.15)

        # --- حذف فضای خالی سفید اطراف نمودار (کشیدن نمودار به دور تا دور تصویر) ---
        plt.subplots_adjust(left=0.03, right=0.99, bottom=0.14, top=0.88)
        
        out = "champion_probability.png"
        plt.savefig(out, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.show()
        print(Colors.wrap(f"✓ نمودار حرفه‌ای با موفقیت ذخیره شد: {out}", Colors.GREEN))

    def bracket_display(self) -> None:
        """نمایش براکت حذفی آخرین شبیه‌سازی."""
        if not self._last_bracket_ready or self.round_of_16 is None:
            print(
                Colors.wrap(
                    "براکت آماده‌ای وجود ندارد. ابتدا گزینه ۴ (یا ۵) را اجرا کنید.",
                    Colors.YELLOW,
                )
            )
            return

        print(Colors.wrap("===== Knockout Bracket =====", Colors.CYAN))
        for stage in (
            self.round_of_16,
            self.quarterfinals,
            self.semifinals,
            self.final,
        ):
            if stage is not None:
                stage.results_display()
                print()
        if self.champion is not None:
            print(Colors.wrap(f"Champion: {self.champion.name}", Colors.GREEN + Colors.BOLD))

    def display_tournament_stats(self) -> None:
        """آمار خلاقانه تورنمنت (بهترین حمله/دفاع/امتیاز گروهی)."""
        if not self.teams:
            return
        # فقط تیم‌هایی که در گروهی بازی کرده‌اند (امتیاز یا گل)
        best_attack = max(self.teams, key=lambda t: t.for_goals)
        best_defense = min(self.teams, key=lambda t: t.against_goals)
        best_points = max(self.teams, key=lambda t: t.points)
        print(Colors.wrap("----- آمار تورنمنت -----", Colors.BLUE))
        print(f"بهترین خط حمله: {best_attack.name} ({best_attack.for_goals} گل)")
        print(
            f"بهترین خط دفاع: {best_defense.name} ({best_defense.against_goals} گل‌خورده)"
        )
        print(f"بیشترین امتیاز گروهی: {best_points.name} ({best_points.points} pts)")


# ---------------------------------------------------------------------------
# منوی اصلی
# ---------------------------------------------------------------------------
def print_menu() -> None:
    print()
    print(Colors.wrap("=====شبیه ساز جام جهانی=====", Colors.BOLD + Colors.CYAN))
    print("1) بارگذاری تیمها از فایلCSV")
    print("2) انجام قرعهکشی گروهها (سیدبندی خودکار)")
    print("3) اجرای مرحله گروهی و نمایش جدول هر گروه")
    print("4) اجرای کامل جام (گروهی + حذفی) و نمایش قهرمان")
    print("5) شبیه سازی ۱۰۰۰ باره و گزارش درصد قهرمانی")
    print("6) نمایش براکت حذفی آخرین شبیه سازی")
    print("7) خروج")


def ask_int(prompt: str, default: Optional[int] = None) -> Optional[int]:
    """خواندن عدد صحیح از کاربر با مدیریت خطا."""
    raw = input(prompt).strip()
    if raw == "" and default is not None:
        return default
    try:
        return int(raw)
    except ValueError:
        print(Colors.wrap("ورودی نامعتبر است؛ عدد وارد کنید.", Colors.RED))
        return None


def main() -> None:
    sim = WorldCupSimulator()

    while True:
        print_menu()
        choice = input("انتخاب شما: ").strip()

        if choice == "1":
            path = input(f"نام فایل CSV [{DEFAULT_CSV}]: ").strip() or DEFAULT_CSV
            sim.load_teams_from_csv(path)

        elif choice == "2":
            sim.groups_draw_and_seed()

        elif choice == "3":
            sim.stage_group_run()

        elif choice == "4":
            if not sim.teams:
                print(Colors.wrap("ابتدا تیم‌ها را بارگذاری کنید (گزینه ۱).", Colors.YELLOW))
            elif not sim._drawn:
                print(Colors.wrap("ابتدا قرعه‌کشی را انجام دهید (گزینه ۲).", Colors.YELLOW))
            else:
                sim.simulation_full_run(verbose=True)

        elif choice == "5":
            if not sim.teams:
                print(Colors.wrap("ابتدا تیم‌ها را بارگذاری کنید (گزینه ۱).", Colors.YELLOW))
                continue
            n = ask_int("تعداد شبیه‌سازی [1000]: ", default=1000)
            if n is None:
                continue
            if n <= 0:
                print(Colors.wrap("تعداد باید مثبت باشد.", Colors.RED))
                continue
            seed_raw = input("seed تصادفی (Enter = بدون seed ثابت): ").strip()
            if seed_raw:
                try:
                    random.seed(int(seed_raw))
                    print(Colors.wrap(f"seed={seed_raw} تنظیم شد.", Colors.GRAY))
                except ValueError:
                    print(Colors.wrap("seed نامعتبر نادیده گرفته شد.", Colors.YELLOW))
            sim.champion_likely_most(simulations_num=n)

        elif choice == "6":
            sim.bracket_display()

        elif choice == "7":
            print(Colors.wrap("خروج از برنامه. موفق باشید!", Colors.GREEN))
            break

        else:
            print(Colors.wrap("گزینه نامعتبر است (۱ تا ۷).", Colors.RED))


if __name__ == "__main__":
    main()