from flask import render_template, url_for, flash, redirect, request
from app import app, db
from app.models import User, Challenge, UserChallenge, Team, Incident, CriticalEvent, CriticalEventResponse,CriticalEventStep,Infrastructure
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import func
from datetime import datetime
from flask import Flask, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
import uuid
import os
from sqlalchemy.orm.attributes import flag_modified
from flask import request, flash, redirect, url_for, render_template
from datetime import datetime
from flask import send_from_directory
from werkzeug.utils import secure_filename

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
            # Отмечаем задачу как решённую для текущего пользователя
            user_challenge = UserChallenge(
                user_id=current_user.id,
                challenge_id=challenge_id,
                solved=True
            )
            db.session.add(user_challenge)

            # Начисляем баллы текущему пользователю
            current_user.total_points += challenge.points
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
    return render_template('manage_teams.html', teams=teams, users=users)

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

from flask_uploads import UploadNotAllowed

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/create_incident', methods=['GET', 'POST'])
@login_required
def create_incident():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
        source_ip = request.form['source_ip']
        source_port = int(request.form['source_port']) if request.form['source_port'] else None
        destination_ip = request.form['destination_ip']
        destination_port = int(request.form['destination_port']) if request.form['destination_port'] else None
        event_type = request.form['event_type']
        related_fqdn = request.form['related_fqdn']
        related_dns = request.form['related_dns']
        ioc = request.form['ioc']
        hash_value = request.form['hash_value']
        mitre_id = request.form['mitre_id']
        siem_id = request.form['siem_id']
        siem_link = request.form['siem_link']

        team_id = current_user.team_id if current_user.team else None

        # Обработка загрузки скриншотов
        screenshot_paths = []
        if 'screenshots' in request.files:
            files = request.files.getlist('screenshots')
            for file in files:
                if file.filename != '' and allowed_file(file.filename):
                    # Генерируем уникальное имя файла
                    unique_filename = generate_unique_filename(file.filename)
                    # Сохраняем файл
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    screenshot_paths.append(unique_filename)  # Сохраняем уникальное имя
                else:
                    flash(f'Недопустимый формат файла: {file.filename}', 'danger')
                    return redirect(url_for('create_incident'))

        # Создаем инцидент
        incident = Incident(
            title=title,
            description=description,
            user_id=current_user.id,
            team_id=team_id,
            start_time=start_time,
            end_time=end_time,
            source_ip=source_ip,
            source_port=source_port,
            destination_ip=destination_ip,
            destination_port=destination_port,
            event_type=event_type,
            related_fqdn=related_fqdn,
            related_dns=related_dns,
            ioc=ioc,
            hash_value=hash_value,
            mitre_id=mitre_id,
            siem_id=siem_id,
            siem_link=siem_link,
            screenshots=screenshot_paths  # Сохраняем уникальные имена файлов
        )
        db.session.add(incident)
        db.session.commit()

        flash('Инцидент успешно создан!', 'success')
        return redirect(url_for('my_incidents'))

    return render_template('create_incident.html')


@app.route('/my_incidents')
@login_required
def my_incidents():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    status = request.args.get('status', 'all')

    # Базовый запрос
    if current_user.team:
        query = Incident.query.filter_by(team_id=current_user.team_id)
    else:
        query = Incident.query.filter_by(user_id=current_user.id)

    # Фильтрация по статусу
    if status != 'all':
        query = query.filter_by(status=status)

    # Пагинация
    incidents = query.order_by(Incident.start_time.desc()).paginate(page=page, per_page=per_page)

    return render_template('my_incidents.html', incidents=incidents, status=status)


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


import os
import logging
from flask import request, flash, redirect, url_for, render_template

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/admin/review_incident/<int:incident_id>', methods=['GET', 'POST'])
@login_required
def review_incident(incident_id):
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    # Получаем инцидент по ID
    incident = Incident.query.get_or_404(incident_id)
    logger.debug(f"Проверка инцидента: {incident.id}")

    if request.method == 'POST':
        action = request.form['action']
        points = int(request.form.get('points', 0))

        if action == 'approve':
            # Одобрение инцидента
            incident.status = 'approved'
            incident.points_awarded = points

            # Начисляем баллы пользователю
            user = User.query.get(incident.user_id)
            user.total_points += points

            flash('Инцидент одобрен! Баллы начислены.', 'success')

        elif action == 'reject':
            # Отклонение инцидента
            incident.status = 'rejected'
            flash('Инцидент отклонен!', 'danger')

        elif action == 'needs_revision':
            # Отправка на доработку
            incident.status = 'needs_revision'

            # Удаляем все скриншоты
            if incident.screenshots:
                for screenshot in incident.screenshots:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], screenshot)
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            logger.info(f"Удален файл: {file_path}")
                        except Exception as e:
                            logger.error(f"Ошибка при удалении файла {file_path}: {e}")
                    else:
                        logger.error(f"Файл не найден: {file_path}")

                # Очищаем список скриншотов в базе данных
                incident.screenshots = []  # Обнуляем список скриншотов
                logger.info("Все скриншоты удалены из базы данных.")

            flash('Инцидент отправлен на доработку! Скриншоты удалены.', 'warning')

        # Сохраняем изменения в базе данных
        incident.admin_id = current_user.id
        db.session.commit()

        return redirect(url_for('admin_incidents'))

    # Передаем инцидент и скриншоты в шаблон
    return render_template('admin/review_incident.html', incident=incident)





# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

import os
import logging
from flask import request, flash, redirect, url_for, render_template
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/edit_incident/<int:incident_id>', methods=['GET', 'POST'])
@login_required
def edit_incident(incident_id):
    # Получаем инцидент из базы данных
    incident = Incident.query.get_or_404(incident_id)
    logger.debug(f"Редактирование инцидента: {incident.id}")

    if request.method == 'POST':
        try:
            # Логируем данные формы и файлы
            logger.debug(f"Данные формы: {request.form}")
            logger.debug(f"Файлы: {request.files}")

            # Обновление данных инцидента
            incident.title = request.form['title']
            incident.description = request.form['description']
            incident.start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
            incident.end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
            incident.source_ip = request.form['source_ip']
            incident.source_port = int(request.form['source_port'])
            incident.destination_ip = request.form['destination_ip']
            incident.destination_port = int(request.form['destination_port'])
            incident.event_type = request.form['event_type']
            incident.related_fqdn = request.form['related_fqdn']
            incident.related_dns = request.form['related_dns']
            incident.ioc = request.form['ioc']
            incident.hash_value = request.form['hash_value']
            incident.mitre_id = request.form['mitre_id']
            incident.siem_id = request.form['siem_id']
            incident.siem_link = request.form['siem_link']
            incident.status = 'pending'  # Меняем статус на "pending" для повторной проверки
            incident = db.session.merge(incident)
            # Обработка загрузки новых скриншотов
            if 'screenshots' in request.files:
                files = request.files.getlist('screenshots')
                logger.debug(f"Получено файлов для загрузки: {len(files)}")

                for file in files:
                    if file.filename != '' and allowed_file(file.filename):
                        unique_filename = generate_unique_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        logger.debug(f"Путь для сохранения файла: {file_path}")

                        try:
                            file.save(file_path)

                            # Инициализируем список скриншотов, если он пустой
                            if incident.screenshots is None:
                                incident.screenshots = []

                            # Добавляем имя файла в список скриншотов
                            incident.screenshots.append(unique_filename)
                            logger.info(f"Добавлен новый скриншот: {unique_filename}")
                        except Exception as e:
                            logger.error(f"Ошибка при сохранении файла {unique_filename}: {e}")
                    else:
                        logger.error(f"Файл не прошел проверку: {file.filename}")

            # Логируем скриншоты перед сохранением
            logger.info(f"Скриншоты перед сохранением: {incident.screenshots}")

            # Привязываем объект к текущей сессии
            incident = db.session.merge(incident)

            # Сохраняем изменения в базе данных
            try:
                flag_modified(incident, 'screenshots')
                db.session.commit()
                logger.info(f"Скриншоты после сохранения: {incident.screenshots}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Ошибка при сохранении инцидента: {e}")
                flash('Произошла ошибка при сохранении инцидента.', 'danger')
            # Уведомляем пользователя об успешном обновлении
            flash('Инцидент обновлен и отправлен на проверку!', 'success')
            return redirect(url_for('my_incidents'))

        except Exception as e:
            # Логируем ошибку и уведомляем пользователя
            logger.error(f"Ошибка при редактировании инцидента: {e}")
            flash('Произошла ошибка при редактировании инцидента.', 'danger')
            return redirect(url_for('my_incidents'))

    # Отображаем форму редактирования
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

@app.route('/admin/critical_event_responses')
@login_required
def admin_critical_event_responses():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    # Получаем только отчёты, ожидающие проверки
    responses = CriticalEventResponse.query.filter_by(status='pending').all()
    return render_template('admin/critical_event_responses.html', responses=responses)

@app.route('/admin/approved_responses')
@login_required
def admin_approved_responses():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    # Получаем все принятые отчёты
    responses = CriticalEventResponse.query.filter_by(status='approved').all()
    return render_template('admin/approved_responses.html', responses=responses)

@app.route('/admin/critical_events')
@login_required
def admin_critical_events():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))

    # Получаем все КС, созданные администраторами
    events = CriticalEvent.query.join(User, CriticalEvent.created_by == User.id).filter(User.is_admin == True).all()
    return render_template('admin/critical_events.html', events=events)


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


@app.route('/admin/review_critical_event/<int:event_id>/<int:team_id>', methods=['GET', 'POST'])
@login_required
def review_critical_event(event_id, team_id):
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    # Получаем ответ на критическое событие для указанной команды
    response = CriticalEventResponse.query.filter_by(
        event_id=event_id,
        team_id=team_id
    ).first_or_404()

    # Получаем все шаги, связанные с этим событием и командой
    steps = CriticalEventStep.query.filter_by(
        event_id=event_id,
        team_id=team_id
    ).all()

    # Отладочный вывод
    print(f"Найдено шагов: {len(steps)}")
    for step in steps:
        print(f"Шаг: {step.step_name}, ID: {step.id}, Event ID: {step.event_id}, Team ID: {step.team_id}")

    if request.method == 'POST':
        action = request.form.get('action')
        points = int(request.form.get('points', 0))

        if action == 'approve':
            response.status = 'approved'
            response.points_awarded = points
            user = User.query.get(response.user_id)
            user.total_points += points
            flash('Отчёт принят! Баллы начислены.', 'success')
        elif action == 'reject':
            response.status = 'rejected'
            flash('Отчёт отклонён!', 'danger')
        elif action == 'needs_revision':
            response.status = 'needs_revision'
            CriticalEventStep.query.filter_by(event_id=event_id, team_id=team_id).delete()
            flash('Отчёт отправлен на доработку! Все шаги удалены.', 'warning')

        db.session.commit()
        return redirect(url_for('admin_critical_events'))

    return render_template('admin/review_critical_event.html', response=response, steps=steps)

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
            response.status = 'approved'
            response.points_awarded = points
            user = User.query.get(response.user_id)
            user.total_points += points
            flash('Отчёт принят! Баллы начислены.', 'success')
        elif action == 'reject':
            response.status = 'rejected'
            flash('Отчёт отклонён!', 'danger')
        elif action == 'needs_revision':
            response.status = 'needs_revision'
            CriticalEventStep.query.filter_by(event_id=response.event_id, team_id=response.team_id).delete()
            flash('Отчёт отправлен на доработку! Все шаги удалены.', 'warning')

        db.session.commit()
        return redirect(url_for('admin_critical_events'))
    print(steps)

    return render_template('admin/review_response.html', response=response, steps=steps)


@app.route('/edit_response/<int:response_id>', methods=['GET', 'POST'])
@login_required
def edit_response(response_id):
    response = CriticalEventResponse.query.get_or_404(response_id)

    # Проверяем, что отчет принадлежит текущему пользователю и его статус "needs_revision"
    if response.user_id != current_user.id or response.status != 'needs_revision':
        flash('You cannot edit this response.', 'danger')
        return redirect(url_for('user_pending_responses'))

    if request.method == 'POST':
        response.response = request.form['response']
        response.status = 'pending'  # Меняем статус на "pending" для повторной проверки
        db.session.commit()
        flash('Response updated and submitted for review!', 'success')
        return redirect(url_for('user_pending_responses'))

    return render_template('edit_response.html', response=response)

@app.route('/user/accepted_responses')
@login_required
def user_accepted_responses():
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
def user_pending_responses():
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
def user_under_review_responses():
    if not current_user.team:
        flash('Вы не состоите в команде.', 'warning')
        return redirect(url_for('index'))

    # Получаем отчёты команды пользователя, которые ожидают проверки
    responses = CriticalEventResponse.query.filter_by(
        team_id=current_user.team_id,
        status='pending'
    ).all()
    return render_template('user/under_review_responses.html', responses=responses)

@app.route('/fill_critical_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def fill_critical_event(event_id):
    event = CriticalEvent.query.get_or_404(event_id)
    response = CriticalEventResponse.query.filter_by(event_id=event.id, team_id=current_user.team_id).first()

    if request.method == 'POST':
        try:
            # Логирование данных формы
            logger.debug(f"Данные формы: {request.form}")
            logger.debug(f"Файлы: {request.files}")

            # Проверка обязательных полей
            step_names = request.form.getlist('step_name[]')
            start_times = request.form.getlist('start_time[]')
            source_ips = request.form.getlist('source_ip[]')
            destination_ips = request.form.getlist('destination_ip[]')
            event_types = request.form.getlist('event_type[]')

            for i, step_name in enumerate(step_names):
                if not step_name or not start_times[i] or not source_ips[i] or not destination_ips[i] or not event_types[i]:
                    flash('Все обязательные поля шага должны быть заполнены.', 'danger')
                    return redirect(url_for('fill_critical_event', event_id=event_id))

            # Обработка загрузки файлов для каждого шага
            screenshot_paths = {}
            for key, files in request.files.lists():
                if key.startswith('screenshots_step_'):
                    step_id = key.replace('screenshots_step_', '').replace('[]', '')
                    screenshot_paths[step_id] = []
                    for file in files:
                        if file.filename != '' and allowed_file(file.filename):
                            unique_filename = generate_unique_filename(file.filename)
                            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                            file.save(file_path)
                            screenshot_paths[step_id].append(unique_filename)
                            logger.debug(f"Файл {file.filename} сохранен как {unique_filename} для шага {step_id}")

            # Обновляем или создаем отчет
            if response:
                response.response = request.form['response']
                response.status = 'pending'  # Обновляем статус на "pending"
            else:
                response = CriticalEventResponse(
                    event_id=event.id,
                    user_id=current_user.id,
                    team_id=current_user.team_id,
                    response=request.form['response'],
                    status='pending'  # Устанавливаем статус "pending"
                )
                db.session.add(response)

            # Обработка шагов
            step_ids = request.form.getlist('step_id[]')
            descriptions = request.form.getlist('description[]')
            end_times = request.form.getlist('end_time[]')
            source_ports = request.form.getlist('source_port[]')
            destination_ports = request.form.getlist('destination_port[]')
            related_fqdns = request.form.getlist('related_fqdn[]')
            related_dns = request.form.getlist('related_dns[]')
            iocs = request.form.getlist('ioc[]')
            hash_values = request.form.getlist('hash_value[]')
            mitre_ids = request.form.getlist('mitre_id[]')
            siem_ids = request.form.getlist('siem_id[]')
            siem_links = request.form.getlist('siem_link[]')
            responsibles = request.form.getlist('responsible[]')
            deadlines = request.form.getlist('deadline[]')
            statuses = request.form.getlist('status[]')
            comments = request.form.getlist('comments[]')

            for i, step_id in enumerate(step_ids):
                if step_id:  # Обновление существующего шага
                    step = CriticalEventStep.query.get(step_id)
                    if step:
                        step.step_name = step_names[i]
                        step.description = descriptions[i]
                        step.start_time = datetime.strptime(start_times[i], '%Y-%m-%dT%H:%M')
                        step.end_time = datetime.strptime(end_times[i], '%Y-%m-%dT%H:%M') if end_times[i] else None
                        step.source_ip = source_ips[i]
                        step.source_port = int(source_ports[i]) if source_ports[i] else None
                        step.destination_ip = destination_ips[i]
                        step.destination_port = int(destination_ports[i]) if destination_ports[i] else None
                        step.event_type = event_types[i]
                        step.related_fqdn = related_fqdns[i]
                        step.related_dns = related_dns[i]
                        step.ioc = iocs[i]
                        step.hash_value = hash_values[i]
                        step.mitre_id = mitre_ids[i]
                        step.siem_id = siem_ids[i]
                        step.siem_link = siem_links[i]
                        step.screenshots = screenshot_paths.get(step_id, [])
                        step.responsible = responsibles[i]
                        step.deadline = datetime.strptime(deadlines[i], '%Y-%m-%dT%H:%M') if deadlines[i] else None
                        step.status = statuses[i]
                        step.comments = comments[i]
                else:  # Создание нового шага
                    step = CriticalEventStep(
                        event_id=event.id,
                        user_id=current_user.id,
                        team_id=current_user.team_id,
                        step_name=step_names[i],
                        description=descriptions[i],
                        start_time=datetime.strptime(start_times[i], '%Y-%m-%dT%H:%M'),
                        end_time=datetime.strptime(end_times[i], '%Y-%m-%dT%H:%M') if end_times[i] else None,
                        source_ip=source_ips[i],
                        source_port=int(source_ports[i]) if source_ports[i] else None,
                        destination_ip=destination_ips[i],
                        destination_port=int(destination_ports[i]) if destination_ports[i] else None,
                        event_type=event_types[i],
                        related_fqdn=related_fqdns[i],
                        related_dns=related_dns[i],
                        ioc=iocs[i],
                        hash_value=hash_values[i],
                        mitre_id=mitre_ids[i],
                        siem_id=siem_ids[i],
                        siem_link=siem_links[i],
                        screenshots=screenshot_paths.get(f"new_{i}", []),
                        responsible=responsibles[i],
                        deadline=datetime.strptime(deadlines[i], '%Y-%m-%dT%H:%M') if deadlines[i] else None,
                        status=statuses[i],
                        comments=comments[i]
                    )
                    db.session.add(step)

            # Удаление шагов, отмеченных для удаления
            removed_steps = request.form.getlist('removed_steps[]')
            for step_id in removed_steps:
                step = CriticalEventStep.query.get(step_id)
                if step:
                    db.session.delete(step)

            db.session.commit()
            flash('Отчет и шаги успешно сохранены и отправлены на проверку!', 'success')
            return redirect(url_for('user_pending_responses'))

        except IntegrityError as e:
            db.session.rollback()
            flash('Ошибка: Некоторые обязательные поля не заполнены.', 'danger')
            logger.error(f"Ошибка IntegrityError: {e}")
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при сохранении отчета.', 'danger')
            logger.error(f"Ошибка при сохранении в базу данных: {e}")

    steps = CriticalEventStep.query.filter_by(event_id=event.id, team_id=current_user.team_id).all()
    return render_template('user/fill_critical_event.html', event=event, response=response, steps=steps)

from flask import request, flash, redirect, url_for
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

@app.route('/add_steps/<int:event_id>', methods=['POST'])
@login_required
def add_steps(event_id):
    if not current_user.team:
        flash('Вы не состоите в команде.', 'warning')
        return redirect(url_for('index'))

    # Обработка загрузки скриншотов
    screenshot_paths = []
    if 'screenshots' in request.files:
        files = request.files.getlist('screenshots')
        for file in files:
            if file.filename != '' and allowed_file(file.filename):
                # Генерируем уникальное имя файла
                unique_filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                screenshot_paths.append(unique_filename)  # Сохраняем имя файла

    # Получаем данные из формы
    step_name = request.form.get('step_name')
    description = request.form.get('description')
    start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
    source_ip = request.form.get('source_ip')
    source_port = int(request.form.get('source_port')) if request.form.get('source_port') else None
    destination_ip = request.form.get('destination_ip')
    destination_port = int(request.form.get('destination_port')) if request.form.get('destination_port') else None
    event_type = request.form.get('event_type')
    related_fqdn = request.form.get('related_fqdn')
    related_dns = request.form.get('related_dns')
    ioc = request.form.get('ioc')
    hash_value = request.form.get('hash_value')
    mitre_id = request.form.get('mitre_id')
    siem_id = request.form.get('siem_id')
    siem_link = request.form.get('siem_link')
    responsible = request.form.get('responsible')
    deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%dT%H:%M') if request.form.get('deadline') else None
    status = request.form.get('status')
    comments = request.form.get('comments')

    # Создаем новый шаг
    step = CriticalEventStep(
        event_id=event_id,
        user_id=current_user.id,
        team_id=current_user.team_id,
        step_name=step_name,
        description=description,
        start_time=start_time,
        end_time=end_time,
        source_ip=source_ip,
        source_port=source_port,
        destination_ip=destination_ip,
        destination_port=destination_port,
        event_type=event_type,
        related_fqdn=related_fqdn,
        related_dns=related_dns,
        ioc=ioc,
        hash_value=hash_value,
        mitre_id=mitre_id,
        siem_id=siem_id,
        siem_link=siem_link,
        screenshots=screenshot_paths,
        responsible=responsible,
        deadline=deadline,
        status=status,
        comments=comments
    )
    db.session.add(step)
    db.session.commit()

    flash('Шаг успешно добавлен!', 'success')
    return redirect(url_for('fill_critical_event', event_id=event_id))

@app.route('/view_event/<int:event_id>')
@login_required
def view_event(event_id):
    event = CriticalEvent.query.get_or_404(event_id)
    return render_template('view_event.html', event=event)

@app.route('/fill_steps/<int:event_id>', methods=['GET', 'POST'])
@login_required
def fill_steps(event_id):
    event = CriticalEvent.query.get_or_404(event_id)

    if request.method == 'POST':
        # Обрабатываем данные из формы
        step_names = request.form.getlist('step_name[]')
        descriptions = request.form.getlist('description[]')
        responsibles = request.form.getlist('responsible[]')
        deadlines = request.form.getlist('deadline[]')
        resources = request.form.getlist('resources[]')
        risks = request.form.getlist('risks[]')
        actions = request.form.getlist('actions[]')
        results = request.form.getlist('results[]')
        statuses = request.form.getlist('status[]')
        comments = request.form.getlist('comments[]')

        # Сохраняем каждый шаг в базе данных
        for i in range(len(step_names)):
            step = CriticalEventStep(
                event_id=event.id,
                step_name=step_names[i],
                description=descriptions[i],
                responsible=responsibles[i],
                deadline=datetime.strptime(deadlines[i], '%Y-%m-%dT%H:%M') if deadlines[i] else None,
                resources=resources[i],
                risks=risks[i],
                actions=actions[i],
                results=results[i],
                status=statuses[i],
                comments=comments[i]
            )
            db.session.add(step)

        db.session.commit()
        flash('Шаги успешно сохранены!', 'success')
        return redirect(url_for('user_pending_responses'))

    return render_template('fill_steps.html', event=event)

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


@app.route('/create_user', methods=['GET', 'POST'])
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
            return redirect(url_for('create_user'))

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

    return render_template('admin/create_user.html')


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    return render_template('admin/admin_dashboard.html')



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
            points_change = int(request.form.get('points_change', 0))  # Изменение баллов

            user = User.query.get(user_id)
            if user:
                user.username = username
                user.email = email
                user.is_admin = is_admin
                user.team_id = team_id if team_id else None
                user.total_points += points_change  # Изменяем баллы
                db.session.commit()
                flash(f'Данные пользователя "{username}" успешно обновлены!', 'success')
                selected_user = user  # Обновляем выбранного пользователя

        # Обработка удаления пользователя
        elif 'delete_user' in request.form:
            user_id = request.form['user_id']
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()
                flash(f'Пользователь "{user.username}" успешно удален!', 'success')

    # Получаем список всех пользователей и команд
    users = User.query.all()
    teams = Team.query.all()
    return render_template('admin/manage_users.html', users=users, teams=teams, selected_user=selected_user)

@app.route('/view_incident/<int:incident_id>')
@login_required
def view_incident(incident_id):
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
