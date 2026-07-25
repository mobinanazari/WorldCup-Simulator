"""ماژول مدیریت مراحل حذفی."""

import random
from typing import List, Optional

from match import Match
from team import Team

class KnockoutStage:
    """یک مرحله حذفی (یک‌هشتم، یک‌چهارم، نیمه‌نهایی یا فینال) را مدیریت می‌کند.

    Attributes:
        round_name (str): نام مرحله.
        matches (List[Match]): لیست مسابقات این مرحله.
    """

    def __init__(self, round_name: str, matches: Optional[List[Match]] = None) -> None:
        """سازنده کلاس KnockoutStage.

        Args:
            round_name (str): نام مرحله (مثلاً Quarterfinals).
            matches (Optional[List[Match]], optional): لیست بازی‌ها. پیش‌فرض None.
        """
        self.round_name, self.matches = round_name, list(matches) if matches else []

    def round_play(self) -> None:
        """همه مسابقات این مرحله را اجرا می‌کند."""
        for match in self.matches:
            match.play()

    def winners_get(self) -> List[Team]:
        """برندگان تمام مسابقات این مرحله را برمی‌گرداند.

        Returns:
            List[Team]: لیست تیم‌های صعودکننده به مرحله بعد.
        """
        return [m.winner if m.winner is not None else (m.team1 if random.random() < 0.5 else m.team2)
                for m in self.matches]

    def results_display(self) -> None:
        """نتایج تمام مسابقات این مرحله را چاپ می‌کند."""
        print(f"===== {self.round_name} =====")
        for match in self.matches:
            result = (f"{match.team1.name} {match.goals1}-{match.goals2} "
                      f"({match.pen_score1}-{match.pen_score2} pens) {match.team2.name}"
                      if match.penalties else f"{match.team1.name} {match.goals1}-{match.goals2} {match.team2.name}")
            suffix = "تساوی" if match.winner is None else f"برنده: {match.winner.name}"
            print(f"{result} -> {suffix}")