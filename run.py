from app import app, db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаст таблицы, если они ещё не существуют
    app.run(host='0.0.0.0', debug=True)