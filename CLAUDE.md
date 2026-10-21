# wuwechnaya-bot

Telegram-бот и backend для парикмахерской: учёт расходников, история выполненных работ.
В планах: запись клиентов (две точки), уведомления о низком остатке, веб-панель отчётов.
Разработка на Mac, рабочий контур на Raspberry Pi 4 (k3s, ARM64). Общаться по-русски, коротко.

## Структура
- `backend/` — FastAPI, модульный монолит: `auth/`, `inventory/`, `worklog/`, плюс `db.py`, `main.py`
- `bot-gateway/` — aiogram 3, long-polling, входящих портов нет
- `deploy/` — k8s-манифесты `backend.yaml`, `bot-gateway.yaml`
- `.github/workflows/` — сборка образов `linux/arm64` в `ghcr.io/xxxaosss/{backend,bot-gateway}:latest`
- `web-admin/` — пока пусто; `backend/booking/` — пустая заготовка под запись (не в git)

## Стек
Python 3.12 (образы `python:3.12-slim`; `.python-version` в репо нет), отдельный venv в `backend/` и `bot-gateway/`.
Backend: FastAPI, SQLAlchemy async + asyncpg, Pydantic v2. Бот: aiogram 3, httpx.
БД: одна PostgreSQL (Helm bitnami), база `db_wu`, схемы `auth`, `inventory`, `worklog`.
Бот ходит в backend по HTTP (`BACKEND_URL=http://backend:8000`), в БД напрямую не ходит.

## Модель данных
- `auth.users`: telegram_id, username, role (`pending` / `master` / `admin`)
- `inventory.consumables`:
  - `unit` — `шт`, `мл` или `г`
  - `quantity` — остаток, ВСЕГДА в базовой единице
  - `pack_size` — нетто одной пачки (NULL: считается только в штуках)
  - `threshold` — порог «заканчивается», в базовых единицах
  - `tare` — вес пустой упаковки, только для учёта в `г`
- `inventory.consumable_incomings`, `inventory.consumable_usages` (`work_log_id` может быть NULL)
- `worklog.services`, `worklog.work_logs` (цена услуги и стоимость работы; цен расходников в системе нет)

## Правила кода
- Количества в backend — `Decimal(str(x))`. Float с Decimal не складывать (это уже ломало прод).
- Пересчёт штуки/мл/г и приход — только через `backend/inventory/units.py` (`to_base`, `receive_amount`, `reconfigure`).
  Списание (`quantity -= qty`) пишется в роутерах `/inventory/use` и `/worklog/complete`, но qty считается через `to_base`.
- Импорты в backend абсолютные (`from db import get_session`), относительные не использовать.
- Инструмента миграций нет, SQL выполняется вручную: `kubectl run pg-migrate ... psql "$DSN"`,
  DSN берётся из секрета `db-secrets` (убрать `+asyncpg`).
  Порядок: сначала миграция (добавляет nullable/default-колонки), потом деплой; удаление колонок после деплоя.
- Бот: числа, введённые пользователем в чате, — только через `fmt.parse_number`
  (исключение: ячейки файла импорта разбирает `to_float` в `import_handlers.py`); `callback_data` до 64 байт;
  лимиты Telegram: 100 кнопок на клавиатуру, 4096 символов в сообщении.
- Бот: порядок роутеров в `app.py` важен. `picker_router` подключается последним
  (он перехватывает любой текст в состояниях выбора), `edit_router` перед ним.
- Роли проверяются только в боте (`auth_helper.py`), `ADMIN_TELEGRAM_ID` всегда админ.
  У backend авторизации нет, наружу его не открывать.
- Секреты и `deploy/*.yaml` без явной просьбы не трогать.

## Проверка перед коммитом
```
python -m compileall -q -x '(venv|\.venv)' backend bot-gateway
cd bot-gateway && BOT_TOKEN=123456:TEST ADMIN_TELEGRAM_ID=1 python -c "import app"
```
Тестов пока нет. Для новой логики писать pytest, начиная с чистых функций.

## Деплой (Argo CD, автоматический)
1. Миграции БД (если есть) применить ДО пуша: деплой теперь идёт сам.
2. `git push`. GitHub Actions собирает образ (на push — только при изменениях в `backend/**` или `bot-gateway/**`;
   вручную — `workflow_dispatch`) с тегами `:latest` и `:<git sha>` и коммитит новый sha в `deploy/kustomization.yaml`
   (коммит `deploy: <сервис> <sha>`, перед следующей работой делать `git pull`).
3. Argo CD (Application `wuwechnaya-bot`, манифест `argocd/wuwechnaya-bot.yaml`) следит за `deploy/` ветки `main`
   и выкатывает сам (`automated`, `selfHeal`, `prune: false`).
4. Проверка: `kubectl get pods`, `kubectl logs -l app=bot-gateway --tail=30`, `kubectl -n argocd get applications`.

Ручной `rollout restart` больше не нужен; образы в кластере берутся по sha, а не `:latest`.
У bot-gateway `strategy: Recreate` (иначе два бота разом дают 409). Секреты в git не лежат и Argo их не ведёт.
Сервисы в namespace `default`. `imagePullPolicy: Always` явно задан только у bot-gateway.

## Секреты (не печатать, не коммитить, `.env` не читать)
k8s Secrets: `bot-secrets` (BOT_TOKEN, ADMIN_TELEGRAM_ID), `db-secrets` (DATABASE_URL), `ghcr-secret`.
Хост БД в DATABASE_URL — имя сервиса `postgres-postgresql`, а не 127.0.0.1.

## Ловушки, на которые уже наступали
- Telegram с Pi через туннель awg0 рвал около 30% соединений. Обход — systemd-юнит `telegram-direct-route`:
  маршрут `149.154.160.0/20` через `192.168.1.1` dev `wlan0`. Если в логах бота снова `Connection reset by peer`,
  проверить `ip route get 149.154.166.110` (должен быть `wlan0`).
- Два экземпляра бота одновременно (старый и новый под) дают TelegramConflictError 409 и CPU в потолок.
  После `rollout restart` убедиться, что остался один под.
- Бот падал с OOMKilled при лимите 128Mi. Сейчас 256Mi (и в `deploy/bot-gateway.yaml`, и в кластере), хватает.
- Образы только `linux/arm64`. Локальный запуск контейнера на Mac: `--platform linux/arm64`.

## Известные пробелы
Нет тестов. Нет авторизации в backend. `/worklog/complete` не идемпотентен.
Напоминания о низком остатке не реализованы. Тара используется только в приходе «вес с упаковкой».

## Решения
После архитектурного или продуктового решения дописывай запись в `docs/decisions.md`: что решили и почему.
Перед крупной правкой сверяйся с этим файлом.
