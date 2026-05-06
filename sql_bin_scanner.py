import pyodbc
import pypdf
import io
import keyring
import csv

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---

# 1. Достаем пароль из системы (программа его сама найдет по имени)
db_pass = keyring.get_password("sql_bin_scanner", "sa")

# 2. Проверяем, что пароль вообще нашелся
if db_pass is None:
    print("Ошибка: Пароль не найден в хранилище Windows!")
    exit()
    
# Если используете Windows-авторизацию (Trusted_Connection=yes)
conn_str = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=SISP-SQL\SISP_SQL_2021;'
    'DATABASE=SISP;'
    f'UID=sa;PWD={db_pass}'
)

# Если нужен логин/пароль, замените Trusted_Connection на:
# 'UID=ваш_логин;PWD=ваш_пароль;'

# --- ЧТО ИЩЕМ ---
KEYWORDS = [
' flash ', 
' eprom ', 
' eeprom ', 
' fram ', 
' feram ', 
' mram ', 
' nvram ', 
' nvsram '
] # Добавьте свои слова (в нижнем регистре)
TABLE_NAME = '[SISP].[dbo].[номинал_микросхемы]'
ID_COLUMN = '[key]'                         # Имя колонки с первичным ключом
INFO_COLUMN = '[номинал_микросхемы]'
BINARY_COLUMN = '[Datasheet_микросхемы]'    # Имя колонки, где лежат PDF

def start_search():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Запрос к базе данных...")
        cursor.execute(f"SELECT top 100 {INFO_COLUMN}, {BINARY_COLUMN} FROM {TABLE_NAME}")
        
        found_ids = []
        # Перед циклом обнуляем счетчики
        total_processed = 0
        found_count = 0
        
        print("Сканирование запущено. Нажмите Ctrl+C для прерывания.")
        
        print("Сканирую PDF в памяти...")
        for row in cursor:
            record_id = row[0]
            pdf_bytes = row[1]
            total_processed += 1
            
            # ВЫВОД ПРОГРЕССА (раз в 100 записей)
            if total_processed % 100 == 0:
                print(f">>> Обработано: {total_processed} | Найдено совпадений: {found_count}")
            
            if not pdf_bytes:
                continue
                
            try:
                # Читаем PDF без сохранения на диск
                reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                text = ""
                for page in reader.pages:
                    text += (page.extract_text() or "")
                
                text_lower = text.lower()
                if any(word.lower() in text_lower for word in KEYWORDS):
                    print(f"[+] Найдено в ID: {record_id}")
                    found_ids.append(str(record_id))
                    found_count += 1
                    
            except Exception as e:
                print(f"[!] Ошибка в записи {record_id}: {e}")

        # Сохраняем результат в файл
        with open("results_chips.csv", "w", newline='', encoding="utf-16") as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['Номинал микросхемы'])
                for item in found_ids:
                    writer.writerow([item])
        print(f"\nУспех! Файл results_chips.csv создан.")
            
       # print(f"\nГотово! Результаты сохранены в found_ids.txt")
        print(f"Всего найдено записей: {len(found_ids)}")
        print(f"Всего проверено: {total_processed}")
        print(f"Всего найдено: {found_count}")

    except Exception as e:
        print(f"Ошибка подключения к SQL: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    start_search()  