from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    from_email = db.Column(db.String(255), nullable=True)   # ✅ sender
    body = db.Column(db.Text, nullable=True)                # ✅ email body
    completed = db.Column(db.Boolean, default=False)
    user_email = db.Column(db.String(255), nullable=False)  # ✅ Gmail account

    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject,
            "from_email": self.from_email,
            "body": self.body,
            "completed": self.completed,
            "user_email": self.user_email,
        }
