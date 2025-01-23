from app import app, db
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models import User, Challenge, UserChallenge, Team, Incident, CriticalEvent, CriticalEventResponse,CriticalEventStep,Infrastructure,PointsHistory, Competition, db,FlagResponse,Sherlock, SherlockFlag,SherlockSubmission
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

from flask import request, jsonify
from datetime import datetime
import os
from app.models import db, Sherlock, SherlockFlag
from flask_login import login_required, current_user
from flask import send_from_directory
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
@app.route('/download/<filename>')
@login_required
def download_file(filename):
    # Убедимся, что файл существует и безопасен для скачивания
    if not filename or not filename.endswith(('.pcap', '.txt', '.zip', '.pdf', '.jpg', '.png')):  # Добавьте нужные расширения
        return "Недопустимый файл.", 400
    # Путь к папке с файлами
    upload_folder = app.config['UPLOAD_FOLDER_SHERLOCKS']
    logger.debug(f"Проверка инцидента: {upload_folder}")
    return send_from_directory(upload_folder, filename, as_attachment=True)



def generate_unique_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()  # Получаем расширение файла
    unique_name = f"{uuid.uuid4().hex}.{ext}"  # Генерируем уникальное имя
    return unique_name

@app.route('/admin/sherlocks')
@login_required
def admin_sherlocks():
    # Проверяем, что пользователь — администратор
    if not current_user.is_admin:
        return "У вас нет прав доступа.", 403

    # Получаем все шерлоки из базы данных
    sherlocks = Sherlock.query.all()

    # Отображаем шаблон с передачей списка шерлоков
    return render_template('sherlocks/admin/admin_sherlocks.html', sherlocks=sherlocks)


# Маршрут для сохранения шерлока
@app.route('/admin/sherlocks/create', methods=['POST'])
@login_required
def create_sherlock():
    # Проверяем, что пользователь — администратор
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "У вас нет прав доступа."}), 403

    # Получаем данные из запроса
    data = request.form
    files = request.files

    # Проверяем обязательные поля
    required_fields = ['title', 'description', 'category', 'difficulty', 'points']
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "message": "Не все обязательные поля заполнены."}), 400

    # Создаем шерлок
    sherlock = Sherlock(
        title=data['title'],
        description=data['description'],
        category=data['category'],
        difficulty=data['difficulty'],
        points=int(data['points']),
        created_at=datetime.utcnow(),
        is_active=True
    )

    # Обрабатываем загруженные файлы
    if 'files' in files:
        file_paths = {}
        for file in files.getlist('files'):
            if file.filename != '':
                # Генерируем уникальное имя файла
                unique_filename = generate_unique_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER_SHERLOCKS'], unique_filename)
                file.save(file_path)
                file_paths[file.filename] = unique_filename

        sherlock.files = file_paths

    # Сохраняем шерлок в базе данных
    db.session.add(sherlock)
    db.session.commit()

    # Добавляем флаги (если они есть)
    flags = data.getlist('flags[]')
    for i in range(0, len(flags), 3):  # Группируем элементы по три
        if i + 2 < len(flags):  # Убедимся, что есть три элемента
            title = flags[i]
            description = flags[i + 1]
            answer = flags[i + 2]

            sherlock_flag = SherlockFlag(
                title=title,
                description=description,
                answer=answer,
                sherlock_id=sherlock.id
            )
            db.session.add(sherlock_flag)

    db.session.commit()

    return jsonify({"success": True, "message": "Шерлок успешно создан!", "sherlock_id": sherlock.id}), 201

@app.route('/admin/sherlocks/<int:sherlock_id>/edit', methods=['POST'])
@login_required
def edit_sherlock(sherlock_id):
    # Проверяем, что пользователь — администратор
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "У вас нет прав доступа."}), 403

    # Находим шерлок по ID
    sherlock = Sherlock.query.get_or_404(sherlock_id)

    # Получаем данные из запроса
    data = request.form
    files = request.files

    # Обновляем данные шерлока
    if 'title' in data:
        sherlock.title = data['title']
    if 'description' in data:
        sherlock.description = data['description']
    if 'category' in data:
        sherlock.category = data['category']
    if 'difficulty' in data:
        sherlock.difficulty = data['difficulty']
    if 'points' in data:
        sherlock.points = int(data['points'])

    # Обрабатываем загруженные файлы
    if 'files' in files:
        file_paths = {}
        for file in files.getlist('files'):
            if file.filename != '':
                # Генерируем уникальное имя файла
                unique_filename = generate_unique_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                file_paths[file.filename] = unique_filename

        sherlock.files = file_paths

    # Обновляем флаги (если они есть)
    if 'flags[]' in data:
        # Удаляем старые флаги
        SherlockFlag.query.filter_by(sherlock_id=sherlock.id).delete()

        # Добавляем новые флаги
        flags = data.getlist('flags[]')
        for i in range(0, len(flags), 3):  # Группируем элементы по три
            if i + 2 < len(flags):  # Убедимся, что есть три элемента
                title = flags[i]
                description = flags[i + 1]
                answer = flags[i + 2]

                sherlock_flag = SherlockFlag(
                    title=title,
                    description=description,
                    answer=answer,
                    sherlock_id=sherlock.id
                )
                db.session.add(sherlock_flag)

    # Сохраняем изменения в базе данных
    db.session.commit()

    return jsonify({"success": True, "message": "Шерлок успешно обновлен!", "sherlock_id": sherlock.id}), 200

@app.route('/admin/sherlocks/<int:sherlock_id>/delete', methods=['DELETE'])
@login_required
def delete_sherlock(sherlock_id):
    # Проверяем, что пользователь — администратор
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "У вас нет прав доступа."}), 403

    # Находим шерлок по ID
    sherlock = Sherlock.query.get_or_404(sherlock_id)

    # Находим все флаги, связанные с данным шерлоком
    flags = SherlockFlag.query.filter_by(sherlock_id=sherlock.id).all()

# Удаляем все связанные записи из sherlock_submission
    for flag in flags:
        SherlockSubmission.query.filter_by(flag_id=flag.id).delete()

# Теперь можно удалить записи из sherlock_flag
    SherlockFlag.query.filter_by(sherlock_id=sherlock.id).delete()
    db.session.commit()
    # Удаляем связанные флаги
    SherlockFlag.query.filter_by(sherlock_id=sherlock.id).delete()

    # Удаляем файлы шерлока (если они есть)
    if sherlock.files:
        for file_path in sherlock.files.values():
            file_full_path = os.path.join(app.config['UPLOAD_FOLDER'], file_path)
            if os.path.exists(file_full_path):
                try:
                    os.remove(file_full_path)
                except Exception as e:
                    print(f"Ошибка при удалении файла {file_full_path}: {e}")

    # Удаляем шерлок из базы данных
    db.session.delete(sherlock)
    db.session.commit()

    return jsonify({"success": True, "message": "Шерлок успешно удален!"}), 200

@app.route('/admin/sherlocks/<int:sherlock_id>', methods=['GET'])
@login_required
def get_sherlock(sherlock_id):
    # Проверяем, что пользователь — администратор
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "У вас нет прав доступа."}), 403

    # Находим шерлок по ID
    sherlock = Sherlock.query.get_or_404(sherlock_id)

    # Получаем флаги шерлока
    flags = SherlockFlag.query.filter_by(sherlock_id=sherlock.id).all()

    # Формируем ответ
    response = {
        "id": sherlock.id,
        "title": sherlock.title,
        "description": sherlock.description,
        "category": sherlock.category,
        "difficulty": sherlock.difficulty,
        "points": sherlock.points,
        "files": sherlock.files,
        "flags": [{"title": flag.title, "description": flag.description, "answer": flag.answer} for flag in flags]
    }

    return jsonify(response), 200

@app.route('/sherlocks')
@login_required
def user_sherlocks():
    # Получаем все активные шерлоки
    sherlocks = Sherlock.query.filter_by(is_active=True).all()

    # Для каждого шерлока проверяем, решен ли он пользователем
    for sherlock in sherlocks:
        # Получаем общее количество флагов в шерлоке
        total_flags = SherlockFlag.query.filter_by(sherlock_id=sherlock.id).count()

        # Получаем количество решенных флагов пользователем
        solved_flags = SherlockSubmission.query.filter_by(
            user_id=current_user.id,
            sherlock_id=sherlock.id,
            is_correct=True
        ).count()

        # Добавляем поле is_solved в объект sherlock
        sherlock.is_solved = (solved_flags == total_flags)

    return render_template('sherlocks/users/user_sherlocks.html', sherlocks=sherlocks)


@app.route('/sherlocks/<int:sherlock_id>')
@login_required
def solve_sherlock(sherlock_id):
    # Находим шерлок по ID
    sherlock = Sherlock.query.get_or_404(sherlock_id)

    # Проверяем, что шерлок активен
    if not sherlock.is_active:
        return "Этот шерлок недоступен.", 404

    # Получаем флаги шерлока
    flags = SherlockFlag.query.filter_by(sherlock_id=sherlock.id).all()
    sherlock.flags = flags

    # Получаем ID флагов, которые уже решены пользователем
    solved_flags = [
        submission.flag_id
        for submission in SherlockSubmission.query.filter_by(
            user_id=current_user.id,
            sherlock_id=sherlock.id,
            is_correct=True
        ).all()
    ]

    return render_template('sherlocks/users/solve_sherlock.html', sherlock=sherlock, solved_flags=solved_flags)

@app.route('/sherlocks/<int:sherlock_id>/submit-flag', methods=['POST'])
@login_required
def submit_sherlock_flag(sherlock_id):
    # Получаем данные из запроса
    data = request.get_json()
    flag_id = data.get('flag_id')
    user_flag = data.get('flag')

    # Находим флаг по ID
    flag = SherlockFlag.query.get_or_404(flag_id)

    # Проверяем, что флаг принадлежит шерлоку
    if flag.sherlock_id != sherlock_id:
        return jsonify({"success": False, "message": "Неверный флаг."}), 400

    # Проверяем, не решен ли уже этот флаг пользователем
    if SherlockSubmission.query.filter_by(
        user_id=current_user.id,
        flag_id=flag.id,
        is_correct=True
    ).first():
        return jsonify({"success": False, "message": "Вы уже решили этот флаг."}), 400

    # Проверяем, правильный ли флаг
    if user_flag == flag.answer:
        # Создаем запись о решении
        submission = SherlockSubmission(
            user_id=current_user.id,
            team_id=current_user.team_id,
            sherlock_id=sherlock_id,
            flag_id=flag.id,
            submitted_flag=user_flag,
            is_correct=True
        )
        db.session.add(submission)

        # Получаем общее количество флагов в шерлоке
        total_flags = SherlockFlag.query.filter_by(sherlock_id=sherlock_id).count()

        # Получаем количество решенных флагов пользователем
        solved_flags = SherlockSubmission.query.filter_by(
            user_id=current_user.id,
            sherlock_id=sherlock_id,
            is_correct=True
        ).count()

        # Если пользователь решил все флаги, начисляем баллы
        if solved_flags == total_flags:
            current_user.total_points += flag.sherlock.points
            db.session.commit()
            return jsonify({"success": True, "message": "Правильный флаг! Все флаги решены, баллы начислены."}), 200
        else:
            db.session.commit()
            return jsonify({"success": True, "message": "Правильный флаг! Осталось решить еще флагов."}), 200
    else:
        return jsonify({"success": False, "message": "Неправильный флаг."}), 400
