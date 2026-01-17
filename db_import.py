import pandas as pd
from flask import Flask
from config import SQLALCHEMY_DATABASE_URI
from models import db, MedicinalPlant

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

df = pd.read_csv("data/medicinalseason.csv")

with app.app_context():
    for _, row in df.iterrows():
        plant = MedicinalPlant(
            plant_name=row["plant_name"],
            local_name=row["local_name"],
            disease=row["disease"],
            how_to_use=row["how_to_use"]

        )
        db.session.add(plant)

    db.session.commit()

print("✅ CSV imported successfully")
