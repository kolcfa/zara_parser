from playwright.sync_api import sync_playwright
import time

# ----------------- НАСТРОЙКИ -----------------
COUNTRY = "kz"
LANG = "en"
HEADLESS = False
CITY_SEARCH = "Almaty"  # город/улица для поиска

# ----------------- ВВОД АРТИКУЛА -----------------
def get_article_from_user():
    while True:
        product_type = input("Введите тип (1 — обувь, 0 — одежда): ").strip()
        if product_type not in ("0", "1"):
            print("❌ Используйте 0 или 1")
            continue

        article_number = input("Введите 7-значный артикул: ").strip()
        if not article_number.isdigit() or len(article_number) != 7:
            print("❌ Артикул должен быть из 7 цифр")
            continue

        article = product_type + article_number
        print(f"📝 Полный артикул: {article}")
        return article

# ----------------- ПРОВЕРКА НАЛИЧИЯ В МАГАЗИНАХ -----------------
def check_store_stock(article):
    url = f"https://www.zara.com/{COUNTRY}/{LANG}/-p{article}.html"
    print(f"\n🌐 Открываю: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        store_stock_data = []

        # Ловим запросы store-stock
        def handle_store_stock_response(response):
            if "store-stock" in response.url:
                try:
                    data = response.json()
                    store_stock_data.append(data)
                except:
                    pass

        page.on("response", handle_store_stock_response)

        page.goto(url, timeout=60000)

        # ----------------- ШАГ 1: Нажимаем Check in-store availability -----------------
        try:
            page.click("button[data-qa-action='store-stock']", timeout=5000)
            print("🔘 Нажата кнопка Check in-store availability")
        except:
            print("⚠ Не удалось нажать Check in-store availability")

        # ----------------- ШАГ 2: Выбираем ONE SIZE ONLY -----------------
        try:
            page.click("label.multi-size-selector__size", timeout=5000)
            print("✅ Выбран размер: ONE SIZE ONLY")
        except:
            print("⚠ Не удалось выбрать ONE SIZE ONLY")

        # ----------------- ШАГ 3: Нажимаем CHECK AVAILABILITY -----------------
        try:
            page.click("button.product-stock-availability-size-selector-form__button", timeout=5000)
            print("🔘 Нажата кнопка CHECK AVAILABILITY")
        except:
            print("⚠ Не удалось нажать CHECK AVAILABILITY")

        # ----------------- ШАГ 4: Ввод города и поиск -----------------
        try:
            page.fill("input#search90", CITY_SEARCH)
            page.click("button[data-qa-action='search-physical-stores']")
            print(f"🔍 Введен город '{CITY_SEARCH}' и выполнен поиск")
        except:
            print("⚠ Не удалось ввести город/выполнить поиск")

        # Ждем, чтобы запрос store-stock успел выполниться
        time.sleep(5)
        browser.close()

        if not store_stock_data:
            print("❌ Данные store-stock не получены")
            return

        print("\n📦 НАЛИЧИЕ В МАГАЗИНАХ (KZ):")
        for block in store_stock_data:
            for store in block.get("stores", []):
                store_id = store.get("physicalStoreId")
                print(f"\n🏬 Магазин ID: {store_id}")

                for item in store.get("availability", []):
                    size = item.get("size", "—")
                    available = item.get("available", False)
                    qty = item.get("quantity")

                    status = "✅ В наличии" if available else "❌ Нет"
                    qty_text = f"({qty} шт.)" if qty else ""
                    print(f"  — Размер {size}: {status} {qty_text}")

# ----------------- ЗАПУСК -----------------
if __name__ == "__main__":
    ARTICLE = get_article_from_user()
    check_store_stock(ARTICLE)
    print("\n🛑 Проверка завершена")
