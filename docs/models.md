# Модели базы данных

В этом разделе описаны все модели базы данных, используемые в проекте. Каждая модель представляет собой таблицу в базе данных и содержит поля, связи и методы.

---

## 1. **User (Пользователь)**

Модель `User` представляет пользователя системы. Каждый пользователь может быть членом команды, решать задачи, создавать инциденты и участвовать в критических событиях.

### Поля:
- **id** (`Integer`, Primary Key): Уникальный идентификатор пользователя.
- **username** (`String`, Unique, Not Null): Имя пользователя.
- **email** (`String`, Unique, Not Null): Электронная почта пользователя.
- **password_hash** (`String`, Not Null): Хэш пароля пользователя.
- **is_admin** (`Boolean`, Default=False): Флаг, указывающий, является ли пользователь администратором.
- **team_id** (`Integer`, ForeignKey('team.id'), Nullable): Идентификатор команды, к которой принадлежит пользователь.
- **total_points** (`Integer`, Default=0): Общее количество баллов пользователя.

### Связи:
- **team**: Связь с моделью `Team` (команда, к которой принадлежит пользователь).
- **created_incidents**: Список инцидентов, созданных пользователем.
- **reviewed_incidents**: Список инцидентов, проверенных пользователем (если он администратор).
- **critical_event_responses**: Список ответов на критические события, созданных пользователем.
- **created_events**: Список критических событий, созданных пользователем (если он администратор).

---

## 2. **Team (Команда)**

Модель `Team` представляет команду пользователей. Команды могут участвовать в решении задач, инцидентов и критических событий.

### Поля:
- **id** (`Integer`, Primary Key): Уникальный идентификатор команды.
- **name** (`String`, Unique, Not Null): Название команды.

### Связи:
- **users**: Список пользователей, входящих в команду.
- **incidents**: Список инцидентов, связанных с командой.
- **critical_events**: Список критических событий, связанных с командой.

---

## 3. **Challenge (Задача)**

Модель `Challenge` представляет задачу, которую пользователи могут решать.

### Поля:
- **id** (`Integer`, Primary Key): Уникальный идентификатор задачи.
- **title** (`String`, Not Null): Название задачи.
- **description** (`Text`, Not Null): Описание задачи.
- **flag** (`String`, Not Null): Флаг, который нужно ввести для решения задачи.
- **points** (`Integer`, Not Null): Количество баллов за решение задачи.
- **category** (`String`, Not Null): Категория задачи.
- **hint** (`Text`, Nullable): Подсказка к задаче.
- **hint_penalty** (`Integer`, Default=10): Штраф за использование подсказки (в процентах от баллов задачи).

### Связи:
- **user_challenges**: Список решений задачи пользователями.

---

## 4. **UserChallenge (Решение задачи пользователем)**

Модель `UserChallenge` связывает пользователя и задачу, храня информацию о решении.

### Поля:
- **id** (`Integer`, Primary Key): Уникальный идентификатор записи.
- **user_id** (`Integer`, ForeignKey('user.id'), Not Null): Идентификатор пользователя.
- **challenge_id** (`Integer`, ForeignKey('challenge.id'), Not Null): Идентификатор задачи.
- **solved** (`Boolean`, Default=False): Флаг, указывающий, решена ли задача.
- **used_hint** (`Boolean`, Default=False): Флаг, указывающий, использовалась ли подсказка.
- **team_id** (`Integer`, ForeignKey('team.id'), Nullable): Идентификатор команды (если задача решена в команде).
- **points_awarded** (`Boolean`, Default=False): Флаг, указывающий, начислены ли баллы за решение.

### Связи:
- **user**: Связь с моделью `User`.
- **challenge**: Связь с моделью `Challenge`.
- **team**: Связь с моделью `Team`.

---

## 5. **Incident (Инцидент)**

Модель `Incident` представляет инцидент, созданный пользователем.

### Поля:
- **id** (`Integer`, Primary Key): Уникальный идентификатор инцидента.
- **title** (`String`, Not Null): Название инцидента.
- **description** (`Text`, Not Null): Описание инцидента.
- **status** (`String`, Default='pending'): Статус инцидента (`pending`, `approved`, `rejected`, `needs_revision`).
- **points_awarded** (`Integer`, Default=0): Количество начисленных баллов.
- **user_id** (`Integer`, ForeignKey('user.id'), Not Null): Идентификатор пользователя, создавшего инцидент.
- **admin_id** (`Integer`, ForeignKey('user.id'), Nullable): Идентификатор администратора, проверившего инцидент.
- **team_id** (`Integer`, ForeignKey('team.id'), Nullable): Идентификатор команды, связанной с инцидентом.
- **start_time** (`DateTime`, Not Null): Время начала инцидента.
- **end_time** (`DateTime`, Not Null): Время окончания инцидента.
- **source_ip** (`String`, Not Null): IP-адрес источника.
- **source_port** (`Integer`, Nullable): Порт источника.
- **destination_ip** (`String`, Not Null): IP-адрес назначения.
- **destination_port** (`Integer`, Nullable): Порт назначения.
- **event_type** (`String`, Not Null): Тип события.
- **related_fqdn** (`Text`, Nullable): Связанное доменное имя.
- **related_dns** (`Text`, Nullable): Связанные DNS-записи.
- **ioc** (`Text`, Nullable): Индикаторы компрометации (IOC).
- **hash_value** (`Text`, Nullable): Хэш-значение.
- **mitre_id** (`String`, Nullable): Идентификатор MITRE ATT&CK.
- **siem_id** (`String`, Nullable): Идентификатор SIEM.
- **siem_link** (`Text`, Nullable): Ссылка на событие в SIEM.
- **screenshots** (`JSON`, Nullable): Скриншоты (для PostgreSQL).

### Связи:
- **user**: Связь с моделью `User` (создатель инцидента).
- **admin**: Связь с моделью `User` (администратор, проверивший инцидент).
- **team**: Связь с моделью `Team`.

---

## 6. **CriticalEvent (Критическое событие)**

Модель `CriticalEvent` представляет критическое событие, созданное администратором.

### Поля:
- **id** (`Integer`, Primary Key): Уникальный идентификатор события.
- **title** (`String`, Not Null): Название события.
- **description** (`Text`, Not Null): Описание события.
- **created_by** (`Integer`, ForeignKey('user.id'), Not Null): Идентификатор пользователя, создавшего событие.
- **created_at** (`DateTime`, Default=db.func.now()): Время создания события.
- **admin_id** (`Integer`, ForeignKey('user.id'), Nullable): Идентификатор администратора, связанного с событием.
- **team_id** (`Integer`, ForeignKey('team.id'), Nullable): Идентификатор команды, связанной с событием.

### Связи:
- **responses**: Список ответов на событие.
- **steps**: Список шагов для выполнения события.
- **created_by_user**: Связь с моделью `User` (создатель события).

---

## 7. **CriticalEventResponse (Ответ на критическое событие)**

Модель `CriticalEventResponse` представляет ответ команды на критическое событие.

### Поля:
- **id** (`Integer`, Primary Key): Уникальный идентификатор ответа.
- **event_id** (`Integer`, ForeignKey('critical_event.id'), Not Null): Идентификатор события.
- **user_id** (`Integer`, ForeignKey('user.id'), Not Null): Идентификатор пользователя, создавшего ответ.
- **team_id** (`Integer`, ForeignKey('team.id'), Nullable): Идентификатор команды.
- **response** (`Text`, Not Null): Текст ответа.
- **status** (`String`, Default='pending'): Статус ответа (`pending`, `approved`, `rejected`, `needs_revision`).
- **points_awarded** (`Integer`, Default=0): Количество начисленных баллов.

### Связи:
- **event**: Связь с моделью `CriticalEvent`.
- **user**: Связь с моделью `User`.
- **team**: Связь с моделью `Team`.

---

## 8. **CriticalEventStep (Шаг критического события)**

Модель `CriticalEventStep` представляет шаг для выполнения критического события.

### Поля:
- **id** (`Integer`, Primary Key): Уникальный идентификатор шага.
- **event_id** (`Integer`, ForeignKey('critical_event.id'), Not Null): Идентификатор события.
- **user_id** (`Integer`, ForeignKey('user.id'), Not Null): Идентификатор пользователя, ответственного за шаг.
- **team_id** (`Integer`, ForeignKey('team.id'), Not Null): Идентификатор команды.
- **step_name** (`String`, Not Null): Название шага.
- **description** (`Text`, Nullable): Описание шага.
- **responsible** (`String`, Nullable): Ответственный за шаг.
- **deadline** (`DateTime`, Nullable): Срок выполнения шага.
- **resources** (`Text`, Nullable): Ресурсы для выполнения шага.
- **risks** (`Text`, Nullable): Риски, связанные с шагом.
- **actions** (`Text`, Nullable): Действия для выполнения шага.
- **results** (`Text`, Nullable): Результаты выполнения шага.
- **status** (`String`, Nullable): Статус шага.
- **comments** (`Text`, Nullable): Комментарии к шагу.

### Связи:
- **event**: Связь с моделью `CriticalEvent`.
- **user**: Связь с моделью `User`.
- **team**: Связь с моделью `Team`.

---
