# Маршруты Flask-приложения

В этом разделе описаны все маршруты (роуты) вашего Flask-приложения. Каждый маршрут имеет описание, метод, URL, параметры и примеры использования.

---

## 1. **Главная страница**

- **Описание:** Отображает главную страницу приложения.
- **Метод:** `GET`
- **URL:** `/`
- **Пример кода:**
  ```python
  @app.route('/')
  def index():
      return render_template('index.html')```
	 

## 2. Регистрация
**Описание:** Отображает страницу регистрации и обрабатывает данные формы.

**Метод:** GET, POST

**URL:** /register

**Пример кода:**

```python
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # Логика регистрации
        return redirect(url_for('login'))
    return render_template('register.html')
```

## 3. Авторизация
**Описание:** Отображает страницу авторизации и обрабатывает данные формы.

**Метод:** GET, POST

**URL:** /login

**Пример кода:**

```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Логика авторизации
        return redirect(url_for('profile'))
    return render_template('login.html')
```

## 4. Профиль пользователя
**Описание:** Отображает страницу профиля пользователя.

**Метод:** GET

**URL:** /profile

**Пример кода:**

```python
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')
```

## 5. Список задач
**Описание:** Отображает список всех задач.

**Метод:** GET

**URL:** /challenges

**Пример кода:**

```python
@app.route('/challenges')
@login_required
def challenges():
    challenges = Challenge.query.all()
    return render_template('challenges.html', challenges=challenges)
```

## 6. Отправить флаг
**Описание:** Обрабатывает отправку флага для решения задачи.

**Метод:** POST

**URL:** /submit_flag/<int:challenge_id>

**Пример кода:**

```python
@app.route('/submit_flag/<int:challenge_id>', methods=['POST'])
@login_required
def submit_flag(challenge_id):
    flag = request.form['flag']
    # Логика проверки флага
    return redirect(url_for('challenges'))
```

## 7. Создать инцидент
**Описание:** Отображает форму создания инцидента и обрабатывает данные формы.

**Метод:** GET, POST

**URL:** /create_incident

**Пример кода:**

```python
@app.route('/create_incident', methods=['GET', 'POST'])
@login_required
def create_incident():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        # Логика создания инцидента
        return redirect(url_for('my_incidents'))
    return render_template('create_incident.html')
```

## 8. Мои инциденты
**Описание:** Отображает список инцидентов, созданных текущим пользователем.

**Метод:** GET

**URL:** /my_incidents

**Пример кода:**

```python
@app.route('/my_incidents')
@login_required
def my_incidents():
    incidents = Incident.query.filter_by(user_id=current_user.id).all()
    return render_template('my_incidents.html', incidents=incidents)
```

## 9. Администрирование инцидентов
**Описание:** Отображает список всех инцидентов для администратора.

**Метод:** GET

**URL:** /admin/incidents

**Пример кода:**

```python
@app.route('/admin/incidents')
@login_required
def admin_incidents():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))
    incidents = Incident.query.all()
    return render_template('admin/incidents.html', incidents=incidents)
```

## 10. Создать критическое событие
**Описание:** Отображает форму создания критического события и обрабатывает данные формы.

**Метод:** GET, POST

**URL:** /admin/create_critical_event

**Пример кода:**

```python
@app.route('/admin/create_critical_event', methods=['GET', 'POST'])
@login_required
def create_critical_event():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        # Логика создания события
        return redirect(url_for('admin_critical_events'))
    return render_template('admin/create_critical_event.html')
```

## 11. Рейтинг пользователей
**Описание:** Отображает рейтинг пользователей.

**Метод:** GET

**URL:** /leaderboard

**Пример кода:**

```python
@app.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.total_points.desc()).all()
    return render_template('leaderboard.html', users=users)
```

## 12. Рейтинг команд
**Описание:** Отображает рейтинг команд.

**Метод:** GET

**URL:** /team_leaderboard

**Пример кода:**

```python
@app.route('/team_leaderboard')
def team_leaderboard():
    teams = Team.query.all()
    return render_template('team_leaderboard.html', teams=teams)
```

## 13. Статистика команды
**Описание:** Отображает статистику команды (состав, баллы, место в рейтинге).

**Метод:** GET

**URL:** /team_stats

**Пример кода:**

```python
@app.route('/team_stats')
@login_required
def team_stats():
    if not current_user.team:
        flash('Вы не состоите в команде.', 'warning')
        return redirect(url_for('index'))
    team = Team.query.get_or_404(current_user.team_id)
    team_members = User.query.filter_by(team_id=team.id).all()
    total_points = sum(member.total_points for member in team_members)
    all_teams = db.session.query(
        Team.id,
        Team.name,
        func.sum(User.total_points).label('total_points')
    ).join(User, User.team_id == Team.id) \
     .group_by(Team.id) \
     .order_by(func.sum(User.total_points).desc()) \
     .all()
    team_rank = next((index + 1 for index, t in enumerate(all_teams) if t.id == team.id), None)
    return render_template('team_stats.html', team=team, members=team_members, total_points=total_points, team_rank=team_rank, all_teams=all_teams)
```

## 14. Выход из системы
**Описание:** Завершает сеанс пользователя и перенаправляет на главную страницу.

**Метод:** GET

**URL:** /logout

**Пример кода:**

```python
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))
