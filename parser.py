import tkinter as tk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

# ----------------- Настройки Chrome -----------------
CHROMEDRIVER_PATH = r"C:\chromedriver\chromedriver.exe"
chrome_options = Options()
chrome_options.add_argument("--headless")  # Без окна браузера, можно убрать для теста
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

# ----------------- Создание драйвера -----------------
driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=chrome_options)

# ----------------- Список стран -----------------
COUNTRIES = ["kz", "pt", "us", "fr", "it", "de", "es", "cn", "hk", "jp", "tr", "bg", "lt", "hu", "ee", "uk", "pl", "fi", "ae", "il"]

# ----------------- Функция проверки -----------------
def check_availability_gui():
    product_type = type_var.get()
    if product_type not in ("0", "1"):
        messagebox.showerror("Ошибка", "Выберите тип товара (0 или 1)")
        return

    article_number = entry_article.get().strip()
    if not article_number.isdigit() or len(article_number) != 7:
        messagebox.showerror("Ошибка", "Артикул должен состоять из 7 цифр")
        return

    article = product_type + article_number  # Формируем полный артикул
    selected_indices = listbox_countries.curselection()
    if not selected_indices:
        messagebox.showerror("Ошибка", "Выберите хотя бы одну страну")
        return

    selected_countries = [COUNTRIES[i] for i in selected_indices]
    unavailable_keywords = ["notify me", "coming soon", "out of stock"]

    text_output.delete(1.0, tk.END)

    for country in selected_countries:
        url = f"https://www.zara.com/{country}/en/-p{article}.html"
        text_output.insert(tk.END, f"\n🌐 Проверка: {country.upper()}\nURL: {url}\n")

        try:
            driver.get(url)
            text_output.insert(tk.END, "✅ Страница загружена\n")
        except:
            text_output.insert(tk.END, "❌ Ошибка загрузки URL\n")
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
                text_output.insert(tk.END, f"❌ Недоступно — {found_unavailable}\n")
                continue

            text_output.insert(tk.END, "🛒 Товар доступен!\n")

        except:
            text_output.insert(tk.END, "❌ Ошибка анализа кнопок\n")
            continue

        # ------------------ Поиск кнопки ADD ------------------
        try:
            add_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[.//span[.='Add'] or normalize-space()='Add']")
                )
            )
            text_output.insert(tk.END, "🔘 Найдена кнопка ADD\n")
            driver.execute_script("arguments[0].click();", add_button)
            time.sleep(1.5)
        except Exception as e:
            text_output.insert(tk.END, f"❌ Кнопка ADD не найдена: {e}\n")

        # ------------------ Список размеров ------------------
        try:
            size_items = driver.find_elements(By.CSS_SELECTOR, "li.size-selector-sizes__size")
            if not size_items:
                text_output.insert(tk.END, "⚠ Размеры не найдены\n")
            else:
                text_output.insert(tk.END, "\n📏 Список размеров:\n")
                for item in size_items:
                    try:
                        size = item.find_element(By.CSS_SELECTOR, ".size-selector-sizes-size__label").text.strip()
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

                        text_output.insert(tk.END, f"— Размер {size}: {status}\n")

                    except Exception as e:
                        text_output.insert(tk.END, f"Ошибка чтения размера: {e}\n")

        except Exception as e:
            text_output.insert(tk.END, f"❌ Ошибка получения размеров: {e}\n")


# ----------------- Выбрать / снять все страны -----------------
def toggle_select_all():
    current_selection = listbox_countries.curselection()
    if len(current_selection) == len(COUNTRIES):
        listbox_countries.selection_clear(0, tk.END)
    else:
        listbox_countries.selection_set(0, tk.END)


# ----------------- GUI -----------------
window = tk.Tk()
window.title("Zara Availability Checker")
window.geometry("600x600")

# Выбор типа товара
tk.Label(window, text="Выберите тип товара").pack(pady=5)
type_var = tk.StringVar(value="0")
frame_type = tk.Frame(window)
frame_type.pack()
tk.Radiobutton(frame_type, text="0 — верхняя одежда", variable=type_var, value="0").pack(side=tk.LEFT, padx=5)
tk.Radiobutton(frame_type, text="1 — обувь и аксессуары", variable=type_var, value="1").pack(side=tk.LEFT, padx=5)

# Ввод артикула
tk.Label(window, text="Введите 7-значный артикул").pack(pady=5)
entry_article = tk.Entry(window, width=20)
entry_article.pack()

# Выбор стран
tk.Label(window, text="Выберите страны").pack(pady=5)
frame_list = tk.Frame(window)
frame_list.pack()
listbox_countries = tk.Listbox(frame_list, selectmode=tk.MULTIPLE, height=10)
for c in COUNTRIES:
    listbox_countries.insert(tk.END, c)
listbox_countries.pack(side=tk.LEFT)
scrollbar = tk.Scrollbar(frame_list, orient=tk.VERTICAL)
scrollbar.config(command=listbox_countries.yview)
listbox_countries.config(yscrollcommand=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

btn_select_all = tk.Button(window, text="Выбрать / Снять все", command=toggle_select_all)
btn_select_all.pack(pady=5)

btn_check = tk.Button(window, text="Проверить наличие", command=check_availability_gui)
btn_check.pack(pady=10)

text_output = tk.Text(window, height=20, wrap=tk.WORD)
text_output.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

window.mainloop()
driver.quit()
