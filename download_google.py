import subprocess
import re

# Открываем файл to_download.txt и читаем ссылки
with open('to_download.txt', 'r') as file:
    links = file.readlines()

# Обрабатываем каждую ссылку
for link in links:
    link = link.strip()  # Убираем пробелы и символы переноса строки
    if not link:  # Пропускаем пустые строки
        continue

    # Извлекаем ID папки из ссылки с помощью регулярного выражения
    folder_id_match = re.search(r'folders/([a-zA-Z0-9_-]+)', link)
    if folder_id_match:
        folder_id = folder_id_match.group(1)  # Получаем ID папки
        download_link = f'https://drive.google.com/drive/folders/{folder_id}'  # Формируем чистую ссылку

        # Пытаемся скачать папку
        try:
            subprocess.run(['gdown', '--folder', download_link], check=True)
            print(f"Успешно скачана папка по ссылке: {download_link}")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при скачивании {download_link}: {e}")
    else:
        print(f"Неверная ссылка: {link}")