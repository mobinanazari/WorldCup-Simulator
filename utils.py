"""ماژول ابزارهای عمومی شامل ثابت‌ها، رنگ‌ها و توابع کمکی ریاضی."""

import math
import random

# ثابت‌های اصلی برنامه و نام پیش‌فرض فایل داده‌ها
SUDDEN_DEATH_MAX_ROUNDS = 50
DEFAULT_CSV = "teams_2026_worldcup.csv"
FALLBACK_CSV = "worldcup_2026_teams.txt"


class Colors:
    """کدهای ANSI برای رنگی‌سازی خروجی ترمینال.
    
    Attributes:
        RESET (str): کد ریست کردن رنگ.
        BOLD (str): کد متن بولد.
        RED (str): کد رنگ قرمز.
        GREEN (str): کد رنگ سبز.
        YELLOW (str): کد رنگ زرد.
        BLUE (str): کد رنگ آبی.
        MAGENTA (str): کد رنگ ارغوانی.
        CYAN (str): کد رنگ فیروزه‌ای.
        GRAY (str): کد رنگ خاکستری.
    """
    RESET, BOLD = "\033[0m", "\033[1m"
    RED, GREEN, YELLOW, BLUE = "\033[91m", "\033[92m", "\033[93m", "\033[94m"
    MAGENTA, CYAN, GRAY = "\033[95m", "\033[96m", "\033[90m"

    @staticmethod
    def wrap(text: str, color: str) -> str:
        """متن رنگی می‌سازد.

        Args:
            text (str): متنی که باید رنگی شود.
            color (str): کد رنگ مورد نظر از کلاس Colors.

        Returns:
            str: متن رنگی شده با کدهای ANSI.
        """
        return f"{color}{text}{Colors.RESET}"


def poisson_sample(lam: float) -> int:
    """یک عدد تصادفی از توزیع پواسون با روش Knuth تولید می‌کند.

    Args:
        lam (float): پارامتر lambda (میانگین مورد انتظار).

    Returns:
        int: عدد تصادفی تولید شده.
    """
    if lam <= 0:
        return 0
    if lam > 100:
        return max(0, int(round(random.gauss(lam, math.sqrt(lam)))))
    limit, count, product = math.exp(-lam), 0, 1.0
    while product > limit:
        count += 1
        product *= random.random()
    return count - 1