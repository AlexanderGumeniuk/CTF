from flask import render_template, url_for, flash, redirect, request
from app import app, db
from app.models import User, Challenge, UserChallenge, Team, Incident, CriticalEvent, CriticalEventResponse,CriticalEventStep,Infrastructure,PointsHistory,FlagResponse,SherlockSubmission
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
from . import sherlocks

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
            # Редирект для администратора
            if user.is_admin:
                return redirect(url_for('admin'))

            # Редирект для обычных пользователей
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

    return render_template('admin.html',
                           team_stats=team_stats,
                           solved_flags=solved_flags,
                           unsolved_flags=unsolved_flags,
                           critical_events_stats=critical_events_stats,
                           incidents_stats=incidents_stats)

  # Импортируем модель PointsHistory

@app.route('/submit_flag/<int:challenge_id>', methods=['POST'])
@login_required
def submit_flag(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    user_flag = request.form['flag']

    # Проверяем, состоит ли пользователь в команде
    if not current_user.team:
        flash('Вы не состоите в команде. Ответы принимаются только от команд.', 'danger')
        return redirect(url_for('competition_challenges', competition_id=challenge.competition_id))

    # Проверяем, сколько попыток уже использовано командой
    attempts_used = FlagResponse.query.filter_by(
        team_id=current_user.team_id,
        challenge_id=challenge_id

    ).count()

    attempts_used1 = FlagResponse.query.filter_by(
        team_id=current_user.team_id,
        challenge_id=challenge_id,
        is_correct=True
    ).count()
    if attempts_used1 >= 1:
        flash('Ваша команда Уже ответила на флаг.', 'danger')
        return redirect(url_for('competition_challenges', competition_id=challenge.competition_id))
    logger.debug(f"Проверка инцидента: {attempts_used1}")
    if attempts_used >= challenge.max_attempts:
        flash('Ваша команда исчерпала все попытки для этой задачи.', 'danger')
        return redirect(url_for('competition_challenges', competition_id=challenge.competition_id))

    # Проверяем, правильный ли флаг
    is_correct = (user_flag == challenge.flag)

    # Сохраняем ответ команды
    response = FlagResponse(
        user_id=current_user.id,
        team_id=current_user.team_id,
        challenge_id=challenge_id,
        response=user_flag,
        flag=challenge.flag,
        is_correct=is_correct
    )
    db.session.add(response)


        # Проверяем, решил ли пользователь задачу ранее
    user_challenge = UserChallenge.query.filter_by(team_id=current_user.team.id, challenge_id=challenge_id).first()
    if is_correct:
        if not user_challenge:
            # Отмечаем задачу как решённую для текущего пользователя
            user_challenge = UserChallenge(
                user_id=current_user.id,
                team_id=current_user.team.id,
                challenge_id=challenge_id,
                solved=True
            )
            db.session.add(user_challenge)
        # Начисляем баллы всем членам команды
        team_members = User.query.filter_by(team_id=current_user.team_id).all()
        current_user.team.total_points += challenge.points
        for member in team_members:
            #member.team.total_points += challenge.points

            # Добавляем запись в историю начисления баллов
            points_history = PointsHistory(
                user_id=member.id,
                points=challenge.points,
                note=f"За решение задачи: {challenge.title}"
            )
            db.session.add(points_history)

        flash('Правильный флаг! Задача решена вашей командой.', 'success')
    else:
        flash('Неправильный флаг. Попробуйте еще раз.', 'danger')

    db.session.commit()
    return redirect(url_for('competition_challenges', competition_id=challenge.competition_id))

@app.route('/leaderboard')
@login_required
def leaderboard():
    # Запрашиваем данные пользователей, исключая администраторов
    leaderboard_data = db.session.query(
        User.username,
        User.total_points,
        User.avatar  # Добавляем поле avatar
    ).filter(User.is_admin == False).order_by(User.total_points.desc()).all()

    return render_template('leaderboard.html', leaderboard=leaderboard_data)

@app.route('/team_leaderboard')
@login_required
def team_leaderboard():
    # Получаем данные для таблицы лидеров
    leaderboard_data = db.session.query(
        Team.name,
        Team.total_points
    ).order_by(Team.total_points.desc()) \
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
                SherlockSubmission.query.filter_by(user_id=user.id).delete()
                db.session.delete(user)
                db.session.commit()
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




@app.route('/download/<filename>')
@login_required
def download_file1(filename):
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
@app.route('/profile/<username>')
@login_required
def view_profile(username):
    # Находим пользователя по имени
    user = User.query.filter_by(username=username).first_or_404()

    # Проверяем, что пользователь не администратор (если нужно)
    if user.is_admin:
        return "Профиль администратора недоступен для просмотра.", 403

    # Получаем команду пользователя (если есть)
    team = Team.query.get(user.team_id) if user.team_id else None

    # Получаем список решенных шерлоков


    return render_template(
        'user/profile_user.html',
        user=user,
        team=team,

    )
