from app import app, db
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models import User, Challenge, UserChallenge, Team, Incident, CriticalEvent, CriticalEventResponse,CriticalEventStep,Infrastructure,PointsHistory, Competition, db,FlagResponse
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from sqlalchemy.orm.attributes import flag_modified
import os
import json
from flask import current_app, flash, redirect, url_for
from app.models import CriticalEvent, CriticalEventResponse
from app import db
from flask_uploads import UploadNotAllowed
import uuid
import logging
from sqlalchemy.exc import IntegrityError
import base64
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from app.models import Competition
import re


def extract_number(title):
    numbers = re.findall(r'\d+', title)
    if numbers:
        return int(numbers[0])  # Возвращаем первое найденное число
    return 0  # Если числа нет, возвращаем 0

def update_competition_status(competition):
    """
    Автоматически обновляет статус соревнования на основе текущей даты.
    """
    now = datetime.utcnow()

    if competition.start_date > now:
        # Соревнование еще не началось
        competition.status = 'planned'
    elif competition.end_date < now:
        # Соревнование завершено
        competition.status = 'finished'
    else:
        # Соревнование активно
        competition.status = 'active'

    # Сохраняем изменения в базе данных
    db.session.commit()
# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
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

def generate_unique_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()  # Получаем расширение файла
    unique_name = f"{uuid.uuid4().hex}.{ext}"  # Генерируем уникальное имя
    return unique_name

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('У вас нет прав доступа к этой странице.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function



def active_competition_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        competition_id = kwargs.get('competition_id')
        competition = Competition.query.get_or_404(competition_id)

        if competition.status != 'active':
            if competition.status == 'planned':
                flash('Соревнование еще не началось.', 'warning')
            elif competition.status == 'finished':
                flash('Соревнование уже завершено.', 'warning')
            return redirect(url_for('user_competitions', competition_id=competition_id))

        return f(*args, **kwargs)
    return decorated_function

# Маршрут для создания соревнования
@app.route('/admin/competitions/create', methods=['GET', 'POST'])
@login_required
def create_competition():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M')

        competition = Competition(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status='planned'
        )
        db.session.add(competition)
        db.session.commit()
        flash('Соревнование успешно создано!', 'success')
        return redirect(url_for('list_competitions'))

    return render_template('competitions/create_competition.html')
# Маршрут для просмотра списка соревнований
@app.route('/admin/competitions')
@login_required
def list_competitions():
    competitions = Competition.query.all()
    return render_template('competitions/admin/list_competitions.html', competitions=competitions)
# Маршрут для редактирования соревнования
@app.route('/admin/competitions/edit/<int:competition_id>', methods=['GET', 'POST'])
@login_required
def edit_competition(competition_id):
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    competition = Competition.query.get_or_404(competition_id)

    if request.method == 'POST':
        competition.title = request.form['title']
        competition.description = request.form['description']
        competition.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M')
        competition.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M')
        db.session.commit()
        flash('Соревнование успешно обновлено!', 'success')
        return redirect(url_for('list_competitions'))

    return render_template('competitions/edit_competition.html', competition=competition)
# Маршрут для удаления соревнования
@app.route('/admin/competitions/delete/<int:competition_id>', methods=['POST'])
@login_required
def delete_competition(competition_id):
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    competition = Competition.query.get_or_404(competition_id)
    db.session.delete(competition)
    db.session.commit()
    flash('Соревнование успешно удалено!', 'success')
    return redirect(url_for('list_competitions'))

@app.route('/admin/competitions/view/<int:competition_id>')
@login_required
@admin_required
def view_competition(competition_id):
    # Получаем соревнование по ID
    competition = Competition.query.get_or_404(competition_id)
    update_competition_status(competition)
    # Статистика по флагам
    total_flags = Challenge.query.filter_by(competition_id=competition_id).count()

    # Статистика по инцидентам
    total_incidents = Incident.query.filter_by(competition_id=competition_id).count()

    # Статистика по критическим событиям
    total_critical_events = CriticalEvent.query.filter_by(competition_id=competition_id).count()

    # Статистика по командам и пользователям
    # Получаем всех пользователей, участвующих в соревновании
    users = User.query.join(Team).filter(Team.competition_id == competition_id).distinct().count()
    # Получаем все команды, участвующие в соревновании
    teams = Team.query.filter_by(competition_id=competition_id).count()

    return render_template(
        'competitions/admin/view_competition.html',
        competition=competition,
        total_flags=total_flags,
        total_incidents=total_incidents,
        total_critical_events=total_critical_events,
        total_users=users,
        total_teams=teams
    )
from flask import jsonify

@app.route('/admin/competitions/<int:competition_id>/add_flag', methods=['POST'])
@login_required
def add_flag_to_competition(competition_id):
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "У вас нет прав доступа к этой странице."}), 403

    try:
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Нет данных для обработки."}), 400

        title = data.get("title")
        description = data.get("description")
        flag = data.get("flag")
        points = data.get("points")
        category = data.get("category")
        max_attempts = data.get("max_attempts")

        # Проверяем, что все поля заполнены
        if not all([title, description, flag, points, category]):
            return jsonify({"success": False, "message": "Все поля обязательны для заполнения."}), 400

        # Проверяем, что соревнование существует
        competition = Competition.query.get_or_404(competition_id)

        # Создаем новый флаг
        challenge = Challenge(
            title=title,
            description=description,
            flag=flag,
            points=points,
            category=category,
            max_attempts=max_attempts,
            competition_id=competition_id
        )
        db.session.add(challenge)
        db.session.commit()

        return jsonify({"success": True, "message": "Флаг успешно добавлен."}), 200

    except Exception as e:
        db.session.rollback()
        # Логируем ошибку для отладки
        print(f"Ошибка при добавлении флага: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка при добавлении флага: {str(e)}"}), 500

@app.route('/admin/competitions/<int:competition_id>/edit_flag/<int:challenge_id>', methods=['POST'])
@login_required
def edit_flag_in_competition(competition_id, challenge_id):
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "У вас нет прав доступа к этой странице."})

    # Получаем данные из запроса
    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    flag = data.get("flag")
    points = data.get("points")
    category = data.get("category")
    max_attempts = data.get("max_attempts")

    if not all([title, description, flag, points, category]):
        return jsonify({"success": False, "message": "Все поля обязательны для заполнения."})

    # Находим задачу по ID и проверяем, что она принадлежит соревнованию
    challenge = Challenge.query.filter_by(id=challenge_id, competition_id=competition_id).first_or_404()

    try:
        # Обновляем данные задачи
        challenge.title = title
        challenge.description = description
        challenge.flag = flag
        challenge.points = points
        challenge.max_attempts = max_attempts
        challenge.category = category
        db.session.commit()
        return jsonify({"success": True, "message": "Флаг успешно обновлен."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Ошибка при обновлении флага: {str(e)}"})

@app.route('/admin/competitions/<int:competition_id>/delete_flag/<int:challenge_id>', methods=['POST'])
@login_required
def delete_flag_from_competition(competition_id, challenge_id):
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "У вас нет прав доступа к этой странице."})

    # Находим задачу по ID и проверяем, что она принадлежит соревнованию
    challenge = Challenge.query.filter_by(id=challenge_id, competition_id=competition_id).first_or_404()

    try:
        # Удаляем задачу (каскадное удаление удалит связанные записи)
        db.session.delete(challenge)
        db.session.commit()
        return jsonify({"success": True, "message": "Флаг и все связанные данные успешно удалены из соревнования."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Ошибка при удалении флага: {str(e)}"})

@app.route('/admin/competitions/<int:competition_id>/flags', methods=['GET'])
@login_required
def view_flags_in_competition(competition_id):
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    # Получаем соревнование по ID
    competition = Competition.query.get_or_404(competition_id)

    # Получаем все флаги, связанные с этим соревнованием
    flags = Challenge.query.filter_by(competition_id=competition_id).all()
    challenges = Challenge.query.filter_by(competition_id=competition_id).all()
    challenges = sorted(challenges, key=lambda x: extract_number(x.title))
    #sorted_challenges = sorted(challenges, key=lambda x: extract_number(x['title']))
    return render_template(
        'competitions/admin/flags_in_competition.html',
        competition=competition,
        flags=challenges  # Передаем флаги в шаблон
    )

@app.route('/admin/competitions/<int:competition_id>/add_team', methods=['GET', 'POST'])
@login_required
@admin_required
def add_team_to_competition(competition_id):
    # Получаем соревнование по ID
    competition = Competition.query.get_or_404(competition_id)
    con_team = Team.query.filter_by(competition_id=competition_id).all()
    if request.method == 'POST':
        # Получаем ID команды из формы
        team_id = request.form.get('team_id')

        if not team_id:
            flash('Не выбрана команда.', 'danger')
            return redirect(url_for('add_team_to_competition', competition_id=competition_id))

        # Находим команду по ID
        team = Team.query.get_or_404(team_id)

        # Проверяем, что команда еще не добавлена в соревнование
        if team.competition_id == competition_id:
            flash(f'Команда "{team.name}" уже участвует в этом соревновании.', 'warning')
            return redirect(url_for('add_team_to_competition', competition_id=competition_id))

        # Добавляем команду в соревнование
        team.competition_id = competition_id
        db.session.commit()

        flash(f'Команда "{team.name}" успешно добавлена в соревнование!', 'success')
        return redirect(url_for('view_competition', competition_id=competition_id))

    # Получаем список всех команд, которые еще не участвуют в этом соревновании
    teams = Team.query.filter((Team.competition_id != competition_id) | (Team.competition_id.is_(None))).all()
    logger.error(f"Ошибка IntegrityError: {con_team}")
    return render_template('competitions/admin/add_team_to_competition.html', competition=competition, teams=teams,con_team=con_team)

@app.route('/admin/competitions/<int:competition_id>/remove_team/<int:team_id>', methods=['POST'])
@login_required
@admin_required
def remove_team_from_competition(competition_id, team_id):
    competition = Competition.query.get_or_404(competition_id)
    team = Team.query.get_or_404(team_id)

    # Проверяем, что команда участвует в этом соревновании
    if team.competition_id != competition_id:
        flash('Команда не участвует в этом соревновании.', 'warning')
        return redirect(url_for('add_team_to_competition', competition_id=competition_id))

    # Удаляем команду из соревнования (сбрасываем competition_id)
    team.competition_id = None
    db.session.commit()

    flash(f'Команда "{team.name}" успешно удалена из соревнования!', 'success')
    return redirect(url_for('add_team_to_competition', competition_id=competition_id))
@app.route('/competitions')
@login_required
def user_competitions():
    # Получаем все активные соревнования
    active_competitions = Competition.query.filter(
        Competition.status == 'active'
    ).all()

    # Получаем завершенные соревнования
    finished_competitions = Competition.query.filter(
        Competition.status == 'finished'
    ).all()

    # Получаем запланированные соревнования
    planned_competitions = Competition.query.filter(
        Competition.status == 'planned'
    ).all()

    return render_template(
        'competitions/user/user_competitions.html',
        active_competitions=active_competitions,
        finished_competitions=finished_competitions,
        planned_competitions=planned_competitions
    )

@app.route('/competitions/<int:competition_id>')
@login_required
@active_competition_required
def view_user_competition(competition_id):
    # Получаем соревнование по ID
    competition = Competition.query.get_or_404(competition_id)
    update_competition_status(competition)
    # Проверяем, что пользователь участвует в этом соревновании
    if not current_user.team or current_user.team.competition_id != competition_id:
        flash('Вы не участвуете в этом соревновании.', 'danger')
        return redirect(url_for('user_competitions'))

    # Получаем инциденты, связанные с этим соревнованием
    incidents = Incident.query.filter_by(competition_id=competition_id, team_id=current_user.team_id).all()

    # Получаем критические события, связанные с этим соревнованием
    critical_events = CriticalEvent.query.filter_by(competition_id=competition_id).all()

    return render_template(
        'competitions/view_user_competition.html',
        competition=competition,
        incidents=incidents,
        critical_events=critical_events
    )

@app.route('/admin/competitions/<int:competition_id>/flag_responses')
@login_required
@admin_required
def admin_flag_responses(competition_id):
    # Получаем соревнование
    competition = Competition.query.get_or_404(competition_id)

    # Получаем все команды, участвующие в соревновании
    teams = Team.query.filter_by(competition_id=competition_id).all()

    # Получаем выбранную команду из параметра запроса
    selected_team_id = request.args.get('team_id', type=int)
    selected_team = Team.query.get(selected_team_id) if selected_team_id else None

    # Собираем данные о ответах на флаги для каждой команды
    team_responses = []
    for team in teams:
        # Если выбрана конкретная команда, пропускаем остальные
        if selected_team_id and team.id != selected_team_id:
            continue

        # Получаем все ответы команды на флаги, которые связаны с задачами этого соревнования
        responses = (
            db.session.query(FlagResponse)
            .join(Challenge, FlagResponse.challenge_id == Challenge.id)
            .filter(
                FlagResponse.team_id == team.id,
                Challenge.competition_id == competition_id
            )
            .all()
        )

        # Группируем ответы по задачам
        challenge_responses = {}
        for response in responses:
            if response.challenge_id not in challenge_responses:
                challenge_responses[response.challenge_id] = []
            challenge_responses[response.challenge_id].append(response)

        # Добавляем данные команды в список
        team_responses.append({
            'team': team,
            'responses': challenge_responses
        })

    return render_template(
        'competitions/admin/flag_responses.html',
        competition=competition,
        teams=teams,
        team_responses=team_responses,
        selected_team_id=selected_team_id
    )
    
@app.route('/competitions/<int:competition_id>/challenges', defaults={'filter': 'all'})
@app.route('/competitions/<int:competition_id>/challenges/<filter>')
@login_required
@active_competition_required
def competition_challenges(competition_id, filter):
    # Получаем соревнование по ID
    competition = Competition.query.get_or_404(competition_id)

    # Проверяем, что пользователь участвует в этом соревновании
    if not current_user.team or current_user.team.competition_id != competition_id:
        flash('Вы не участвуете в этом соревновании.', 'danger')
        return redirect(url_for('user_competitions'))

    # Получаем все задачи для этого соревнования
    challenges = Challenge.query.filter_by(competition_id=competition_id).all()
    blocked_challenge_ids = []
    for challenge in challenges:
        attempts_used = FlagResponse.query.filter_by(
            team_id=current_user.team_id,
            challenge_id=challenge.id
        ).count()

        if attempts_used == challenge.max_attempts:
            blocked_challenge_ids.append(challenge.id)

    # Получаем ID решенных задач текущего пользователя
    solved_challenge_ids = [
        uc.challenge_id for uc in UserChallenge.query.filter_by(
            team_id=current_user.team.id,
            solved=True
        ).all()
    ]

    # Фильтруем задачи в зависимости от параметра filter
    if filter == 'solved':
        challenges = [challenge for challenge in challenges if challenge.id in solved_challenge_ids]
    elif filter == 'unsolved':
        challenges = [challenge for challenge in challenges if (challenge.id not in solved_challenge_ids) and (challenge.id  not in blocked_challenge_ids)]
    elif filter == 'blocked':
        challenges = [challenge for challenge in challenges if challenge.id  in blocked_challenge_ids]

    # Сортируем задачи по числовому значению в названии
    challenges = sorted(challenges, key=lambda x: extract_number(x.title))

    # Получаем список решенных задач для отображения статуса
    solved_challenges = [challenge for challenge in challenges if challenge.id in solved_challenge_ids]
    blocked_challenge = [challenge for challenge in challenges if challenge.id  in blocked_challenge_ids]
    return render_template(
        'competitions/user/competition_challenges.html',
        competition=competition,
        challenges=challenges,
        solved_challenges=solved_challenges,
        blocked_challenge = blocked_challenge,
        filter_type=filter  # Передаем текущий фильтр в шаблон
    )


@app.route('/admin/competitions/<int:competition_id>/team_stats')
@login_required
@admin_required
def admin_competition_team_stats(competition_id):
    # Получаем соревнование по ID
    competition = Competition.query.get_or_404(competition_id)

    # Получаем все команды, участвующие в соревновании
    teams = Team.query.filter_by(competition_id=competition_id).all()

    # Собираем статистику по каждой команде
    team_stats = []
    for team in teams:
        # Получаем всех участников команды
        members = User.query.filter_by(team_id=team.id).all()

        # Считаем общее количество баллов команды
        total_points = sum(member.total_points for member in members)

        # Считаем количество решенных задач
        solved_challenges = UserChallenge.query.filter(
            UserChallenge.team_id == team.id,
            UserChallenge.solved == True
        ).count()

        # Считаем количество инцидентов
        incidents = Incident.query.filter_by(team_id=team.id).count()

        # Считаем количество критических событий
        critical_events = CriticalEventResponse.query.filter_by(team_id=team.id).count()

        # Добавляем статистику команды в список
        team_stats.append({
            'team': team,
            'members': members,
            'total_points': total_points,
            'solved_challenges': solved_challenges,
            'incidents': incidents,
            'critical_events': critical_events
        })

    return render_template(
        'competitions/admin/team_stats.html',
        competition=competition,
        team_stats=team_stats
    )

@app.route('/admin/competitions/<int:competition_id>/teams/<int:team_id>')
@login_required
@admin_required
def view_team_details(competition_id, team_id):
    # Получаем соревнование и команду
    competition = Competition.query.get_or_404(competition_id)
    team = Team.query.get_or_404(team_id)

    # Проверяем, что команда участвует в этом соревновании
    if team.competition_id != competition_id:
        flash('Эта команда не участвует в данном соревновании.', 'danger')
        return redirect(url_for('admin_competition_team_stats', competition_id=competition_id))

    # Получаем всех участников команды
    members = User.query.filter_by(team_id=team.id).all()

    # Получаем решенные задачи командой
    solved_challenges = UserChallenge.query.filter(
        UserChallenge.team_id == team.id,
        UserChallenge.solved == True
    ).all()

    # Получаем инциденты команды
    incidents = Incident.query.filter_by(team_id=team.id).all()

    # Получаем отчеты по критическим событиям
    critical_event_responses = CriticalEventResponse.query.filter_by(team_id=team.id).all()

    return render_template(
        'competitions/admin/view_team_details.html',
        competition=competition,
        team=team,
        members=members,
        solved_challenges=solved_challenges,
        incidents=incidents,
        critical_event_responses=critical_event_responses
    )
###########################################################Incident####################################################################
@app.route('/competitions/<int:competition_id>/create_incident', methods=['GET', 'POST'])
@login_required
@active_competition_required
def create_incident(competition_id):
    competition = Competition.query.get_or_404(competition_id)

    # Проверяем, что пользователь участвует в соревновании
    if not current_user.team or current_user.team.competition_id != competition_id:
        flash('Вы не участвуете в этом соревновании.', 'danger')
        return redirect(url_for('user_competitions'))

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
            team_id=current_user.team_id,
            competition_id=competition_id,
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
            status='pending'
        )
        db.session.add(incident)
        db.session.commit()
        flash('Инцидент успешно создан и отправлен на проверку!', 'success')
        return redirect(url_for('view_user_competition', competition_id=competition_id))

    return render_template('competitions/user/create_incident.html', competition=competition)

@app.route('/competitions/<int:competition_id>/incidents')
@login_required
def view_competition_incidents(competition_id):
    competition = Competition.query.get_or_404(competition_id)

    # Проверяем, что пользователь участвует в соревновании
    if not current_user.team or current_user.team.competition_id != competition_id:
        flash('Вы не участвуете в этом соревновании.', 'danger')
        return redirect(url_for('user_competitions'))

    # Получаем параметр status из запроса
    status = request.args.get('status', 'all')  # По умолчанию 'all'

    # Базовый запрос для инцидентов
    incidents_query = Incident.query.filter_by(competition_id=competition_id, team_id=current_user.team_id)

    # Фильтрация по статусу
    if status != 'all':
        incidents_query = incidents_query.filter_by(status=status)

    # Получаем отфильтрованные инциденты
    incidents = incidents_query.all()

    return render_template('competition_incidents.html', competition=competition, incidents=incidents, status=status)

@app.route('/admin/competitions/<int:competition_id>/review_incident/<int:incident_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def review_incident(competition_id, incident_id):
    # Получаем соревнование и инцидент
    competition = Competition.query.get_or_404(competition_id)
    if not current_user.is_admin:
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('index'))

    # Получаем инцидент по ID
    incident = Incident.query.get_or_404(incident_id)
    logger.debug(f"Проверка инцидента: {incident.id}")

    if request.method == 'POST':
        # Проверяем, что инцидент находится в статусе "pending" (ожидает проверки)
        if incident.status != 'pending':
            flash('Этот инцидент уже был проверен и не может быть изменен.', 'warning')
            return redirect(url_for('admin_incidents'))

        action = request.form['action']
        points = int(request.form.get('points', 0))

        if action == 'approve':
            # Одобрение инцидента
            incident.status = 'approved'
            incident.points_awarded = points

            # Начисляем баллы пользователю
            user = User.query.get(incident.user_id)
            user.total_points += points

            # Добавляем запись в историю начисления баллов
            points_history = PointsHistory(
                user_id=incident.user_id,
                points=points,
                note=f"За инцидент: {incident.title}"
            )
            db.session.add(points_history)

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

        return redirect(url_for('admin_competition_incidents', competition_id=competition_id))


    return render_template('admin/review_incident.html', competition=competition, incident=incident)

@app.route('/admin/competitions/<int:competition_id>/incidents')
@login_required
@admin_required
def admin_competition_incidents(competition_id):
    # Получаем соревнование по ID
    competition = Competition.query.get_or_404(competition_id)

    # Получаем статус для фильтрации (если передан)
    status = request.args.get('status', 'all')  # По умолчанию показываем все инциденты

    # Фильтруем инциденты по статусу
    if status == 'all':
        incidents = Incident.query.filter_by(competition_id=competition_id).all()
    else:
        incidents = Incident.query.filter_by(competition_id=competition_id, status=status).all()

    return render_template(
        'competitions/admin/competition_incidents.html',
        competition=competition,
        incidents=incidents,
        status=status
    )


@app.route('/competitions/<int:competition_id>/incidents')
@login_required
@active_competition_required
def user_competition_incidents(competition_id):
    # Получаем соревнование по ID
    competition = Competition.query.get_or_404(competition_id)

    # Проверяем, что пользователь участвует в этом соревновании
    if not current_user.team or current_user.team.competition_id != competition_id:
        flash('Вы не участвуете в этом соревновании.', 'danger')
        return redirect(url_for('user_competitions'))

    # Получаем статус для фильтрации (если передан)
    status = request.args.get('status', 'all')  # По умолчанию показываем все инциденты

    # Фильтруем инциденты по статусу и команде пользователя
    if status == 'all':
        incidents = Incident.query.filter_by(
            competition_id=competition_id,
            team_id=current_user.team_id
        ).all()
    else:
        incidents = Incident.query.filter_by(
            competition_id=competition_id,
            team_id=current_user.team_id,
            status=status
        ).all()

    return render_template(
        'competitions/user/competition_incidents.html',
        competition=competition,
        incidents=incidents,
        status=status
    )


@app.route('/competitions/<int:competition_id>/incidents/<int:incident_id>/edit', methods=['GET', 'POST'])
@login_required
@active_competition_required
def edit_incident(competition_id, incident_id):
    # Получаем соревнование и инцидент
    competition = Competition.query.get_or_404(competition_id)
    incident = Incident.query.get_or_404(incident_id)
    incident = db.session.merge(incident)

    # Проверяем, что инцидент принадлежит команде пользователя
    if not current_user.team or incident.team_id != current_user.team_id:
        flash('У вас нет доступа к этому инциденту.', 'danger')
        return redirect(url_for('user_competition_incidents', competition_id=competition_id))

    # Проверяем, что инцидент можно редактировать (статус "Требует доработки")
    if incident.status != 'needs_revision':
        flash('Этот инцидент нельзя редактировать.', 'warning')
        return redirect(url_for('view_incident', competition_id=competition_id, incident_id=incident_id))

    if request.method == 'POST':
        # Обновляем данные инцидента
        incident.title = request.form['title']
        incident.description = request.form['description']
        incident.start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
        incident.end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
        incident.source_ip = request.form['source_ip']
        incident.source_port = int(request.form['source_port']) if request.form['source_port'] else None
        incident.destination_ip = request.form['destination_ip']
        incident.destination_port = int(request.form['destination_port']) if request.form['destination_port'] else None
        incident.event_type = request.form['event_type']
        incident.related_fqdn = request.form['related_fqdn']
        incident.related_dns = request.form['related_dns']
        incident.ioc = request.form['ioc']
        incident.hash_value = request.form['hash_value']
        incident.mitre_id = request.form['mitre_id']
        incident.siem_id = request.form['siem_id']
        incident.siem_link = request.form['siem_link']
        incident.status = 'pending'
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
        #logger.info(f"Скриншоты перед сохранением: {incident.screenshots}")

        # Привязываем объект к текущей сессии
        incident = db.session.merge(incident)

        # Сохраняем изменения в базе данных
        try:
            flag_modified(incident, 'screenshots')
            db.session.commit()
            logger.info(f"Скриншоты после сохранения: {incident.screenshots}")
            return render_template('competitions/user/view_incident.html', competition=competition, incident=incident)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при сохранении инцидента: {e}")
            flash('Произошла ошибка при сохранении инцидента.', 'danger')
        # Уведомляем пользователя об успешном обновлении
        flash('Инцидент обновлен и отправлен на проверку!', 'success')



# Отображаем форму редактирования
    return render_template('competitions/user/edit_incident.html', competition=competition, incident=incident)


@app.route('/competitions/<int:competition_id>/incidents/<int:incident_id>')
@login_required
@active_competition_required
def view_incident(competition_id, incident_id):
    competition = Competition.query.get_or_404(competition_id)
    incident = Incident.query.get_or_404(incident_id)

    # Проверяем, что инцидент принадлежит текущему пользователю или его команде
    if not current_user.team or incident.team_id != current_user.team_id:
        flash('У вас нет доступа к этому инциденту.', 'danger')
        return redirect(url_for('user_competitions'))

    # Если статус "needs_revision", перенаправляем на редактирование
    if incident.status == 'needs_revision':
        return redirect(url_for('edit_incident', competition_id=competition_id, incident_id=incident_id))


    # Иначе показываем страницу просмотра
    return render_template('competitions/user/view_incident.html', competition=competition, incident=incident)

###################################CriticalEvent###############################################################################
@app.route('/admin/competitions/<int:competition_id>/critical_events')
@login_required
@admin_required
def admin_competition_critical_events(competition_id):
    # Получаем соревнование по ID
    competition = Competition.query.get_or_404(competition_id)

    # Получаем все КС для этого соревнования
    critical_events = CriticalEvent.query.filter_by(competition_id=competition_id).all()

    return render_template(
        'competitions/admin/list_critical_events.html',
        competition=competition,
        critical_events=critical_events
    )
@app.route('/competitions/<int:competition_id>/critical_events')
@login_required
def list_critical_events(competition_id):
    # Получаем соревнование
    competition = Competition.query.get_or_404(competition_id)

    # Получаем все критические события для этого соревнования
    critical_events = CriticalEvent.query.filter_by(competition_id=competition_id).all()

    # Получаем текущую команду пользователя
    user_team = current_user.team

    # Если пользователь состоит в команде, получаем отчеты его команды
    team_reports = []
    if user_team:
        team_reports = CriticalEventResponse.query.filter_by(
            team_id=user_team.id,
            competition_id=competition_id
        ).all()

    return render_template(
        'competitions/user/list_critical_events.html',
        competition=competition,
        critical_events=critical_events,
        team_reports=team_reports  # Передаем отчеты команды в шаблон
    )

# Маршрут для создания нового КС (только для администратора)
@app.route('/admin/competitions/<int:competition_id>/critical_events/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_critical_event(competition_id):
    competition = Competition.query.get_or_404(competition_id)

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        critical_event = CriticalEvent(
            title=title,
            description=description,
            competition_id=competition_id,
            created_by=current_user.id
        )
        db.session.add(critical_event)
        db.session.commit()
        flash('Критическое событие успешно создано!', 'success')
        return redirect(url_for('admin_competition_critical_events', competition_id=competition_id))

    return render_template('competitions/admin/create_critical_event.html', competition=competition)

# Маршрут для просмотра деталей КС
@app.route('/admin/competitions/<int:competition_id>/critical_events/<int:critical_event_id>')
@login_required
def view_critical_event(competition_id, critical_event_id):
    competition = Competition.query.get_or_404(competition_id)
    critical_event = CriticalEvent.query.get_or_404(critical_event_id)
    return render_template('competitions/admin/view_critical_event.html', competition=competition, critical_event=critical_event)

# Маршрут для редактирования КС (только для администратора)
@app.route('/admin/competitions/<int:competition_id>/critical_events/<int:critical_event_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_critical_event(competition_id, critical_event_id):
    competition = Competition.query.get_or_404(competition_id)
    critical_event = CriticalEvent.query.get_or_404(critical_event_id)

    if request.method == 'POST':
        critical_event.title = request.form['title']
        critical_event.description = request.form['description']
        db.session.commit()
        flash('Критическое событие успешно обновлено!', 'success')
        return redirect(url_for('view_critical_event', competition_id=competition_id, critical_event_id=critical_event_id))

    return render_template('competitions/admin/edit_critical_event.html', competition=competition, critical_event=critical_event)

# Маршрут для удаления КС (только для администратора)
@app.route('/admin/competitions/<int:competition_id>/critical_events/<int:critical_event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_critical_event(competition_id, critical_event_id):
    competition = Competition.query.get_or_404(competition_id)
    critical_event = CriticalEvent.query.get_or_404(critical_event_id)

    db.session.delete(critical_event)
    db.session.commit()
    flash('Критическое событие успешно удалено!', 'success')
    return redirect(url_for('admin_competition_critical_events', competition_id=competition_id))

@app.route('/competitions/<int:competition_id>/fill_critical_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def fill_critical_event(competition_id, event_id):
    competition = Competition.query.get_or_404(competition_id)
    event = CriticalEvent.query.get_or_404(event_id)

    # Проверяем, что пользователь участвует в соревновании
    if not current_user.team or current_user.team.competition_id != competition_id:
        flash('Вы не участвуете в этом соревновании.', 'danger')
        return redirect(url_for('user_competitions'))

    if event.competition_id != competition_id:
        flash('Это критическое событие не принадлежит данному соревнованию.', 'danger')
        return redirect(url_for('view_user_competition', competition_id=competition_id))

    # Проверяем, есть ли уже отчет со статусом "на проверке" (pending)
    existing_pending_report = CriticalEventResponse.query.filter_by(
        event_id=event.id,
        team_id=current_user.team_id,
        status='pending'
    ).first()

    if existing_pending_report:
        flash('У вас уже есть отчет, ожидающий проверки. Вы не можете отправить новый отчет, пока текущий не будет проверен.', 'warning')
        return redirect(url_for('view_user_competition', competition_id=competition_id))

    # Проверяем, есть ли уже отчет со статусом "принят" (approved)
    existing_approved_report = CriticalEventResponse.query.filter_by(
        event_id=event.id,
        team_id=current_user.team_id,
        status='approved'
    ).first()

    if existing_approved_report:
        flash('Отчет по этому критическому событию уже принят. Вы не можете отправить новый отчет.', 'warning')
        return redirect(url_for('view_user_competition', competition_id=competition_id))

    response = CriticalEventResponse.query.filter_by(
        event_id=event.id,
        team_id=current_user.team_id
    ).first()

    if request.method == 'POST':
        try:
            # Создаем или обновляем отчет
            if response:
                response.response = request.form['response']
                response.status = 'pending'
                response.competition_id = competition_id
            else:
                response = CriticalEventResponse(
                    event_id=event.id,
                    user_id=current_user.id,
                    team_id=current_user.team_id,
                    response=request.form['response'],
                    status='pending',
                    competition_id=competition_id
                )
                db.session.add(response)
                db.session.flush()  # Сохраняем отчет, чтобы получить его ID

            # Обработка шагов
            step_ids = request.form.getlist('step_id[]')
            step_names = request.form.getlist('step_name[]')
            descriptions = request.form.getlist('description[]')
            start_times = request.form.getlist('start_time[]')
            end_times = request.form.getlist('end_time[]')
            source_ips = request.form.getlist('source_ip[]')
            source_ports = request.form.getlist('source_port[]')
            destination_ips = request.form.getlist('destination_ip[]')
            destination_ports = request.form.getlist('destination_port[]')
            event_types = request.form.getlist('event_type[]')
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

            # Обработка загрузки скриншотов
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
                        response_id=response.id,
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
                        comments=comments[i],
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
            return redirect(url_for('list_critical_events', competition_id=competition_id))

        except IntegrityError as e:
            db.session.rollback()
            flash('Ошибка: Некоторые обязательные поля не заполнены.', 'danger')
            logger.error(f"Ошибка IntegrityError: {e}")
            return redirect(url_for('fill_critical_event', competition_id=competition_id, event_id=event_id))

        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при сохранении отчета.', 'danger')
            logger.error(f"Ошибка при сохранении в базу данных: {e}")
            return redirect(url_for('fill_critical_event', competition_id=competition_id, event_id=event_id))

    # GET-запрос: отображаем форму
    steps = CriticalEventStep.query.filter_by(event_id=event.id, team_id=current_user.team_id).all()
    return render_template('competitions/user/fill_critical_event.html', competition=competition, event=event, response=response, steps=steps)

@app.route('/admin/competitions/<int:competition_id>/critical_events/reports')
@login_required
@admin_required
def admin_critical_event_reports(competition_id):
    # Получаем соревнование
    competition = Competition.query.get_or_404(competition_id)

    # Получаем все отчеты, ожидающие проверки
    reports = CriticalEventResponse.query.filter_by(
        status='pending',
        competition_id=competition_id
    ).all()

    return render_template(
        'competitions/admin/critical_event_responses.html',
        competition=competition,
        reports=reports
    )

@app.route('/admin/competitions/<int:competition_id>/critical_events/reports/<int:report_id>/review', methods=['GET', 'POST'])
@login_required
@admin_required
def review_critical_event_report(competition_id, report_id):
    # Получаем отчет по ID
    report = CriticalEventResponse.query.get_or_404(report_id)

    # Получаем связанные шаги
    steps = CriticalEventStep.query.filter_by(response_id=report.id).all()

    if request.method == 'POST':
        action = request.form.get('action')  # Одобрить, отклонить или отправить на доработку
        points = int(request.form.get('points', 0))  # Баллы за отчет

        if action == 'approve':
            # Одобрение отчета
            report.status = 'approved'
            report.points_awarded = points

            # Начисляем баллы пользователю
            user = User.query.get(report.user_id)
            user.total_points += points

            # Добавляем запись в историю начисления баллов
            points_history = PointsHistory(
                user_id=report.user_id,
                points=points,
                note=f"За критическое событие: {report.event.title}"
            )
            db.session.add(points_history)

            flash('Отчет одобрен! Баллы начислены.', 'success')

        elif action == 'reject':
            # Отклонение отчета
            report.status = 'rejected'
            flash('Отчет отклонен!', 'danger')

        elif action == 'needs_revision':
            # Отправка на доработку
            report.status = 'needs_revision'
            flash('Отчет отправлен на доработку!', 'warning')

        # Сохраняем изменения в базе данных
        db.session.commit()
        return redirect(url_for('admin_critical_event_reports', competition_id=competition_id))

    return render_template(
        'competitions/admin/review_response.html',
        competition_id=competition_id,
        response=report,  # Переименовано в response
        steps=steps
    )
######################################infrastructure##############################################
from flask import request, flash
import os
import uuid

@app.route('/admin/competitions/<int:competition_id>/infrastructure', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_infrastructure(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    infrastructure = Infrastructure.query.filter_by(competition_id=competition_id).first()

    if not infrastructure:
        infrastructure = Infrastructure(competition=competition)

    if request.method == 'POST':
        # Обновляем данные инфраструктуры
        infrastructure.title = request.form.get('title', infrastructure.title)
        infrastructure.description = request.form.get('description', infrastructure.description)
        infrastructure.organization_description = request.form.get('organization_description', infrastructure.organization_description)
        print(request.files)
        # Обрабатываем JSON-данные
        try:
            infrastructure.topology = json.loads(request.form.get('topology', '[]'))
            infrastructure.links = json.loads(request.form.get('links', '[]'))
        except json.JSONDecodeError:
            flash('Ошибка в формате JSON. Проверьте введенные данные.', 'danger')
            return redirect(url_for('manage_infrastructure', competition_id=competition_id))

        # Обрабатываем загрузку файлов
        if 'files' in request.files:

            files = request.files.getlist('files')
            uploaded_files = []

            for file in files:
                if file.filename != '':
                    # Генерируем уникальное имя файла
                    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER_INFRA'], unique_filename)
                    file.save(file_path)  # Сохраняем файл на сервере
                    uploaded_files.append({
                        'filename': file.filename,
                        'path': unique_filename
                    })
            print("Fiels:",uploaded_files)
            # Обновляем список файлов
            if uploaded_files:
                if infrastructure.files:
                    infrastructure.files.extend(uploaded_files)
                else:
                    infrastructure.files = uploaded_files

        # Сохраняем изменения
        flag_modified(infrastructure, 'files')
        db.session.commit()
        db.session.add(infrastructure)
        db.session.commit()

        flash('Инфраструктура успешно сохранена!', 'success')
        return redirect(url_for('manage_infrastructure', competition_id=competition_id))

    return render_template(
        'competitions/admin/manage_infrastructure.html',
        competition=competition,
        infrastructure=infrastructure,
        topology=infrastructure.topology if infrastructure.topology else [],
        links=infrastructure.links if infrastructure.links else [],
        files=infrastructure.files if infrastructure.files else []
    )
@app.route('/competitions/<int:competition_id>/infrastructure/description')
@login_required
@active_competition_required
def view_infrastructure_description(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    infrastructure = Infrastructure.query.filter_by(competition_id=competition_id).first()

    if not infrastructure:
        flash('Инфраструктура для этого соревнования еще не создана.', 'warning')
        return redirect(url_for('view_user_competition', competition_id=competition_id))

    return render_template(
        'competitions/user/infrastructure_description.html',
        competition=competition,
        infrastructure=infrastructure
    )

@app.route('/competitions/<int:competition_id>/infrastructure/scheme')
@login_required
@active_competition_required
def view_infrastructure_scheme(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    infrastructure = Infrastructure.query.filter_by(competition_id=competition_id).first()

    if not infrastructure:
        flash('Инфраструктура для этого соревнования еще не создана.', 'warning')
        return redirect(url_for('view_user_competition', competition_id=competition_id))

    return render_template(
        'competitions/user/infrastructure_scheme.html',
        competition=competition,
        topology=infrastructure.topology if infrastructure.topology else [],
        links=infrastructure.links if infrastructure.links else []
    )

@app.route('/competitions/<int:competition_id>/infrastructure/nodes')
@login_required
@active_competition_required
def view_infrastructure_nodes(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    infrastructure = Infrastructure.query.filter_by(competition_id=competition_id).first()

    if not infrastructure:
        flash('Инфраструктура для этого соревнования еще не создана.', 'warning')
        return redirect(url_for('view_user_competition', competition_id=competition_id))

    return render_template(
        'competitions/user/infrastructure_nodes.html',
        competition=competition,
        topology=infrastructure.topology if infrastructure.topology else []
    )
import os

@app.route('/admin/competitions/<int:competition_id>/infrastructure/delete_file', methods=['POST'])
@login_required
@admin_required
def delete_infrastructure_file(competition_id):
    data = request.get_json()
    file_path = data.get('file_path')

    if not file_path:
        return jsonify({'success': False, 'message': 'Не указан путь к файлу.'})

    # Получаем инфраструктуру
    infrastructure = Infrastructure.query.filter_by(competition_id=competition_id).first()
    if not infrastructure:
        return jsonify({'success': False, 'message': 'Инфраструктура не найдена.'})

    # Удаляем файл из списка
    if infrastructure.files:
        infrastructure.files = [file for file in infrastructure.files if file['path'] != file_path]
        db.session.commit()

    # Удаляем файл с сервера
    file_full_path = os.path.join(app.config['UPLOAD_FOLDER_INFRA'], file_path)
    if os.path.exists(file_full_path):
        os.remove(file_full_path)

    return jsonify({'success': True})
