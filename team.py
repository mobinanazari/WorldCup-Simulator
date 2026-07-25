"""ماژول مدل تیم ملی."""

from typing import Optional, Tuple

class Team:
    """اطلاعات و آمار یک تیم ملی را نگهداری می‌کند.

    Attributes:
        name (str): نام تیم.
        attack (float): قدرت حمله تیم (0 تا 100).
        defense (float): قدرت دفاع تیم (0 تا 100).
        rank (int): رتبه جهانی تیم.
        for_goals (int): تعداد گل‌های زده شده در تورنمنت.
        against_goals (int): تعداد گل‌های خورده در تورنمنت.
        points (int): امتیاز کسب شده در مرحله گروهی.
        group (Optional[str]): نام گروهی که تیم در آن قرار دارد.
    """

    def __init__(self, name: str, attack: float, defense: float, rank: int) -> None:
        """سازنده کلاس Team.

        Args:
            name (str): نام تیم.
            attack (float): قدرت حمله.
            defense (float): قدرت دفاع.
            rank (int): رتبه تیم.
        """
        self.name, self.attack, self.defense, self.rank = name, float(attack), float(defense), int(rank)
        self.for_goals = self.against_goals = self.points = 0
        self.group: Optional[str] = None

    def goal_difference(self) -> int:
        """تفاضل گل تیم را محاسبه می‌کند.

        Returns:
            int: تفاضل گل (گل زده - گل خورده).
        """
        return self.for_goals - self.against_goals

    def reset_stats(self) -> None:
        """آمار تیم (گل‌ها و امتیازات) را برای شروع مسابقات جدید صفر می‌کند."""
        self.for_goals = self.against_goals = self.points = 0

    def _lambda_against(self, opponent: "Team") -> float:
        """گل مورد انتظار تیم مقابل حریف را محاسبه می‌کند (فرمول پروژه).

        Args:
            opponent (Team): تیم حریف.

        Returns:
            float: میانگین گل‌های مورد انتظار در ۹۰ دقیقه.
        """
        return self.attack / 100 * 1.5 + (1 - opponent.defense / 100) * 0.8

    def penalty_success_prob(self, opponent: "Team") -> float:
        """احتمال موفقیت پنالتی را بر اساس قدرت تیم‌ها محاسبه می‌کند.

        Args:
            opponent (Team): تیم حریف.

        Returns:
            float: احتمال موفقیت در بازه 0.6 تا 0.9.
        """
        return max(0.6, min(0.9, 0.75 + (self.attack - opponent.defense) / 250))

    def simulate_match(self, opponent: "Team", is_knockout: bool = False) -> Tuple[int, int, Optional["Team"]]:
        """مسابقه را شبیه‌سازی می‌کند (متد کمکی).

        Args:
            opponent (Team): تیم حریف.
            is_knockout (bool, optional): آیا مسابقه حذفی است؟ پیش‌فرض False.

        Returns:
            Tuple[int, int, Optional[Team]]: (گل تیم اول، گل تیم دوم، تیم برنده)
        """
        # برای جلوگیری از ایمپورت دور (Circular Import)، Match داخل تابع لود می‌شود.
        from match import Match
        match = Match(self, opponent, is_knockout)
        match.play()
        return match.goals1, match.goals2, match.winner