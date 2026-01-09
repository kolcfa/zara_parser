import random
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys

# ----------------- Настройки -----------------
CHROMEDRIVER_PATH = r"C:\chromedriver\chromedriver.exe"

COUNTRIES = [
    "kz", "pt", "us", "fr", "it", "de", "es", "cn", "hk", "jp",
    "tr", "bg", "lt", "hu", "ee", "uk", "pl", "fi", "ae", "il"
]

UNAVAILABLE_KEYWORDS = ["notify me", "coming soon", "out of stock"]


def build_driver(headless: bool) -> webdriver.Chrome:
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")

    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/143.0.7499.42 Safari/537.36"
    )

    return webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=chrome_options)


def ask_product_type() -> str:
    while True:
        t = input("Введите тип товара (0 - верхняя одежда или 1 - обувь и аксессуары): ").strip()
        if t in ("0", "1"):
            return t
        print("Ошибка: тип должен быть 0 или 1.")


def ask_article_number() -> str:
    while True:
        a = input("Введите 7-значный артикул (только цифры): ").strip()
        if re.fullmatch(r"\d{7}", a):
            return a
        print("Ошибка: артикул должен состоять ровно из 7 цифр.")


def ask_countries() -> list[str]:
    print("\nДоступные страны:")
    print(", ".join(COUNTRIES))
    s = input("Введите страны через запятую (например: kz,us,fr) или Enter = все: ").strip().lower()

    if not s:
        return COUNTRIES[:]

    parts = [c.strip() for c in s.split(",") if c.strip()]
    unknown = [c for c in parts if c not in COUNTRIES]
    if unknown:
        print(f"Неизвестные страны: {', '.join(unknown)}")
        print("Повторите ввод.")
        return ask_countries()

    seen = set()
    out = []
    for c in parts:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def ask_headless() -> bool:
    while True:
        s = input("Запускать headless? (Y/n): ").strip().lower()
        if s in ("", "y", "yes", "да", "д"):
            return True
        if s in ("n", "no", "нет", "н"):
            return False
        print("Введите Y или N (или просто Enter).")


def try_close_overlays(driver: webdriver.Chrome):
    # OneTrust / cookies accept
    try:
        driver.execute_script("""
            const b = document.querySelector('#onetrust-accept-btn-handler');
            if (b) b.click();
        """)
    except Exception:
        pass

    # ESC иногда закрывает модалки
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except Exception:
        pass


def get_button_texts_js(driver: webdriver.Chrome) -> list[str]:
    return driver.execute_script("""
        return Array.from(document.querySelectorAll('button'))
            .map(b => (b.innerText || '').replace(/\\n/g,' ').trim())
            .filter(t => t.length > 0);
    """)


def wait_for_sizes_any(driver: webdriver.Chrome, timeout: int = 18):
    """
    Ждём любые варианты рендера размеров:
    1 li.size-selector-sizes__size (старый/частый вариант)
    2 кнопки размеров по data-qa-action^="size-" (часто в CN/новых раскладках)
    """
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("""
            const a = document.querySelectorAll('li.size-selector-sizes__size').length;
            const b = document.querySelectorAll('button[data-qa-action^="size-"]').length;
            const c = document.querySelectorAll('[data-qa-action^="size-"]').length;
            return (a > 0) || (b > 0) || (c > 0);
        """)
    )


def get_sizes_js(driver: webdriver.Chrome) -> list[tuple[str, str]]:
    """
    Универсальный снимок размеров:
    - сначала пробуем стандартные li.size-selector-sizes__size
    - если их нет, берём кнопки с data-qa-action^="size-" и читаем текст
    """
    data = driver.execute_script("""
        // 1 основной вариант
        let items = Array.from(document.querySelectorAll('li.size-selector-sizes__size'));
        if (items.length) {
            return items.map(li => {
                const label =
                    li.querySelector('.size-selector-sizes-size__label')?.innerText?.trim()
                    || (li.innerText || '').trim().split('\\n')[0].trim()
                    || '';
                const btn = li.querySelector('button');
                const status = btn?.getAttribute('data-qa-action') || '';
                return [label, status];
            });
        }

        // 2 fallback: любые size-кнопки по data-qa-action
        const btns = Array.from(document.querySelectorAll('button[data-qa-action^="size-"], [data-qa-action^="size-"]'))
            .filter(el => el.tagName.toLowerCase() === 'button' || el.getAttribute('role') === 'button');

        return btns.map(b => {
            const status = b.getAttribute('data-qa-action') || '';
            const label = (b.innerText || '').replace(/\\n/g,' ').trim();
            return [label, status];
        });
    """)

    return [(a, b) for a, b in data]


def click_add(driver: webdriver.Chrome) -> bool:
    try:
        add_button = WebDriverWait(driver, 12).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[normalize-space()='Add'] or normalize-space()='Add']")
            )
        )
        driver.execute_script("arguments[0].click();", add_button)
        return True
    except TimeoutException:
        return False
    except Exception:
        return False


def check_availability(driver: webdriver.Chrome, product_type: str, article_number: str, countries: list[str]):
    article = product_type + article_number

    for country in countries:
        url = f"https://www.zara.com/{country}/en/-p{article}.html"

        print("\n" + "=" * 70)
        print(f"Проверка: {country.upper()}")
        print(f"URL: {url}")

        # 1 Открыть страницу
        try:
            driver.get(url)
            WebDriverWait(driver, 18).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            print("Страница загружена")
        except Exception as e:
            print(f"Ошибка загрузки URL: {e}")
            continue

        time.sleep(random.uniform(1.0, 2.0))
        try_close_overlays(driver)

        # 2 Проверка доступности по кнопкам (устойчиво)
        try:
            button_texts = get_button_texts_js(driver)
            found_unavailable = next(
                (t for t in button_texts if any(k in t.lower() for k in UNAVAILABLE_KEYWORDS)),
                None
            )

            if found_unavailable:
                print(f"❌ Недоступно — {found_unavailable}")
                continue

            print("Явных 'notify me/coming soon/out of stock' не найдено")
        except Exception as e:
            print(f"❌ Ошибка анализа кнопок: {e}")
            continue

        # 3 ADD
        add_clicked = click_add(driver)
        if add_clicked:
            print("Кнопка ADD найдена и нажата")
            time.sleep(random.uniform(1.0, 1.8))
        else:
            print("⚠ Кнопка ADD не найдена/не кликабельна")

        # 4 Размеры (CN иногда требует чуть больше ожидания и/или повторный клик ADD)
        got_sizes = False
        for attempt in range(2):
            try:
                wait_for_sizes_any(driver, timeout=22 if country in ("cn", "hk") else 16)
                size_data = get_sizes_js(driver)

                if not size_data:
                    raise TimeoutException("size_data empty")

                print("📏 Список размеров:")
                for size, status_attr in size_data:
                    status_attr = (status_attr or "").strip()

                    if status_attr == "size-in-stock":
                        status = "✅ В наличии"
                    elif status_attr == "size-out-of-stock":
                        status = "❌ Нет в наличии"
                    elif status_attr == "size-back-soon":
                        status = "⏳ Скоро появится"
                    elif status_attr == "size-low-on-stock":
                        status = "📉 Осталось мало"
                    else:
                        status = f"❔ {status_attr or 'unknown'}"

                    print(f"— Размер {size or '?'}: {status}")

                got_sizes = True
                break

            except TimeoutException:
                if attempt == 0:
                    # повторный клик — часто помогает на CN
                    print("↻ Размеры не появились, пробую повторный клик ADD...")
                    try_close_overlays(driver)
                    _ = click_add(driver)
                    time.sleep(random.uniform(1.0, 2.0))
                else:
                    if add_clicked:
                        print("⚠ Размеры не появились (timeout) после клика ADD")
                    else:
                        print("⚠ Размеры не появились (timeout)")
            except Exception as e:
                print(f"❌ Ошибка получения размеров: {e}")
                break

        if not got_sizes:
            # иногда Zara рисует размеры внутри другого контейнера,
            # но хотя бы дадим подсказку, что парсер не увидел их в DOM
            pass


def main():
    print("Zara Availability Checker (console)\n")

    product_type = ask_product_type()
    article_number = ask_article_number()
    countries = ask_countries()
    headless = ask_headless()

    driver = build_driver(headless=headless)
    try:
        check_availability(driver, product_type, article_number, countries)
    finally:
        driver.quit()
        print("\nГотово. Драйвер закрыт.")


if __name__ == "__main__":
    main()
