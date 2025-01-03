from flask import render_template, url_for, flash, redirect, request
from app import app, db
from app.models import User, Challenge, UserChallenge, Team, Incident, CriticalEvent, CriticalEventResponse
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import func
from datetime import datetime


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/challenges')
@login_required
def challenges():
    # Получаем параметр фильтрации из запроса
    filter_type = request.args.get('filter', 'all')  # По умолчанию показываем все задачи

    # Получаем все задачи
    all_challenges = Challenge.query.all()

    # Фильтруем задачи
    if filter_type == 'solved':
        # Задачи, которые пользователь уже решил
        challenges = [challenge for challenge in all_challenges if challenge.solved_by_user(current_user)]
    elif filter_type == 'unsolved':
        # Задачи, которые пользователь еще не решил
        challenges = [challenge for challenge in all_challenges if not challenge.solved_by_user(current_user)]
    else:
        # Все задачи
        challenges = all_challenges

    return render_template('challenges.html', challenges=challenges, filter_type=filter_type)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Хэшируем пароль перед сохранением
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        # Проверяем пароль с помощью хэша
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('profile'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@app.route('/admin')
@login_required
def admin():
    if current_user.is_admin:
        return render_template('admin.html')
    else:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))


@app.route('/submit_flag/<int:challenge_id>', methods=['POST'])
@login_required
def submit_flag(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    user_flag = request.form['flag']

    if user_flag == challenge.flag:
        # Проверяем, решил ли пользователь задачу ранее
        user_challenge = UserChallenge.query.filter_by(
            user_id=current_user.id,
            challenge_id=challenge_id
        ).first()

        if not user_challenge:
            # Отмечаем задачу как решённую для пользователя
            user_challenge = UserChallenge(
                user_id=current_user.id,
                challenge_id=challenge_id,
                solved=True
            )
            db.session.add(user_challenge)

            # Начисляем баллы пользователю
            current_user.total_points += challenge.points
            db.session.commit()
            flash('Correct flag! Well done!', 'success')
        else:
            flash('You have already solved this challenge!', 'info')
    else:
        flash('Incorrect flag. Try again!', 'danger')

    return redirect(url_for('challenges'))

@app.route('/add_challenge', methods=['GET', 'POST'])
@login_required
def add_challenge():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        flag = request.form['flag']
        points = int(request.form['points'])
        category = request.form['category']
        hint = request.form.get('hint', None)  # Подсказка (может быть пустой)
        hint_penalty = int(request.form.get('hint_penalty', 10))  # Штраф за подсказку (по умолчанию 10%)

        challenge = Challenge(
            title=title,
            description=description,
            flag=flag,
            points=points,
            category=category,
            hint=hint,
            hint_penalty=hint_penalty
        )
        db.session.add(challenge)
        db.session.commit()
        flash('Задача успешно добавлена!', 'success')
        return redirect(url_for('challenges'))

    return render_template('add_challenge.html')


@app.route('/leaderboard')
def leaderboard():
    # Подсчитываем общее количество баллов для каждого пользователя
    leaderboard_data = db.session.query(
        User.username,
        User.total_points.label('total_points')
    ).order_by(User.total_points.desc()) \
     .all()

    return render_template('leaderboard.html', leaderboard=leaderboard_data)


@app.route('/team_leaderboard')
def team_leaderboard():
    # Подсчитываем общее количество баллов для каждой команды
    leaderboard_data = db.session.query(
        Team.name,
        func.sum(User.total_points).label('total_points')
    ).join(User, User.team_id == Team.id) \
     .group_by(Team.id) \
     .order_by(func.sum(User.total_points).desc()) \
     .all()

    return render_template('team_leaderboard.html', leaderboard=leaderboard_data)


@app.route('/manage_teams', methods=['GET', 'POST'])
@login_required
def manage_teams():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        user_id = request.form['user_id']
        team_id = request.form['team_id']

        user = User.query.get(user_id)
        team = Team.query.get(team_id)

        if user and team:
            user.team = team
            db.session.commit()
            flash(f'User {user.username} has been added to team {team.name}!', 'success')
        else:
            flash('User or team not found!', 'danger')

    users = User.query.all()
    teams = Team.query.all()
    return render_template('manage_teams.html', users=users, teams=teams)


@app.route('/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    # Проверяем, что пользователь — администратор
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        team_name = request.form['team_name']

        # Проверяем, что команда с таким именем не существует
        if Team.query.filter_by(name=team_name).first():
            flash('Team name already exists!', 'danger')
        else:
            # Создаем новую команду
            team = Team(name=team_name)
            db.session.add(team)
            db.session.commit()
            flash(f'Team "{team_name}" created successfully!', 'success')
            return redirect(url_for('manage_teams'))

    return render_template('create_team.html')


@app.route('/delete_team/<int:team_id>', methods=['POST'])
@login_required
def delete_team(team_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    team = Team.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    flash(f'Team "{team.name}" deleted successfully!', 'success')
    return redirect(url_for('manage_teams'))

@app.route('/create_incident', methods=['GET', 'POST'])
@login_required
def create_incident():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        incident_type = request.form['incident_type']
        severity_level = request.form['severity_level']
        detection_time = request.form['detection_time']
        occurrence_time = request.form['occurrence_time']
        source = request.form['source']
        affected_systems = request.form['affected_systems']
        suspected_cause = request.form['suspected_cause']
        actions_taken = request.form['actions_taken']
        prevention_recommendations = request.form['prevention_recommendations']

        # Преобразуем строки времени в объекты datetime
        detection_time = datetime.strptime(detection_time, '%Y-%m-%dT%H:%M') if detection_time else None
        occurrence_time = datetime.strptime(occurrence_time, '%Y-%m-%dT%H:%M') if occurrence_time else None

        # Автоматически добавляем команду пользователя
        team_id = current_user.team_id if current_user.team else None

        # Создаем инцидент
        incident = Incident(
            title=title,
            description=description,
            user_id=current_user.id,
            team_id=team_id,  # Автоматически добавляем команду
            incident_type=incident_type,
            severity_level=severity_level,
            detection_time=detection_time,
            occurrence_time=occurrence_time,
            source=source,
            affected_systems=affected_systems,
            suspected_cause=suspected_cause,
            actions_taken=actions_taken,
            prevention_recommendations=prevention_recommendations
        )
        db.session.add(incident)
        db.session.commit()
        flash('Инцидент успешно создан!', 'success')
        return redirect(url_for('my_incidents'))

    return render_template('create_incident.html')

@app.route('/my_incidents')
@login_required
def my_incidents():
    incidents = Incident.query.filter_by(user_id=current_user.id).all()
    return render_template('my_incidents.html', incidents=incidents)


@app.route('/admin/incidents')
@login_required
def admin_incidents():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    # Получаем статус из query-параметра (по умолчанию 'pending')
    status = request.args.get('status', 'pending')

    # Фильтруем инциденты по статусу
    if status == 'all':
        incidents = Incident.query.all()
    else:
        incidents = Incident.query.filter_by(status=status).all()

    return render_template('admin/admin_incidents.html', incidents=incidents, status=status)


@app.route('/admin/review_incident/<int:incident_id>', methods=['GET', 'POST'])
@login_required
def review_incident(incident_id):
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    incident = Incident.query.get_or_404(incident_id)

    if request.method == 'POST':
        action = request.form['action']
        points = int(request.form.get('points', 0))

        if action == 'approve':
            incident.status = 'approved'
            incident.points_awarded = points

            # Начисляем баллы пользователю
            user = User.query.get(incident.user_id)
            user.total_points += points
            db.session.commit()

            flash('Инцидент одобрен! Баллы начислены.', 'success')
        elif action == 'reject':
            incident.status = 'rejected'
            flash('Инцидент отклонен!', 'danger')
        elif action == 'needs_revision':
            incident.status = 'needs_revision'
            flash('Инцидент отправлен на доработку!', 'warning')

        incident.admin_id = current_user.id
        db.session.commit()
        return redirect(url_for('admin_incidents'))

    return render_template('admin/review_incident.html', incident=incident)


@app.route('/edit_incident/<int:incident_id>', methods=['GET', 'POST'])
@login_required
def edit_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)

    # Проверяем, что инцидент принадлежит текущему пользователю и его статус "needs_revision"
    if incident.user_id != current_user.id or incident.status != 'needs_revision':
        flash('Вы не можете редактировать этот инцидент.', 'danger')
        return redirect(url_for('my_incidents'))

    if request.method == 'POST':
        # Обновляем все поля инцидента
        incident.title = request.form['title']
        incident.description = request.form['description']
        incident.incident_type = request.form['incident_type']
        incident.severity_level = request.form['severity_level']
        incident.detection_time = datetime.strptime(request.form['detection_time'], '%Y-%m-%dT%H:%M') if request.form['detection_time'] else None
        incident.occurrence_time = datetime.strptime(request.form['occurrence_time'], '%Y-%m-%dT%H:%M') if request.form['occurrence_time'] else None
        incident.source = request.form['source']
        incident.affected_systems = request.form['affected_systems']
        incident.suspected_cause = request.form['suspected_cause']
        incident.actions_taken = request.form['actions_taken']
        incident.prevention_recommendations = request.form['prevention_recommendations']
        incident.status = 'pending'  # Меняем статус на "pending" для повторной проверки

        db.session.commit()
        flash('Инцидент обновлен и отправлен на проверку!', 'success')
        return redirect(url_for('my_incidents'))

    return render_template('edit_incident.html', incident=incident)


@app.route('/admin/create_critical_event', methods=['GET', 'POST'])
@login_required
def create_critical_event():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        # Создаем новое КС
        event = CriticalEvent(
            title=title,
            description=description,
            created_by=current_user.id
        )
        db.session.add(event)
        db.session.commit()
        flash('Critical event created successfully!', 'success')
        return redirect(url_for('admin_critical_events'))

    return render_template('admin/create_critical_event.html')
    
@app.route('/admin/critical_events', methods=['GET', 'POST'])
@login_required
def admin_critical_events():
    if request.method == 'POST':
        selected_team_id = request.form.get('team_id')  # Для POST-запросов
    else:
        selected_team_id = request.args.get('team_id')  # Для GET-запросов

    # Логика для фильтрации событий и отчетов по selected_team_id
    if selected_team_id:
        # Фильтруем события по team_id
        events = CriticalEvent.query.filter_by(team_id=selected_team_id).all()
        # Фильтруем отчеты по team_id
        responses = CriticalEventResponse.query.filter_by(team_id=selected_team_id).all()
    else:
        # Если команда не выбрана, показываем все события и отчеты
        events = CriticalEvent.query.all()
        responses = CriticalEventResponse.query.all()

    # Получаем список всех команд
    teams = Team.query.all()

    # Передаем данные в шаблон
    return render_template(
        'admin/critical_events.html',
        events=events,
        responses=responses,
        teams=teams,
        selected_team_id=selected_team_id
    )
@app.route('/admin/edit_critical_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_critical_event(event_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    critical_event = CriticalEvent.query.get_or_404(event_id)

    if request.method == 'POST':
        critical_event.title = request.form['title']
        critical_event.description = request.form['description']
        critical_event.team_id = request.form.get('team_id')
        db.session.commit()
        flash('Critical event updated successfully!', 'success')
        return redirect(url_for('admin_critical_events'))

    # Передаем список команд в шаблон
    teams = Team.query.all()
    return render_template('admin/edit_critical_event.html', critical_event=critical_event, teams=teams)


@app.route('/admin/delete_critical_event/<int:event_id>', methods=['POST'])
@login_required
def delete_critical_event(event_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    critical_event = CriticalEvent.query.get_or_404(event_id)
    db.session.delete(critical_event)
    db.session.commit()
    flash('Critical event deleted successfully!', 'success')
    return redirect(url_for('admin_critical_events'))


@app.route('/user/critical_events')
@login_required
def user_critical_events():
    # Получаем все ответы пользователя на КС
    events = CriticalEvent.query.all()
    return render_template('user/critical_events.html', events=events)

@app.route('/fill_critical_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def fill_critical_event(event_id):
    event = CriticalEvent.query.get_or_404(event_id)

    # Проверяем, есть ли у пользователя отчет на это событие
    response = CriticalEventResponse.query.filter_by(
        event_id=event.id,
        user_id=current_user.id
    ).first()

    if request.method == 'POST':
        # Если отчет уже существует и не требует доработки, запрещаем отправку
        if response and response.status != 'needs_revision':
            flash('You have already submitted a response for this event.', 'info')
            return redirect(url_for('user_critical_events'))

        response_text = request.form['response']

        if response:
            # Обновляем существующий отчет
            response.response = response_text
            response.status = 'pending'  # Возвращаем статус "pending"
        else:
            # Создаем новый отчет
            response = CriticalEventResponse(
                event_id=event.id,
                user_id=current_user.id,
                team_id=current_user.team_id,
                response=response_text,
                status='pending'
            )
            db.session.add(response)

        db.session.commit()
        flash('Your response has been submitted!', 'success')
        return redirect(url_for('user_critical_events'))

    # Если отчет уже существует и не требует доработки, запрещаем доступ к форме
    if response and response.status != 'needs_revision':
        flash('You have already submitted a response for this event.', 'info')
        return redirect(url_for('user_critical_events'))

    return render_template('user/fill_critical_event.html', event=event, response=response)

@app.route('/admin/review_critical_event/<int:event_id>/<int:team_id>', methods=['GET', 'POST'])
@login_required
def review_critical_event(event_id, team_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    # Получаем ответ на критическое событие для указанной команды
    response = CriticalEventResponse.query.filter_by(
        event_id=event_id,
        team_id=team_id
    ).first_or_404()

    if request.method == 'POST':
        action = request.form.get('action')
        points = int(request.form.get('points', 0))

        if action == 'approve':
            response.status = 'approved'
            response.points_awarded = points

            # Начисляем баллы пользователю
            user = User.query.get(response.user_id)
            user.total_points += points
            db.session.commit()

            flash('Response approved! Points awarded.', 'success')
        elif action == 'reject':
            response.status = 'rejected'
            flash('Response rejected!', 'danger')
        elif action == 'needs_revision':
            response.status = 'needs_revision'
            flash('Response sent for revision!', 'warning')

        db.session.commit()
        return redirect(url_for('admin_critical_events'))

    return render_template('admin/review_critical_event.html', response=response)
    
@app.route('/request_hint/<int:challenge_id>', methods=['POST'])
@login_required
def request_hint(challenge_id):
    # Заглушка: просто сообщаем, что подсказка запрошена
    flash('Запрос на подсказку отправлен. В будущем подсказка будет отправлена через Rocket.Chat.', 'info')
    return redirect(url_for('challenges'))
    
@app.route('/admin/review_response/<int:response_id>', methods=['GET', 'POST'])
@login_required
def review_response(response_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    response = CriticalEventResponse.query.get_or_404(response_id)

    if request.method == 'POST':
        action = request.form.get('action')
        points = int(request.form.get('points', 0))

        if action == 'approve':
            response.status = 'approved'
            response.points_awarded = points

            # Начисляем баллы пользователю
            user = User.query.get(response.user_id)
            user.total_points += points
            db.session.commit()

            flash('Response approved! Points awarded.', 'success')
        elif action == 'reject':
            response.status = 'rejected'
            flash('Response rejected!', 'danger')
        elif action == 'needs_revision':
            response.status = 'needs_revision'
            flash('Response sent for revision!', 'warning')

        db.session.commit()
        return redirect(url_for('admin_critical_events'))

    return render_template('admin/review_response.html', response=response)


@app.route('/edit_response/<int:response_id>', methods=['GET', 'POST'])
@login_required
def edit_response(response_id):
    response = CriticalEventResponse.query.get_or_404(response_id)

    # Проверяем, что отчет принадлежит текущему пользователю и его статус "needs_revision"
    if response.user_id != current_user.id or response.status != 'needs_revision':
        flash('You cannot edit this response.', 'danger')
        return redirect(url_for('user_critical_events'))

    if request.method == 'POST':
        response.response = request.form['response']
        response.status = 'pending'  # Меняем статус на "pending" для повторной проверки
        db.session.commit()
        flash('Response updated and submitted for review!', 'success')
        return redirect(url_for('user_critical_events'))

    return render_template('edit_response.html', response=response)