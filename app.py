from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_cors import CORS
from gmail_tasks import get_task_emails, fetch_and_store_tasks
from models import db, Task
from apscheduler.schedulers.background import BackgroundScheduler
from auth import auth_blueprint

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your_secret_key'
CORS(app)

app.register_blueprint(auth_blueprint)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/api')
def api_status():
    return jsonify({'message': 'Gmail Task Tracker API is running'})

@app.route('/')
def home():
    if 'credentials' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login-page')
def login_page():
    return render_template('login.html')

@app.route('/tasks/sync', methods=['POST'])
def sync_tasks():
    try:
        user_email = request.json.get('user_email')
        if not user_email:
            return jsonify({'error': 'Missing user_email'}), 400

        fetched_tasks = get_task_emails(user_email)
        new_tasks = []

        existing_subjects = set(task.subject for task in Task.query.filter_by(user_email=user_email).all())

        for item in fetched_tasks:
            if item['subject'] not in existing_subjects:
                task = Task(
                    subject=item['subject'],
                    from_email=item.get('from_email'),
                    body=item.get('body'),
                    completed=False,
                    user_email=user_email
                )
                db.session.add(task)
                new_tasks.append(task.to_dict())

        db.session.commit()
        return jsonify({'synced_tasks': new_tasks})

    except Exception as e:
        print("❌ Sync error:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/tasks', methods=['GET'])
def get_user_tasks():
    user_email = request.args.get('user_email')
    if not user_email:
        return jsonify({'error': 'Missing user_email'}), 400

    tasks = Task.query.filter_by(user_email=user_email).order_by(Task.id.desc()).all()
    return jsonify([task.to_dict() for task in tasks])

@app.route('/tasks/<int:task_id>', methods=['PATCH'])
def mark_task_completed(task_id):
    user_email = request.json.get('user_email')
    if not user_email:
        return jsonify({'error': 'Missing user_email'}), 400

    task = Task.query.filter_by(id=task_id, user_email=user_email).first()
    if not task:
        return jsonify({'error': 'Task not found or unauthorized'}), 404

    task.completed = True
    db.session.commit()
    return jsonify(task.to_dict())

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=fetch_and_store_tasks, trigger="interval", minutes=5)
    scheduler.start()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        start_scheduler()
    app.run(debug=True)
