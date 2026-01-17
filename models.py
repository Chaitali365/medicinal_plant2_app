from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class MedicinalPlant(db.Model):
    __tablename__ = "medicinal_plant"

    id = db.Column(db.Integer, primary_key=True)
    plant_name = db.Column(db.String(200), nullable=False)
    local_name = db.Column(db.String(200))
    disease = db.Column(db.Text)
    how_to_use = db.Column(db.Text)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    plant_id = db.Column(db.Integer, db.ForeignKey("medicinal_plant.id"))
    