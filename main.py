"""فایل اجرایی اصلی (Entry Point) و رابط کاربری شبیه‌ساز جام جهانی."""

from utils import Colors, DEFAULT_CSV
from world_cup_simulator import WorldCupSimulator

def print_menu() -> None:
    """منوی اصلی برنامه را نمایش می‌دهد."""
    print()
    print(Colors.wrap("=====شبیه ساز جام جهانی=====", Colors.BOLD + Colors.CYAN))
    print("\n".join(("1) بارگذاری تیمها از فایلCSV", "2) انجام قرعهکشی گروهها (سیدبندی خودکار)", "3) اجرای مرحله گروهی و نمایش جدول هر گروه",
          "4) اجرای کامل جام (گروهی + حذفی) و نمایش قهرمان", "5) شبیه سازی ۱۰۰۰ باره و گزارش درصد قهرمانی",
          "6) نمایش براکت حذفی آخرین شبیه سازی", "7) خروج")))


def ask_int(prompt: str, default: int = None) -> int:
    """ورودی عدد صحیح را با مقدار پیش‌فرض و مدیریت خطا دریافت می‌کند.

    Args:
        prompt (str): پیام نمایش داده شده به کاربر.
        default (int, optional): مقدار پیش‌فرض در صورت ورود خالی.

    Returns:
        int: عدد وارد شده توسط کاربر یا مقدار پیش‌فرض.
    """
    raw = input(prompt).strip()
    if raw == "" and default is not None:
        return default
    try:
        return int(raw)
    except ValueError:
        print(Colors.wrap("ورودی نامعتبر است؛ عدد وارد کنید.", Colors.RED))
        return None


def main() -> None:
    """حلقه اصلی منو و ارتباط کاربر با شبیه‌ساز را اجرا می‌کند."""
    simulator = WorldCupSimulator()
    while True:
        print_menu()
        choice = input("انتخاب شما: ").strip()
        if choice == "1":
            path = input(f"نام فایل CSV [{DEFAULT_CSV}]: ").strip() or DEFAULT_CSV
            simulator.load_teams_from_csv(path)
        elif choice in ("2", "3", "6"):
            {"2": simulator.groups_draw_and_seed, "3": simulator.stage_group_run, "6": simulator.bracket_display}[choice]()
        elif choice == "4":
            if not simulator.teams:
                print(Colors.wrap("ابتدا تیم‌ها را بارگذاری کنید (گزینه ۱).", Colors.YELLOW))
            elif not simulator._drawn:
                print(Colors.wrap("ابتدا قرعه‌کشی را انجام دهید (گزینه ۲).", Colors.YELLOW))
            else:
                simulator.simulation_full_run(verbose=True)
        elif choice == "5":
            if not simulator.teams:
                print(Colors.wrap("ابتدا تیم‌ها را بارگذاری کنید (گزینه ۱).", Colors.YELLOW))
                continue
            if (count := ask_int("تعداد شبیه‌سازی [1000]: ", 1000)) is None:
                continue
            if count <= 0:
                print(Colors.wrap("تعداد باید مثبت باشد.", Colors.RED))
                continue
            seed = input("seed تصادفی (Enter = بدون seed ثابت): ").strip()
            if seed:
                try:
                    import random
                    random.seed(int(seed))
                    print(Colors.wrap(f"seed={seed} تنظیم شد.", Colors.GRAY))
                except ValueError:
                    print(Colors.wrap("seed نامعتبر نادیده گرفته شد.", Colors.YELLOW))
            simulator.champion_likely_most(count)
        elif choice == "7":
            print(Colors.wrap("خروج از برنامه. موفق باشید!", Colors.GREEN))
            break
        else:
            print(Colors.wrap("گزینه نامعتبر است (۱ تا ۷).", Colors.RED))


if __name__ == "__main__":
    main()