import re
import os
import sys

def parse_html_file(html_file_path, output_file_path):
    """
    Парсит HTML-файл, находит все уникальные элементы, начинающиеся с "/@" и заканчивающиеся "/",
    извлекает часть после "/" и перед "/", и сохраняет результат в текстовый файл.
    
    Args:
        html_file_path (str): Путь к HTML-файлу
        output_file_path (str): Путь к выходному текстовому файлу
    """
    try:
        # Читаем HTML-файл
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Используем регулярное выражение для поиска всех элементов "/@.../"
        pattern = r'/(@[^/]+)/'
        matches = re.findall(pattern, html_content)
        
        # Получаем уникальные элементы и сортируем их
        unique_elements = sorted(set(matches))
        
        # Записываем уникальные элементы в текстовый файл
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            for element in unique_elements:
                output_file.write(f"{element}\n")
        
        print(f"Найдено {len(unique_elements)} уникальных элементов в файле {os.path.basename(html_file_path)}. "
              f"Результат сохранен в {output_file_path}.")
        
        return len(unique_elements)
    except Exception as e:
        print(f"Ошибка при обработке файла {html_file_path}: {e}")
        return 0

def aggregate_results(results_folder, output_file_path):
    """
    Собирает все уникальные юзернеймы из текстовых файлов в папке результатов
    и сохраняет их в общий файл.
    
    Args:
        results_folder (str): Путь к папке с результатами парсинга
        output_file_path (str): Путь к выходному общему файлу
    """
    try:
        # Собираем все уникальные юзернеймы
        all_usernames = set()
        
        # Получаем список текстовых файлов в папке результатов
        result_files = [f for f in os.listdir(results_folder) if f.endswith('.txt') and f != "Results.txt"]
        
        if not result_files:
            print(f"В папке {results_folder} не найдено текстовых файлов с результатами.")
            return 0
        
        # Читаем каждый файл и добавляем юзернеймы в общее множество
        for result_file in result_files:
            file_path = os.path.join(results_folder, result_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    usernames = [line.strip() for line in file if line.strip()]
                    all_usernames.update(usernames)
            except Exception as e:
                print(f"Ошибка при чтении файла {file_path}: {e}")
        
        # Сортируем и записываем все уникальные юзернеймы в общий файл
        sorted_usernames = sorted(all_usernames)
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            for username in sorted_usernames:
                output_file.write(f"{username}\n")
        
        print(f"\nСобрано {len(sorted_usernames)} уникальных юзернеймов из {len(result_files)} файлов. "
              f"Результат сохранен в {output_file_path}.")
        
        return len(sorted_usernames)
    except Exception as e:
        print(f"Ошибка при агрегации результатов: {e}")
        return 0

def main():
    # Определяем пути к папкам
    html_folder = "Html"
    results_folder = "Results"
    aggregate_file = os.path.join(results_folder, "Results.txt")
    
    # Проверяем существование папки с HTML файлами
    if not os.path.exists(html_folder):
        print(f"Папка {html_folder} не существует.")
        return
    
    if not os.path.isdir(html_folder):
        print(f"{html_folder} не является папкой.")
        return
    
    # Создаем папку Results, если она не существует
    if not os.path.exists(results_folder):
        os.makedirs(results_folder)
        print(f"Создана папка {results_folder}")
    
    # Получаем список HTML файлов
    html_files = [f for f in os.listdir(html_folder) if f.lower().endswith(('.html', '.htm'))]
    
    if not html_files:
        print(f"В папке {html_folder} не найдено HTML-файлов.")
        return
    
    total_processed = 0
    total_elements = 0
    
    # Обрабатываем каждый HTML-файл
    for html_file in html_files:
        input_path = os.path.join(html_folder, html_file)
        
        # Создаем имя выходного файла на основе имени входного файла
        output_file_name = os.path.splitext(html_file)[0] + ".txt"
        output_path = os.path.join(results_folder, output_file_name)
        
        # Парсим файл и записываем результаты
        elements_count = parse_html_file(input_path, output_path)
        
        if elements_count > 0:
            total_processed += 1
            total_elements += elements_count
    
    print(f"\nОбработка HTML-файлов завершена. Обработано файлов: {total_processed}/{len(html_files)}")
    print(f"Общее количество найденных уникальных элементов: {total_elements}")
    
    # Агрегируем результаты из всех файлов в общий файл
    print("\nНачинаем агрегацию результатов...")
    unique_count = aggregate_results(results_folder, aggregate_file)
    
    if unique_count > 0:
        print(f"\nРабота парсера успешно завершена!")
        print(f"Итоговый результат сохранен в {aggregate_file}")

if __name__ == "__main__":
    main()