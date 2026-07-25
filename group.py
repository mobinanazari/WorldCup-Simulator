"""ماژول مدیریت مرحله گروهی."""

import random
from collections import defaultdict
from itertools import combinations, groupby
from typing import Dict, List, Tuple

from match import Match
from team import Team

class Group:
    """مسابقات و رتبه‌بندی یک گروه چهار تیمی را مدیریت می‌کند.

    Attributes:
        name (str): نام گروه (مثل A, B).
        teams (List[Team]): لیست تیم‌های گروه.
        matches (List[Match]): لیست بازی‌های انجام شده در گروه.
    """

    def __init__(self, name: str, teams: List[Team]) -> None:
        """سازنده کلاس Group.

        Args:
            name (str): نام گروه.
            teams (List[Team]): لیست ۴ تیم گروه.
        """
        self.name, self.teams, self.matches = name, list(teams), []
        self._h2h_points: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def matches_all_play(self) -> None:
        """شش بازی گروه را اجرا می‌کند و نتایج رودررو را ثبت می‌کند."""
        self.matches.clear()
        self._h2h_points.clear()
        for team1, team2 in combinations(self.teams, 2):
            match = Match(team1, team2)
            match.play()
            self.matches.append(match)
            self._record_h2h(match)

    def _record_h2h(self, match: Match) -> None:
        """امتیاز بازی مستقیم را برای شکستن تساوی ذخیره می‌کند.

        Args:
            match (Match): مسابقه انجام شده بین دو تیم.
        """
        a, b = match.team1.name, match.team2.name
        points = (3, 0) if match.goals1 > match.goals2 else ((0, 3) if match.goals2 > match.goals1 else (1, 1))
        table = self._h2h_points[tuple(sorted((a, b)))]
        table[a], table[b] = table[a] + points[0], table[b] + points[1]

    def _h2h_score(self, team: Team, peers: List[Team]) -> int:
        """امتیاز رودررو تیم را مقابل تیم‌های کاملاً مساوی محاسبه می‌کند.

        Args:
            team (Team): تیم مورد نظر.
            peers (List[Team]): تیم‌هایی که در رتبه‌بندی امتیاز برابر دارند.

        Returns:
            int: مجموع امتیازات بازی‌های مستقیم.
        """
        return sum(self._h2h_points.get(tuple(sorted((team.name, other.name))), {}).get(team.name, 0)
                   for other in peers if other.name != team.name)

    def ranking_get(self) -> List[Team]:
        """جدول گروه را بر اساس امتیاز، تفاضل گل، گل زده و بازی مستقیم رتبه‌بندی می‌کند.

        Returns:
            List[Team]: لیست تیم‌ها به ترتیب رتبه یک تا چهار.
        """
        teams = list(self.teams)
        random.shuffle(teams)
        key = lambda t: (t.points, t.goal_difference(), t.for_goals)
        teams.sort(key=key, reverse=True)
        
        ranked = []
        for _, tied in groupby(teams, key):
            block = list(tied)
            if len(block) > 1:
                block.sort(key=lambda t: (self._h2h_score(t, block), random.random()), reverse=True)
            ranked.extend(block)
        return ranked

    def advance_teams(self) -> List[Team]:
        """دو تیم اول گروه را برمی‌گرداند.

        Returns:
            List[Team]: لیست دو تیم صعودکننده.
        """
        return self.ranking_get()[:2]

    def display_table(self) -> None:
        """جدول رتبه‌بندی گروه را چاپ می‌کند."""
        print(f"===== Group {self.name} =====")
        for index, team in enumerate(self.ranking_get(), 1):
            difference = team.goal_difference()
            print(f"{index}. {team.name}: {team.points} pts, GD {f'+{difference}' if difference > 0 else difference}, GF {team.for_goals}")