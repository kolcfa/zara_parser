from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

# ----------------- Настройки -----------------
COUNTRIES = ["kz", "pt", "us", "fr", "it", "de", "es", "cn", "hk", "jp", "tr", "bg", "lt", "hu", "ee", "uk", "pl", "fi", "ae", "il"]
# , "pt", "us", "fr", "it", "de", "es", "cn", "hk", "jp", "tr", "bg", "lt", "hu", "ee", "in", "uk", "pl", "fi", "ae", "il", "by"
CHROMEDRIVER_PATH = r"C:\chromedriver\chromedriver.exe"

# Настройки Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")  # Без окна браузера
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--log-level=3")
chrome_options.add_argument("--blink-settings=imagesEnabled=false")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-plugins")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/143.0.7499.41 Safari/537.36"
)

# ----------------- Создание драйвера -----------------
try:
    driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=chrome_options)
    print("✅ ChromeDriver успешно запущен")
except Exception as e:
    print(f"❌ Не удалось запустить ChromeDriver: {e}")
    exit()

# ----------------- Ввод артикула -----------------
def get_article_from_user():
    while True:
        product_type = input("Введите тип (1 — обувь, 0 — верхняя одежда): ").strip()
        if product_type not in ("1", "0"):
            print("❌ Используйте 1 или 0.")
            continue

        article_number = input("Введите 7-значный артикул: ").strip()
        if not article_number.isdigit() or len(article_number) != 7:
            print("❌ Артикул должен состоять из 7 цифр.")
            continue

        full_article = product_type + article_number
        print(f"📝 Полный артикул: {full_article}")
        return full_article

# ----------------- Проверка товара -----------------
def check_availability(article):
    unavailable_keywords = ["notify me", "coming soon", "out of stock"]

    for country in COUNTRIES:
        url = f"https://www.zara.com/{country}/en/-p{article}.html"
        print(f"\n🌐 Проверка: {country.upper()}")
        print(f"URL: {url}")

        try:
            driver.get(url)
            print("✅ Страница загружена")
        except:
            print("❌ Ошибка загрузки URL")
            continue

        time.sleep(random.uniform(1, 2))

        # Проверка доступности товара
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            found_unavailable = None

            for btn in buttons:
                text = btn.text.replace("\n", " ").strip()
                if any(k in text.lower() for k in unavailable_keywords):
                    found_unavailable = text
                    break

            if found_unavailable:
                print(f"❌ Недоступно — {found_unavailable}")
                continue

            print("🛒 Товар доступен!")

        except:
            print("❌ Ошибка анализа кнопок")
            continue

        # ------------------ ПОИСК КНОПКИ ADD ------------------
        try:
            add_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[.//span[.='Add'] or normalize-space()='Add']")
                )
            )
            print("🔘 Найдена кнопка ADD")

            driver.execute_script("arguments[0].click();", add_button)
            time.sleep(1.5)

        except Exception as e:
            print("❌ Кнопка ADD не найдена:", e)
            continue

        # ------------------ ПОИСК ВСЕХ РАЗМЕРОВ + СТАТУСОВ ------------------
        try:
            size_items = driver.find_elements(
                By.CSS_SELECTOR,
                "li.size-selector-sizes__size"
            )

            if not size_items:
                print("⚠ Размеры не найдены")
            else:
                print("\n📏 Список размеров:")

                for item in size_items:
                    try:
                        # Размер
                        size = item.find_element(
                            By.CSS_SELECTOR,
                            ".size-selector-sizes-size__label"
                        ).text.strip()

                        # Статус
                        button = item.find_element(By.CSS_SELECTOR, "button")
                        status_attr = button.get_attribute("data-qa-action")

                        if status_attr == "size-in-stock":
                            status = "✅ В наличии"
                        elif status_attr == "size-out-of-stock":
                            status = "❌ Нет в наличии"
                        elif status_attr == "size-back-soon":
                            status = "⏳ Скоро появится"
                        elif status_attr == "size-low-on-stock":
                            status = "📉 Осталось мало"
                        else:
                            status = f"❔ {status_attr}"

                        print(f"— Размер {size}: {status}")

                    except Exception as e:
                        print("Ошибка чтения размера:", e)

        except Exception as e:
            print("❌ Ошибка получения размеров:", e)

# ----------------- Запуск -----------------
if __name__ == "__main__":
    ARTICLE = get_article_from_user()
    check_availability(ARTICLE)
    driver.quit()
    print("\n🛑 Скрипт завершён")
