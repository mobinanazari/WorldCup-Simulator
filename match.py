"""ماژول شبیه‌سازی مسابقه."""

import random
from typing import Optional, Tuple

from team import Team
from utils import poisson_sample, SUDDEN_DEATH_MAX_ROUNDS

class Match:
    """یک مسابقه گروهی یا حذفی را شبیه‌سازی می‌کند.

    Attributes:
        team1 (Team): تیم اول.
        team2 (Team): تیم دوم.
        is_knockout (bool): وضعیت حذفی بودن مسابقه.
        goals1 (int): گل تیم اول در زمان قانونی.
        goals2 (int): گل تیم دوم در زمان قانونی.
        pen_score1 (int): گل پنالتی تیم اول.
        pen_score2 (int): گل پنالتی تیم دوم.
        winner (Optional[Team]): تیم برنده مسابقه.
        penalties (bool): آیا مسابقه به پنالتی کشیده شد یا خیر.
    """

    def __init__(self, team1: Team, team2: Team, is_knockout: bool = False) -> None:
        """سازنده کلاس Match.

        Args:
            team1 (Team): تیم میزبان یا اول.
            team2 (Team): تیم مهمان یا دوم.
            is_knockout (bool, optional): آیا بازی حذفی است؟ پیش‌فرض False.
        """
        self.team1, self.team2, self.is_knockout = team1, team2, is_knockout
        self.goals1 = self.goals2 = self.pen_score1 = self.pen_score2 = 0
        self.winner: Optional[Team] = None
        self.penalties = False

    def play(self) -> None:
        """مسابقه را اجرا کرده و آمار دو تیم را به‌روزرسانی می‌کند."""
        lam1, lam2 = self.team1._lambda_against(self.team2), self.team2._lambda_against(self.team1)
        self.goals1, self.goals2 = poisson_sample(lam1), poisson_sample(lam2)
        
        if self.is_knockout and self.goals1 == self.goals2:
            self.goals1 += poisson_sample(0.33 * lam1)
            self.goals2 += poisson_sample(0.33 * lam2)
            
        if self.is_knockout and self.goals1 == self.goals2:
            self.penalties = True
            self.pen_score1, self.pen_score2 = self._penalty_shootout()
            
        self.winner = (self.team1 if self.goals1 > self.goals2 else
                       self.team2 if self.goals2 > self.goals1 else
                       (self.team1 if self.pen_score1 > self.pen_score2 else self.team2) if self.penalties else None)
        
        self.team1.for_goals += self.goals1
        self.team1.against_goals += self.goals2
        self.team2.for_goals += self.goals2
        self.team2.against_goals += self.goals1
        
        if not self.is_knockout:
            if self.goals1 == self.goals2:
                self.team1.points += 1
                self.team2.points += 1
            else:
                (self.team1 if self.goals1 > self.goals2 else self.team2).points += 3

    def _penalty_shootout(self) -> Tuple[int, int]:
        """پنج پنالتی اولیه و سپس پنالتی‌های ناگهانی را اجرا می‌کند.

        Returns:
            Tuple[int, int]: (گل پنالتی تیم اول، گل پنالتی تیم دوم)
        """
        p1, p2 = self.team1.penalty_success_prob(self.team2), self.team2.penalty_success_prob(self.team1)
        score1 = score2 = 0
        
        for index in range(5):
            score1 += random.random() < p1
            score2 += random.random() < p2
            remaining = 4 - index
            if score1 > score2 + remaining or score2 > score1 + remaining:
                break
                
        if score1 == score2:
            for _ in range(SUDDEN_DEATH_MAX_ROUNDS):
                result1, result2 = random.random() < p1, random.random() < p2
                score1 += result1
                score2 += result2
                if result1 != result2:
                    break
            else:
                score1 += random.random() < 0.5
                score2 += score1 == score2
        return score1, score2