from flask import render_template, url_for, flash, redirect, request
from app import app, db
from app.models import User, Challenge, UserChallenge, Team, Incident, CriticalEvent, CriticalEventResponse,CriticalEventStep,Infrastructure,PointsHistory
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import func
from datetime import datetime
from flask import Flask, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
import uuid
import os
from sqlalchemy.orm.attributes import flag_modified
from flask import request, flash, redirect, url_for, render_template
from flask import send_from_directory
import logging

from . import competitions

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
def generate_unique_filename(filename):
    """
    Генерирует уникальное имя файла, сохраняя его расширение.
    """
    ext = os.path.splitext(filename)[1]  # Получаем расширение файла
    unique_name = f"{uuid.uuid4().hex}{ext}"  # Генерируем уникальное имя
    return unique_name

@app.route('/')
def index():
    return render_template('index.html')

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

  # Импортируем модель PointsHistory

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
            # Отмечаем задачу как решённую для текущего пользователя
            user_challenge = UserChallenge(
                user_id=current_user.id,
                challenge_id=challenge_id,
                solved=True
            )
            db.session.add(user_challenge)

            # Начисляем баллы текущему пользователю
            current_user.total_points += challenge.points

            # Добавляем запись в историю начисления баллов
            points_history = PointsHistory(
                user_id=current_user.id,
                points=challenge.points,
                note=f"За решение задачи: {challenge.title}"
            )
            db.session.add(points_history)

            db.session.commit()

            # Если пользователь в команде, отмечаем задачу как решённую для всех членов команды
            if current_user.team:
                team_members = User.query.filter_by(team_id=current_user.team_id).all()
                for member in team_members:
                    if member.id != current_user.id:  # Пропускаем текущего пользователя
                        member_challenge = UserChallenge.query.filter_by(
                            user_id=member.id,
                            challenge_id=challenge_id
                        ).first()

                        if not member_challenge:
                            member_challenge = UserChallenge(
                                user_id=member.id,
                                challenge_id=challenge_id,
                                solved=True
                            )
                            db.session.add(member_challenge)

                            # Начисляем баллы члену команды
                            member.total_points += challenge.points

                            # Добавляем запись в историю начисления баллов для члена команды
                            member_points_history = PointsHistory(
                                user_id=member.id,
                                points=challenge.points,
                                note=f"За решение задачи: {challenge.title} (командное начисление)"
                            )
                            db.session.add(member_points_history)

                db.session.commit()

            flash('Correct flag! Well done!', 'success')
        else:
            flash('You have already solved this challenge!', 'info')
    else:
        flash('Incorrect flag. Try again!', 'danger')

    # Перенаправляем на страницу задач текущего соревнования
    return redirect(url_for('competition_challenges', competition_id=challenge.competition_id))


@app.route('/leaderboard')
@login_required
def leaderboard():
    # Запрашиваем данные пользователей, включая аватарки
    leaderboard_data = db.session.query(
        User.username,
        User.total_points,
        User.avatar  # Добавляем поле avatar
    ).order_by(User.total_points.desc()) \
     .all()

    return render_template('leaderboard.html', leaderboard=leaderboard_data)

@app.route('/team_leaderboard')
@login_required
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

@app.route('/request_hint/<int:challenge_id>', methods=['POST'])
@login_required
def request_hint(challenge_id):
    # Заглушка: просто сообщаем, что подсказка запрошена
    flash('Запрос на подсказку отправлен. В будущем подсказка будет отправлена через Rocket.Chat.', 'info')
    return redirect(url_for('challenges'))
@app.route('/admin/manage_teams', methods=['GET', 'POST'])
@login_required
def manage_teams():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Обработка создания новой команды
        if 'create_team' in request.form:
            team_name = request.form['team_name']
            if Team.query.filter_by(name=team_name).first():
                flash('Команда с таким именем уже существует!', 'danger')
            else:
                team = Team(name=team_name)
                db.session.add(team)
                db.session.commit()
                flash(f'Команда "{team_name}" успешно создана!', 'success')

        # Обработка удаления команды
        elif 'delete_team' in request.form:
            team_id = request.form['team_id']
            team = Team.query.get(team_id)
            if team:
                db.session.delete(team)
                db.session.commit()
                flash(f'Команда "{team.name}" успешно удалена!', 'success')

        # Обработка добавления пользователя в команду
        elif 'add_user_to_team' in request.form:
            user_id = request.form['user_id']
            team_id = request.form['team_id']
            user = User.query.get(user_id)
            team = Team.query.get(team_id)
            if user and team:
                user.team_id = team.id
                db.session.commit()
                flash(f'Пользователь "{user.username}" добавлен в команду "{team.name}"!', 'success')

        # Обработка удаления пользователя из команды
        elif 'remove_user_from_team' in request.form:
            user_id = request.form['user_id']
            user = User.query.get(user_id)
            if user:
                user.team_id = None
                db.session.commit()
                flash(f'Пользователь "{user.username}" удален из команды!', 'success')

    # Получаем список всех команд и пользователей
    teams = Team.query.all()
    users = User.query.all()
    return render_template('admin/manage_teams.html', teams=teams, users=users)

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
            return redirect(url_for('admin/manage_teams'))

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
    return redirect(url_for('admin/manage_teams'))

from flask_uploads import UploadNotAllowed

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/admin/create_critical_event', methods=['GET', 'POST'])
@login_required
def create_critical_event1():
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

@app.route('/admin/critical_event_responses')
@login_required
def admin_critical_event_responses1():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    # Получаем только отчёты, ожидающие проверки
    responses = CriticalEventResponse.query.filter_by(status='pending').all()
    return render_template('admin/critical_event_responses.html', responses=responses)

@app.route('/admin/approved_responses')
@login_required
def admin_approved_responses1():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    # Получаем все принятые отчёты
    responses = CriticalEventResponse.query.filter_by(status='approved').all()
    return render_template('admin/approved_responses.html', responses=responses)

@app.route('/admin/critical_events')
@login_required
def admin_critical_events1():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    # Получаем все КС, созданные администраторами
    events = CriticalEvent.query.join(User, CriticalEvent.created_by == User.id).filter(User.is_admin == True).all()
    return render_template('admin/critical_events.html', events=events)


@app.route('/admin/edit_critical_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_critical_event1(event_id):
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


import os
from flask import current_app, flash, redirect, url_for
from app.models import CriticalEvent, CriticalEventResponse
from app import db

def delete_screenshots(screenshots):
    """
    Удаляет файлы скриншотов с сервера.
    """
    if screenshots:
        for screenshot in screenshots:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], screenshot)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Файл {screenshot} успешно удален.")
                except Exception as e:
                    print(f"Ошибка при удалении файла {screenshot}: {e}")



# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



@app.route('/admin/review_response/<int:response_id>', methods=['GET', 'POST'])
@login_required
def review_response1(response_id):
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    # Получаем отчет по ID
    response = CriticalEventResponse.query.get_or_404(response_id)

    # Получаем все шаги, связанные с этим отчетом
    steps = CriticalEventStep.query.filter_by(
        event_id=response.event_id,
        team_id=response.team_id
    ).all()

    # Преобразуем JSON-строку в список (если необходимо)
    for step in steps:
        logger.debug(f"Проверка инцидента: {step.screenshots}")
        if step.screenshots and isinstance(step.screenshots, str):
            step.screenshots = json.loads(step.screenshots)

    if request.method == 'POST':
        action = request.form.get('action')
        points = int(request.form.get('points', 0))

        if action == 'approve':
            # Одобрение отчета
            response.status = 'approved'
            response.points_awarded = points

            # Начисляем баллы пользователю
            user = User.query.get(response.user_id)
            user.total_points += points

            # Добавляем запись в историю начисления баллов
            points_history = PointsHistory(
                user_id=response.user_id,
                points=points,
                note=f"За критическое событие: {response.event.title}"
            )
            db.session.add(points_history)

            flash('Отчёт принят! Баллы начислены.', 'success')

        elif action == 'reject':
            # Отклонение отчета
            response.status = 'rejected'
            flash('Отчёт отклонён!', 'danger')

        elif action == 'needs_revision':
            # Отправка на доработку
            response.status = 'needs_revision'
            CriticalEventStep.query.filter_by(event_id=response.event_id, team_id=response.team_id).delete()
            flash('Отчёт отправлен на доработку! Все шаги удалены.', 'warning')

        # Сохраняем изменения в базе данных
        db.session.commit()

        return redirect(url_for('admin_critical_events'))

    return render_template('admin/review_response.html', response=response, steps=steps)

@app.route('/user/accepted_responses')
@login_required
def user_accepted_responses1():
    if not current_user.team:
        flash('Вы не состоите в команде.', 'warning')
        return redirect(url_for('index'))

    # Получаем принятые отчёты для команды пользователя
    responses = CriticalEventResponse.query.filter_by(
        team_id=current_user.team_id,
        status='approved'
    ).all()
    return render_template('user/accepted_responses.html', responses=responses)

@app.route('/user/pending_responses')
@login_required
def user_pending_responses1():
    if not current_user.team:
        flash('Вы не состоите в команде.', 'warning')
        return redirect(url_for('index'))

    # Получаем все критические события
    events = CriticalEvent.query.all()
    pending_responses = []

    for event in events:
        # Проверяем, есть ли отчёт команды пользователя для этого события
        team_response = CriticalEventResponse.query.filter_by(
            event_id=event.id,
            team_id=current_user.team_id
        ).first()

        # Если отчёта нет или он требует доработки, добавляем событие в список
        if not team_response or team_response.status in ['rejected', 'needs_revision']:
            pending_responses.append(event)

    return render_template('user/pending_responses.html', events=pending_responses)

@app.route('/user/under_review_responses')
@login_required
def user_under_review_responses1():
    if not current_user.team:
        flash('Вы не состоите в команде.', 'warning')
        return redirect(url_for('index'))

    # Получаем отчёты команды пользователя, которые ожидают проверки
    responses = CriticalEventResponse.query.filter_by(
        team_id=current_user.team_id,
        status='pending'
    ).all()
    return render_template('user/under_review_responses.html', responses=responses)


@app.route('/view_event/<int:event_id>')
@login_required
def view_event(event_id):
    event = CriticalEvent.query.get_or_404(event_id)
    return render_template('view_event.html', event=event)


@app.route('/submit_critical_event/<int:event_id>', methods=['POST'])
@login_required
def submit_critical_event(event_id):
    event = CriticalEvent.query.get_or_404(event_id)
    response = CriticalEventResponse.query.filter_by(event_id=event.id, user_id=current_user.id).first()

    # Проверяем, что отчет можно отправить на проверку
    if response and response.status in ['rejected', 'needs_revision']:
        response.status = 'pending'  # Меняем статус на "pending"
        db.session.commit()
        flash('Отчет отправлен на проверку!', 'success')
    else:
        flash('Отчет уже находится на проверке или не может быть отправлен.', 'warning')

    return redirect(url_for('user_pending_responses'))


@app.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        is_admin = 'is_admin' in request.form  # Проверяем, отмечен ли чекбокс "Администратор"

        # Проверяем, что пароли совпадают
        if password != confirm_password:
            flash('Пароли не совпадают!', 'danger')
            return redirect(url_for('/admin/create_user'))

        # Проверяем, что пользователь с таким email или username не существует
        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash('Пользователь с таким email или username уже существует!', 'danger')
        else:
            # Создаем нового пользователя
            user = User(username=username, email=email, is_admin=is_admin)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'Пользователь "{username}" успешно создан!', 'success')
            return redirect(url_for('admin'))  # Перенаправляем на страницу администрирования

    return render_template('/admin/create_user.html')


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    # Статистика команд
    teams = Team.query.all()
    team_stats = []
    for team in teams:
        team_stats.append({
            'name': team.name,
            'members': len(team.users),
            'points': sum(user.total_points for user in team.users)
        })

    # Статистика флагов
    challenges = Challenge.query.all()
    solved_flags = UserChallenge.query.filter_by(solved=True).count()
    unsolved_flags = UserChallenge.query.filter_by(solved=False).count()

    # Статистика по критическим событиям
    critical_events = CriticalEvent.query.all()
    critical_events_stats = {
        'total': len(critical_events),
        'pending': CriticalEventResponse.query.filter_by(status='pending').count(),
        'resolved': CriticalEventResponse.query.filter_by(status='resolved').count()
    }

    # Статистика по инцидентам
    incidents = Incident.query.all()
    incidents_stats = {
        'total': len(incidents),
        'open': Incident.query.filter_by(status='open').count(),
        'closed': Incident.query.filter_by(status='closed').count()
    }

    return render_template('admin/admin_dashboard.html',
                           team_stats=team_stats,
                           solved_flags=solved_flags,
                           unsolved_flags=unsolved_flags,
                           critical_events_stats=critical_events_stats,
                           incidents_stats=incidents_stats)




# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/admin/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    selected_user = None
    if request.method == 'GET':
        # Получаем выбранного пользователя из query-параметра
        user_id = request.args.get('user_id')
        if user_id:
            selected_user = User.query.get(user_id)

    if request.method == 'POST':
        # Обработка редактирования пользователя
        if 'edit_user' in request.form:
            user_id = request.form['user_id']
            username = request.form['username']
            email = request.form['email']
            is_admin = 'is_admin' in request.form
            team_id = request.form.get('team_id')

            # Обработка points_change
            points_change_str = request.form.get('points_change', '0')  # Получаем значение как строку
            points_change = int(points_change_str) if points_change_str.strip() else 0  # Преобразуем в int, если не пусто

            user = User.query.get(user_id)
            if user:
                user.username = username
                user.email = email
                user.is_admin = is_admin
                user.team_id = team_id if team_id else None

                # Изменяем баллы только если points_change не равен 0
                if points_change != 0:
                    user.total_points += points_change
                    flash(f'Баллы пользователя "{username}" изменены на {points_change}.', 'success')
                else:
                    flash(f'Баллы пользователя "{username}" не изменены.', 'info')

                db.session.commit()
                selected_user = user  # Обновляем выбранного пользователя

        # Обработка удаления пользователя
        elif 'delete_user' in request.form:
            user_id = request.form['user_id']
            user = User.query.get(user_id)
            if user:
                try:
                    # Находим администратора (например, первого администратора в системе)
                    admin_user = User.query.filter_by(is_admin=True).first()

                    if not admin_user:
                        flash('Не найден администратор для переназначения событий.', 'danger')
                        return redirect(url_for('manage_users'))

                    # Переназначаем события (critical_event) на администратора
                    CriticalEvent.query.filter_by(created_by=user_id).update({"created_by": admin_user.id})
                    CriticalEvent.query.filter_by(admin_id=user_id).update({"admin_id": admin_user.id})

                    # Удаляем все связанные инциденты
                    incidents = Incident.query.filter_by(user_id=user_id).all()
                    for incident in incidents:
                        db.session.delete(incident)

                    # Удаляем все связанные записи в points_history
                    points_history = PointsHistory.query.filter_by(user_id=user_id).all()
                    for history in points_history:
                        db.session.delete(history)

                    # Удаляем все связанные записи в user_challenge
                    user_challenges = UserChallenge.query.filter_by(user_id=user_id).all()
                    for challenge in user_challenges:
                        db.session.delete(challenge)

                    # Удаляем все связанные записи в critical_event_response
                    user_critical_event_response = CriticalEventResponse.query.filter_by(user_id=user_id).all()
                    for response in user_critical_event_response:
                        db.session.delete(response)

                    # Удаляем пользователя
                    db.session.delete(user)

                    # Фиксируем изменения в базе данных
                    db.session.commit()
                    flash(f'Пользователь "{user.username}" успешно удален! События переназначены администратору.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Ошибка при удалении пользователя: {str(e)}', 'danger')

    # Получаем список всех пользователей и команд
    users = User.query.all()
    teams = Team.query.all()
    return render_template('admin/manage_users.html', users=users, teams=teams, selected_user=selected_user)

@app.route('/view_incident/<int:incident_id>')
@login_required
def view_incident1(incident_id):
    # Получаем инцидент по ID
    incident = Incident.query.get_or_404(incident_id)

    # Проверяем, что инцидент принадлежит текущему пользователю или его команде
    if (incident.user_id != current_user.id) and (not current_user.team or incident.team_id != current_user.team_id):
        flash('У вас нет прав доступа к этому инциденту.', 'danger')
        return redirect(url_for('my_incidents'))

    # Проверяем, что инцидент имеет статус "approved" или "rejected"
    if incident.status not in ['approved', 'rejected']:
        flash('Этот инцидент нельзя просмотреть.', 'danger')
        return redirect(url_for('my_incidents'))

    return render_template('user/view_incident.html', incident=incident)
@app.route('/team_stats')
@login_required
def team_stats():
    # Проверяем, что пользователь состоит в команде
    if not current_user.team:
        flash('Вы не состоите в команде.', 'warning')
        return redirect(url_for('index'))

    # Получаем текущую команду пользователя
    team = Team.query.get_or_404(current_user.team_id)

    # Получаем всех участников команды
    team_members = User.query.filter_by(team_id=team.id).all()

    # Получаем общее количество баллов команды
    total_points = sum(member.total_points for member in team_members)

    # Получаем место команды в рейтинге
    all_teams = db.session.query(
        Team.id,
        Team.name,
        func.sum(User.total_points).label('total_points')
    ).join(User, User.team_id == Team.id) \
     .group_by(Team.id) \
     .order_by(func.sum(User.total_points).desc()) \
     .all()

    # Находим место текущей команды
    team_rank = next((index + 1 for index, t in enumerate(all_teams) if t.id == team.id), None)

    return render_template('user/team_stats.html', team=team, members=team_members, total_points=total_points, team_rank=team_rank, all_teams=all_teams)

@app.route('/infrastructure')
@login_required
def infrastructure():
    # Получаем данные об инфраструктуре из базы данных
    infra = Infrastructure.query.first()  # Предполагаем, что у нас только одна запись
    if not infra:
        flash('Информация об инфраструктуре пока недоступна.', 'warning')
        return redirect(url_for('index'))

    return render_template('infrastructure.html', infra=infra)

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    # Убедитесь, что файл существует и безопасен для скачивания
    if not filename or not filename.endswith(('.pdf', '.txt', '.docx')):
        flash('Недопустимый файл.', 'danger')
        return redirect(url_for('infrastructure'))

    # Путь к папке с файлами
    upload_folder = app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, filename, as_attachment=True)





@app.route('/upload', methods=['GET', 'POST'])
@login_required
#@admin_required Исправить
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            flash('Файл успешно загружен!', 'success')
            return redirect(url_for('infrastructure'))
        else:
            flash('Недопустимый формат файла.', 'danger')
    return render_template('upload.html')


@app.route('/infrastructure/topology')
@login_required
def infrastructure_topology():
    # Получаем данные об инфраструктуре
    infra = Infrastructure.query.first()
    if not infra:
        flash('Информация о топологии сети пока недоступна.', 'warning')
        return redirect(url_for('infrastructure'))

    # Преобразуем данные топологии в JSON
    topology_data = {
        "nodes": infra.topology.get("nodes", []),
        "links": infra.topology.get("links", [])
    }

    return render_template('infrastructure_topology.html', topology_data=topology_data )

from flask import request, redirect, url_for, flash


@app.route('/admin/topology', methods=['GET'])
@login_required
def admin_topology():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    # Получаем данные топологии
    infra = Infrastructure.query.first()

    # Проверяем, что данные существуют
    if not infra:
        flash('Данные об инфраструктуре отсутствуют.', 'warning')
        return redirect(url_for('index'))

    # Проверяем и преобразуем данные
    topology = infra.topology if infra.topology else []  # Убедимся, что topology — это список
    links = infra.links if infra.links else []

    # Формируем данные для передачи в шаблон
    topology_data = {
        "nodes": topology,  # Узлы (список)
        "links": links      # Связи
    }

    # Передаем данные в шаблон как объект JSON
    return render_template('admin_topology.html', topology_data=topology_data)


from flask import request, jsonify

@app.route('/save_topology', methods=['POST'])
@login_required
def save_topology():
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "У вас нет прав доступа к этой странице."})

    # Получаем данные из запроса
    data = request.get_json()

    # Логируем полученные данные
    print("Полученные данные:", data)

    # Проверяем, что данные существуют
    if not data:
        return jsonify({"success": False, "message": "Нет данных для сохранения."})

    # Получаем объект инфраструктуры из базы данных
    infra = Infrastructure.query.first()
    if not infra:
        return jsonify({"success": False, "message": "Инфраструктура не найдена."})

    try:
        # Обновляем данные топологии
        infra.topology = {
            "nodes": data["nodes"],  # Сохраняем все узлы (новые и отредактированные)
            "links": data["links"]   # Сохраняем все связи (новые и существующие)
        }
        db.session.commit()
        print("Топология успешно сохранена в базе данных.")
        return jsonify({"success": True, "message": "Топология успешно сохранена."})
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при сохранении топологии: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка при сохранении топологии: {str(e)}"})

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('Файл не выбран', 'danger')
        return redirect(url_for('profile'))

    file = request.files['avatar']
    if file.filename == '':
        flash('Файл не выбран', 'danger')
        return redirect(url_for('profile'))

    if file and allowed_file(file.filename):
        current_user.update_avatar(file)
        flash('Аватар успешно обновлен', 'success')
    else:
        flash('Недопустимый формат файла', 'danger')

    return redirect(url_for('profile'))




@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Обновляем имя пользователя
        new_username = request.form.get('username')
        if new_username and new_username != current_user.username:
            current_user.username = new_username

        # Обновляем пароль
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if new_password and confirm_password:
            if new_password == confirm_password:
                current_user.set_password(new_password)
            else:
                flash('Пароли не совпадают', 'danger')
                return redirect(url_for('edit_profile'))

        # Обновляем аватар
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    # Генерируем уникальное имя файла
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)

                    # Удаляем старый аватар, если он существует
                    if current_user.avatar:
                        old_avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar)
                        if os.path.exists(old_avatar_path):
                            os.remove(old_avatar_path)

                    # Сохраняем новое имя файла в базе данных
                    current_user.avatar = unique_filename
                else:
                    flash('Недопустимый формат файла', 'danger')
                    return redirect(url_for('edit_profile'))

        # Сохраняем изменения в базе данных
        db.session.commit()
        flash('Профиль успешно обновлен', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html')
