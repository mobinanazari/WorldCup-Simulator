"""ماژول کنترل‌کننده اصلی جام جهانی."""

import csv
import os
import random
from collections import Counter
from typing import Dict, List, Optional

# matplotlib اختیاری است
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from team import Team
from match import Match
from group import Group
from knockout_stage import KnockoutStage
from utils import Colors, DEFAULT_CSV, FALLBACK_CSV

class WorldCupSimulator:
    """بارگذاری، قرعه، مراحل جام، آمار و نمودار را مدیریت می‌کند.

    Attributes:
        teams (List[Team]): لیست ۳۲ تیم بارگذاری شده.
        groups (List[Group]): لیست ۸ گروه.
        round_of_16 (Optional[KnockoutStage]): مرحله یک‌هشتم.
        quarterfinals (Optional[KnockoutStage]): مرحله یک‌چهارم.
        semifinals (Optional[KnockoutStage]): مرحله نیمه‌نهایی.
        final (Optional[KnockoutStage]): مرحله فینال.
        champion (Optional[Team]): تیم قهرمان نهایی.
    """

    GROUP_NAMES = list("ABCDEFGH")

    def __init__(self) -> None:
        """سازنده کلاس WorldCupSimulator. متغیرها را مقداردهی اولیه می‌کند."""
        self.teams, self.groups = [], []
        self.round_of_16 = self.quarterfinals = self.semifinals = self.final = None
        self.champion: Optional[Team] = None
        self._drawn = self._group_played = self._last_bracket_ready = False

    def _clear_knockout(self) -> None:
        """اطلاعات مراحل حذفی قبلی را پاک می‌کند."""
        self.round_of_16 = self.quarterfinals = self.semifinals = self.final = None
        self.champion, self._last_bracket_ready = None, False

    def _play_group_stage(self) -> None:
        """آمار تیم‌ها را صفر کرده و همه بازی‌های گروهی را اجرا می‌کند."""
        for team in self.teams:
            team.reset_stats()
        for group in self.groups:
            group.matches_all_play()
        self._group_played = True

    def _display_groups(self) -> None:
        """جدول هر هشت گروه را در ترمینال چاپ می‌کند."""
        print(Colors.wrap("\n===== جداول مرحله گروهی =====", Colors.CYAN))
        for group in self.groups:
            group.display_table()
            print()

    @staticmethod
    def _make_stage(name: str, teams: List[Team]) -> KnockoutStage:
        """از فهرست برندگان، مسابقات مرحله حذفی بعدی را می‌سازد.

        Args:
            name (str): نام مرحله.
            teams (List[Team]): تیم‌های صعودکننده.

        Returns:
            KnockoutStage: شیء مرحله حذفی ساخته شده.
        """
        return KnockoutStage(name, [Match(teams[i], teams[i + 1], True) for i in range(0, len(teams), 2)])

    def load_teams_from_csv(self, filename: str) -> bool:
        """۳۲ تیم را از فایل CSV می‌خواند.

        Args:
            filename (str): مسیر فایل CSV.

        Returns:
            bool: True در صورت موفقیت، False در صورت خطا.
        """
        if not os.path.isfile(filename):
            if filename == DEFAULT_CSV and os.path.isfile(FALLBACK_CSV):
                filename = FALLBACK_CSV
            else:
                print(Colors.wrap(f"خطا: فایل «{filename}» یافت نشد.", Colors.RED))
                return False
        loaded: List[Team] = []
        try:
            with open(filename, "r", encoding="utf-8-sig", newline="") as file:
                for row in csv.DictReader(file):
                    data = {key.strip().lower(): (value.strip() if isinstance(value, str) else value)
                            for key, value in row.items() if key}
                    if data.get("name"):
                        loaded.append(Team(data["name"], float(data["attack"]), float(data["defense"]),
                                           int(float(data["rank"]))))
        except (OSError, ValueError, KeyError, csv.Error) as error:
            print(Colors.wrap(f"خطا در خواندن CSV: {error}", Colors.RED))
            return False
        if len(loaded) != 32:
            print(Colors.wrap(f"خطا: انتظار ۳۲ تیم بود؛ {len(loaded)} تیم خوانده شد.", Colors.RED))
            return False
        self.teams, self.groups = loaded, []
        self._drawn = self._group_played = False
        self._clear_knockout()
        print(Colors.wrap(f"✓ {len(self.teams)} تیم با موفقیت از «{filename}» بارگذاری شد.", Colors.GREEN))
        return True

    def groups_draw_and_seed(self) -> bool:
        """سیدبندی و قرعه‌کشی تیم‌ها در ۸ گروه را انجام می‌دهد.

        Returns:
            bool: True در صورت موفقیت، False در صورت نبود تیم.
        """
        if not self.teams:
            print(Colors.wrap("ابتدا تیم‌ها را بارگذاری کنید (گزینه ۱).", Colors.YELLOW))
            return False
        ordered = sorted(self.teams, key=lambda team: team.rank)
        seeds = [ordered[start:start + 8] for start in range(0, 32, 8)]
        for seed in seeds:
            random.shuffle(seed)
        self.groups = []
        for index, name in enumerate(self.GROUP_NAMES):
            teams = [seeds[seed][index] for seed in range(4)]
            for team in teams:
                team.group = name
                team.reset_stats()
            self.groups.append(Group(name, teams))
        self._drawn, self._group_played = True, False
        self._clear_knockout()
        print(Colors.wrap("✓ قرعه‌کشی گروه‌ها با سیدبندی انجام شد:", Colors.GREEN))
        for group in self.groups:
            print(f"  Group {group.name}: {', '.join(team.name for team in group.teams)}")
        return True

    def stage_group_run(self) -> bool:
        """مرحله گروهی را اجرا و جداول را نمایش می‌دهد.

        Returns:
            bool: True در صورت موفقیت، False در صورت انجام نشدن قرعه قبلی.
        """
        if not self._drawn or not self.groups:
            print(Colors.wrap("ابتدا قرعه‌کشی گروه‌ها را انجام دهید (گزینه ۲).", Colors.YELLOW))
            return False
        self._play_group_stage()
        self._display_groups()
        return True

    def bracket_knockout_setup(self) -> bool:
        """براکت یک‌هشتم نهایی را بر اساس نتایج گروهی می‌سازد.

        Returns:
            bool: True در صورت موفقیت، False در صورت اجرا نشدن مرحله گروهی.
        """
        if not self._group_played:
            print(Colors.wrap("ابتدا مرحله گروهی را اجرا کنید (گزینه ۳ یا ۴).", Colors.YELLOW))
            return False
        advanced = {group.name: group.advance_teams() for group in self.groups}
        specs = (("A", 0, "B", 1), ("C", 0, "D", 1), ("E", 0, "F", 1), ("G", 0, "H", 1),
                 ("B", 0, "A", 1), ("D", 0, "C", 1), ("F", 0, "E", 1), ("H", 0, "G", 1))
        self.round_of_16 = KnockoutStage("Round of 16", [
            Match(advanced[a][pa], advanced[b][pb], True) for a, pa, b, pb in specs])
        self.quarterfinals = self.semifinals = self.final = None
        return True

    def stage_knockout_run(self) -> Optional[Team]:
        """تمام مراحل حذفی را اجرا می‌کند.

        Returns:
            Optional[Team]: تیم قهرمان یا None در صورت بروز خطا.
        """
        if self.round_of_16 is None and not self.bracket_knockout_setup():
            return None
        self.round_of_16.round_play()
        winners = self.round_of_16.winners_get()
        for attribute, name in (("quarterfinals", "Quarterfinals"), ("semifinals", "Semifinals"), ("final", "Final")):
            stage = self._make_stage(name, winners)
            setattr(self, attribute, stage)
            stage.round_play()
            winners = stage.winners_get()
        self.champion, self._last_bracket_ready = winners[0], True
        return self.champion

    def simulation_full_run(self, verbose: bool = True) -> Optional[Team]:
        """جام کامل را از قرعه‌کشی تا فینال اجرا می‌کند.

        Args:
            verbose (bool, optional): آیا نتایج چاپ شود؟ پیش‌فرض True.

        Returns:
            Optional[Team]: تیم قهرمان نهایی.
        """
        if not self.teams:
            if verbose: print(Colors.wrap("تیمی بارگذاری نشده است.", Colors.YELLOW))
            return None
        if not self._drawn:
            if verbose: print(Colors.wrap("قرعه‌کشی انجام نشده است.", Colors.YELLOW))
            return None
        self._play_group_stage()
        if verbose: self._display_groups()
        self.bracket_knockout_setup()
        champion = self.stage_knockout_run()
        if verbose and champion is not None and self.final is not None:
            print(Colors.wrap("===== FINAL =====", Colors.MAGENTA))
            match = self.final.matches[0]
            print(f"{match.team1.name} {match.goals1} - {match.goals2} {match.team2.name}")
            if match.penalties:
                print(f"(پنالتی: {match.pen_score1}-{match.pen_score2})")
            print(Colors.wrap(f"قهرمان جام جهانی: {champion.name}", Colors.GREEN + Colors.BOLD))
            self.display_tournament_stats()
        return champion

    def champion_likely_most(self, simulations_num: int = 1000) -> Dict[str, float]:
        """جام را چندین بار شبیه‌سازی می‌کند تا درصد قهرمانی هر تیم را بدهد.

        Args:
            simulations_num (int, optional): تعداد دفعات شبیه‌سازی. پیش‌فرض 1000.

        Returns:
            Dict[str, float]: دیکشنری نام تیم و درصد قهرمانی آن.
        """
        if simulations_num <= 0:
            print(Colors.wrap("تعداد شبیه‌سازی باید عدد مثبت باشد.", Colors.RED))
            return {}
        if not self.teams:
            print(Colors.wrap("ابتدا تیم‌ها را بارگذاری کنید (گزینه ۱).", Colors.YELLOW))
            return {}
        wins: Counter = Counter()
        for _ in range(simulations_num):
            self.groups_draw_and_seed()
            self._play_group_stage()
            self.bracket_knockout_setup()
            champion = self.stage_knockout_run()
            if champion is not None:
                wins[champion.name] += 1
        percentages: Dict[str, float] = {}
        print(Colors.wrap(f"شبیه سازی {simulations_num} بار انجام شد.", Colors.CYAN))
        print("درصد قهرمانی هر تیم:")
        for name, count in wins.most_common():
            percentages[name] = 100 * count / simulations_num
            print(f"{name}: {percentages[name]:.1f}%")
        for team in sorted(self.teams, key=lambda item: item.rank):
            percentages.setdefault(team.name, 0.0)
        if HAS_MATPLOTLIB and percentages:
            self._plot_champion_percentages(percentages, simulations_num)
        elif not HAS_MATPLOTLIB:
            print(Colors.wrap("(matplotlib نصب نیست؛ نمودار رسم نشد.)", Colors.GRAY))
        return percentages

    def _plot_champion_percentages(self, percentages: Dict[str, float], simulations_num: int) -> None:
        """نمودار میله‌ای درصد قهرمانی تیم‌ها را رسم و ذخیره می‌کند.

        Args:
            percentages (Dict[str, float]): درصدهای قهرمانی تیم‌ها.
            simulations_num (int): تعداد کل شبیه‌سازی‌ها.
        """
        from matplotlib.colors import LinearSegmentedColormap
        from matplotlib.patches import FancyBboxPatch
        import numpy as np

        items = sorted(((n, v) for n, v in percentages.items() if v > 0), key=lambda item: item[1], reverse=True)
        if not items:
            return
        names, values = map(list, zip(*items))
        fig, ax = plt.subplots(figsize=(20, 9))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("#f8f9fa")
        width, max_value = 0.5, max(values) if values else 10
        title_axis = fig.add_axes([0.0, 0.93, 1.0, 0.07])
        title_axis.set(xlim=(0, 1), ylim=(0, 1))
        title_axis.axis("off")
        title_axis.imshow(np.linspace(0, 1, 256).reshape(1, -1), aspect="auto", extent=[0, 1, 0, 1], cmap=LinearSegmentedColormap.from_list("green", ["#064e3b", "#10b981"]))
        title_axis.text(0.5, 0.65, "🏆 World Cup 2026 Champion Probability 🏆", ha="center", va="center", fontsize=18, color="white", fontweight="bold", fontfamily="sans-serif")
        title_axis.text(0.5, 0.25, f"({simulations_num:,} Simulations Run)", ha="center", va="center", fontsize=14, color="#ecfdf5", style="italic", fontfamily="sans-serif")
        
        medals = (["#FFF8DC", "#FFD700", "#DAA520", "#B8860B"], ["#FFFFFF", "#E8E8E8", "#C0C0C0", "#A9A9A9"], ["#FFE4C4", "#CD7F32", "#8B4513", "#5C3317"])
        for index, value in enumerate(values):
            if index < 3:
                box = FancyBboxPatch((index - width / 2, 0), width, value, boxstyle="round,pad=0,rounding_size=0.04", linewidth=1.2, edgecolor="#2c3e50", facecolor="none", zorder=3)
                ax.add_patch(box)
                image = ax.imshow(np.linspace(0, 1, 256).reshape(-1, 1), extent=[index - width / 2, index + width / 2, 0, value], aspect="auto", cmap=LinearSegmentedColormap.from_list("metal", medals[index]), zorder=2)
                image.set_clip_path(box)
            else:
                ratio = (index - 3) / max(1, len(names) - 4)
                red, green, blue = (int(a + (b - a) * ratio) for a, b in ((31, 72), (58, 219), (147, 251)))
                ax.add_patch(FancyBboxPatch((index - width / 2, 0), width, value, boxstyle="round,pad=0,rounding_size=0.05", linewidth=0.8, edgecolor="#2c3e50", facecolor=(red / 255, green / 255, blue / 255, 1.0), zorder=2))
            ax.text(index, value + max_value * 0.015, f"{value:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#2c3e50", fontfamily="sans-serif", zorder=4)
            
        ax.set_ylabel("Championship Probability (%)", fontsize=14, fontweight="bold", color="#34495e", labelpad=15, fontfamily="sans-serif")
        ax.set_xlim(-0.4, len(names) - 0.6)
        ax.set_xticks(range(len(names)), names, rotation=45, ha="right", fontsize=10, color="#2c3e50", fontfamily="sans-serif")
        plt.yticks(fontsize=11, color="#7f8c8d", fontfamily="sans-serif")
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color("#bdc3c7")
        ax.yaxis.grid(True, linestyle="--", alpha=0.5, color="#bdc3c7")
        ax.set_axisbelow(True)
        ax.set_ylim(0, max_value * 1.15)
        plt.subplots_adjust(left=0.03, right=0.99, bottom=0.14, top=0.88)
        plt.savefig("champion_probability.png", dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.show()
        print(Colors.wrap("✓ نمودار حرفه‌ای با موفقیت ذخیره شد: champion_probability.png", Colors.GREEN))

    def bracket_display(self) -> None:
        """آخرین براکت حذفی اجرا شده را چاپ می‌کند."""
        if not self._last_bracket_ready or self.round_of_16 is None:
            print(Colors.wrap("براکت آماده‌ای وجود ندارد. ابتدا گزینه ۴ (یا ۵) را اجرا کنید.", Colors.YELLOW))
            return
        print(Colors.wrap("===== Knockout Bracket =====", Colors.CYAN))
        for stage in (self.round_of_16, self.quarterfinals, self.semifinals, self.final):
            if stage is not None:
                stage.results_display()
                print()
        if self.champion is not None:
            print(Colors.wrap(f"Champion: {self.champion.name}", Colors.GREEN + Colors.BOLD))

    def display_tournament_stats(self) -> None:
        """آمار منتخب جام (بهترین حمله، دفاع و امتیازگیر) را چاپ می‌کند."""
        if not self.teams:
            return
        attack, defense, points = (max(self.teams, key=lambda t: t.for_goals),
                                   min(self.teams, key=lambda t: t.against_goals), max(self.teams, key=lambda t: t.points))
        print(Colors.wrap("----- آمار تورنمنت -----", Colors.BLUE))
        print(f"بهترین خط حمله: {attack.name} ({attack.for_goals} گل)")
        print(f"بهترین خط دفاع: {defense.name} ({defense.against_goals} گل‌خورده)")
        print(f"بیشترین امتیاز گروهی: {points.name} ({points.points} pts)")