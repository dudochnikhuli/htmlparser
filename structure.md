project/
│
├── Html/                   # Папка с HTML-файлами для парсинга
│
├── Results/                # Папка с результатами
│   ├── Results.txt         # Список юзернеймов каналов для анализа
│   ├── Table.csv           # Выходной CSV-файл с собранными данными
│   ├── progress.json       # Файл для сохранения прогресса
│   ├── AI.txt              # Категоризированные списки юзернеймов
│   ├── Data Science.txt    # Категоризированные списки юзернеймов
│   └── ИИ.txt              # Категоризированные списки юзернеймов
│
├── sessions/               # Папка с сессиями Telegram
│   ├── sessions_info.json  # Информация о созданных сессиях
│   ├── session_1.session   # Файлы сессий Telegram
│   └── ...                 # Дополнительные файлы сессий
│
├── TG_parser.py            # Основной скрипт для анализа Telegram-каналов
├── create_sessions.py      # Скрипт для создания сессий Telegram
├── html_parser.py          # Скрипт для извлечения юзернеймов из HTML-файлов
├── .env                    # Файл с API-учетными данными
├── .env.example            # Пример файла с API-учетными данными
├── README.md               # Документация проекта
├── structure.md            # Описание структуры проекта (этот файл)
└── requirements.txt        # Список зависимостей