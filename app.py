from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY
from models import db, MedicinalPlant, User, Favorite
from disease_aliases import normalize_disease

import pandas as pd
import os

import pyttsx3
import threading
import queue


app = Flask(__name__)
app.secret_key = SECRET_KEY

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)

# ---------- LOGIN REQUIRED DECORATOR ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("home.html")


# ---------- SEARCH ----------
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    results = []
    disease = ""

    if request.method == "POST":
        disease = request.form["disease"]
        normalized = normalize_disease(disease)

        results = MedicinalPlant.query.filter(
            MedicinalPlant.disease.ilike(f"%{normalized}%")
        ).all()

    return render_template("index.html", results=results, disease=disease)


# ---------- PLANT DETAIL ----------
@app.route("/plant/<int:id>")
@login_required
def plant_detail(id):
    plant = MedicinalPlant.query.get_or_404(id)
    return render_template("plant_detail.html", plant=plant)


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            session["user"] = user.username
            return redirect(url_for("search"))

    return render_template("login.html")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ---------- FAVORITES ----------
@app.route("/favorite/<int:plant_id>")
@login_required
def favorite(plant_id):
    user = User.query.filter_by(username=session["user"]).first()

    existing = Favorite.query.filter_by(
        user_id=user.id, plant_id=plant_id
    ).first()

    if not existing:
        fav = Favorite(user_id=user.id, plant_id=plant_id)
        db.session.add(fav)
        db.session.commit()

    return redirect(url_for("search"))


@app.route("/favorites")
@login_required
def favorites():
    user = User.query.filter_by(username=session["user"]).first()

    plants = db.session.query(MedicinalPlant).join(
        Favorite, MedicinalPlant.id == Favorite.plant_id
    ).filter(Favorite.user_id == user.id).all()

    return render_template("favorites.html", plants=plants)


# ---------- SEASONS ----------
@app.route("/seasons", methods=["GET", "POST"])
def seasons():
    csv_path = os.path.join("data", "medicinalseason.csv")
    df = pd.read_csv(csv_path)

    seasons = sorted(df["season"].dropna().unique())
    plants = []
    selected_season = None

    if request.method == "POST":
        selected_season = request.form.get("season")
        plants = df[df["season"] == selected_season].to_dict(orient="records")

    return render_template(
        "seasons.html",
        seasons=seasons,
        plants=plants,
        selected_season=selected_season
    )


# ---------- ABOUT (SEARCH + COMPARE) ----------
@app.route("/about", methods=["GET", "POST"])
def about():
    csv_path = os.path.join("data", "medicinalseason.csv")
    df = pd.read_csv(csv_path)

    plant = None
    plant1 = None
    plant2 = None
    query = ""

    plant_names = sorted(df["plant_name"].dropna().unique())

    # EXISTING SINGLE SEARCH (UNCHANGED)
    if request.method == "POST" and "plant_name" in request.form:
        query = request.form.get("plant_name", "").strip().lower()
        result = df[df["plant_name"].str.lower() == query]
        if not result.empty:
            plant = result.iloc[0].to_dict()

    # NEW COMPARE FEATURE (SEPARATE & SAFE)
    if request.method == "POST" and "compare" in request.form:
        p1 = request.form.get("plant1")
        p2 = request.form.get("plant2")

        if p1 and p2:
            plant1 = df[df["plant_name"] == p1].iloc[0].to_dict()
            plant2 = df[df["plant_name"] == p2].iloc[0].to_dict()

    return render_template(
        "about.html",
        plant=plant,
        plant1=plant1,
        plant2=plant2,
        plant_names=plant_names,
        query=query
    )


PLANT_DB = {
    "Jamun": ("Syzygium cumini", "Anti-diabetic fruit", "Regulates blood sugar, improves digestion.", "Seed powder or fresh fruit."),
    "Bitter Gourd": ("Momordica charantia", "Blood purifier", "Controls diabetes, purifies blood, boosts immunity.", "Juice or cooked vegetable."),
    "Peppermint": ("Mentha piperita", "Cooling herb", "Relieves indigestion, headaches, and respiratory issues.", "Tea or essential oil."),
    "Clove": ("Syzygium aromaticum", "Analgesic spice", "Toothache relief, digestive aid, antimicrobial.", "Chewed raw or clove oil."),
    "Garlic": ("Allium sativum", "Heart tonic", "Lowers cholesterol, boosts immunity, blood thinner.", "Raw cloves or in food."),
    "Vasaka": ("Adhatoda vasica", "Respiratory expert", "Treats cough, asthma, and bronchitis.", "Leaf juice or decoction."),
    "Babul": ("Acacia nilotica", "Oral health guardian", "Strengthens gums, treats skin diseases.", "Bark decoction or datun (twig)."),
    "Coriander": ("Coriandrum sativum", "Cooling spice", "Relieves excess heat (Pitta), digestive aid.", "Seeds water or fresh leaves."),
    "Kalmegh": ("Andrographis paniculata", "King of Bitters", "Liver detox, fever reduction, immunity.", "Powder or decoction."),
    "Punarnava": ("Boerhavia diffusa", "Kidney rejuvenator", "Treats kidney disorders, UTI, and swelling.", "Root powder or decoction."),
    "Shatavari": ("Asparagus racemosus", "Women's tonic", "Hormonal balance, reproductive health, vitality.", "Root powder with milk."),
    "Guggulu": ("Commiphora wightii", "Fat burner", "Lowers cholesterol, treats arthritis, weight management.", "Purified resin tablet."),
    "Haritaki": ("Terminalia chebula", "Master detoxifier", "Cleanses colon, improves vision and longevity.", "Powder with warm water."),
    "Baheda": ("Terminalia bellirica", "Respiratory tonic", "Good for throat, hair health, and eyes.", "Fruit powder."),
    "Mulethi": ("Glycyrrhiza glabra", "Soothing herb", "Cures acidity, sore throat, and ulcers.", "Root stick or powder."),
    "Pippali": ("Piper longum", "Metabolism booster", "Improves lung function, burns toxins (Ama).", "Powder with honey."),
    "Bhringraj": ("Eclipta alba", "Ruler of Hair", "Promotes hair growth, liver health.", "Oil for hair, juice for liver."),
    "Safed Musli": ("Chlorophytum borivilianum", "Strength tonic", "Boosts vitality, stamina, and immunity.", "Root powder with milk."),
    "Gokhru": ("Tribulus terrestris", "Urinary tonic", "Treats kidney stones, UTI, and prostate issues.", "Fruit decoction."),
    "Shankhpushpi": ("Convolvulus pluricaulis", "Brain tonic", "Enhances memory, reduces mental stress/anxiety.", "Syrup or powder."),
    "Manjistha": ("Rubia cordifolia", "Blood purifier", "Clear skin, lymphatic support, blood detox.", "Powder or tablet."),
    "Sarpgandha": ("Rauvolfia serpentina", "BP regulator", "Treats hypertension and insomnia.", "Root powder (under supervision)."),
    "Moringa": ("Moringa oleifera", "Superfood", "Rich in vitamins, strengthens bones, joints.", "Leaf powder or drumsticks."),
    "Papaya": ("Carica papaya", "Platelet booster", "Leaf juice increases platelets in dengue.", "Leaf juice or ripe fruit."),
    "Anar": ("Punica granatum", "Hemoglobin booster", "Improves heart health, blood count.", "Fruit or juice."),
    "Methi": ("Trigonella foenum-graecum", "Insulin mimetic", "Controls blood sugar, good for hair.", "Soaked seeds water."),
    "Saunf": ("Foeniculum vulgare", "Digestive coolant", "Prevents bloating, freshens breath.", "Chewed after meals."),
    "Dalchini": ("Cinnamomum verum", "Metabolism spice", "Improves insulin sensitivity, digestion.", "Bark powder or tea."),
    "Heeng": ("Ferula assa-foetida", "Anti-flatulent", "Instant relief from gas and bloating.", "Pinch in warm water/food."),
    "Tejpatta": ("Cinnamomum tamala", "Aromatic leaf", "Improves digestion, regulates sugar.", "In cooking."),
    "Karipatta": ("Murraya koenigii", "Hair tonic", "Prevents greying, aids digestion.", "Chewed raw or in food."),
    "Sadabahar": ("Catharanthus roseus", "Anti-cancer", "Used in diabetes and specific cancer therapies.", "Flower/Leaf extracts."),
    "Vidarikand": ("Pueraria tuberosa", "Nutritive tonic", "Builds body mass, strength, and immunity.", "Tuber powder."),
    "Kaunch Beej": ("Mucuna pruriens", "Nerve tonic", "Treats Parkinson's, boosts testosterone.", "Seed powder."),
    "Arjuna": ("Terminalia arjuna", "Heart Guardian", "Strengthens heart muscles, controls BP.", "Bark decoction with milk."),
    "Ashok": ("Saraca asoca", "Friend of Women", "Treats uterine disorders and menstrual issues.", "Bark decoction."),
    "Bael": ("Aegle marmelos", "Gut healer", "Cures IBS, diarrhea, and dysentery.", "Fruit pulp or sherbet."),
    "Chitrak": ("Plumbago zeylanica", "Digestive fire", "Treats weak digestion and piles.", "Root powder (purified)."),
    "Senna": ("Cassia angustifolia", "Laxative", "Relieves acute constipation.", "Leaf powder or tea."),
    "Patharchatta": ("Kalanchoe pinnata", "Stone breaker", "Dissolves kidney stones.", "Chew fresh leaves."),
    "Parijat": ("Nyctanthes arbor-tristis", "Sciatica cure", "Treats joint pain, sciatica, and fever.", "Leaf decoction."),
    "Aprajita": ("Clitoria ternatea", "Mind flower", "Boosts memory, stress relief.", "Blue tea from flowers."),
    "Nagarmotha": ("Cyperus rotundus", "Digestive herb", "Treats fever, digestion, and skin issues.", "Tuber powder."),
    "Kachnar": ("Bauhinia variegata", "Cyst breaker", "Treats thyroid, cysts, and swollen glands.", "Bark decoction."),
    "Makoi": ("Solanum nigrum", "Liver tonic", "Treats liver and spleen enlargement.", "Fresh juice or fruit."),
    "Kantakari": ("Solanum virginianum", "Throat healer", "Treats cough, asthma, and throat pain.", "Whole plant decoction."),
    "Malkangni": ("Celastrus paniculatus", "Intellect tree", "Improves memory and cognitive function.", "Oil or seed powder."),
    "Atibala": ("Abutilon indicum", "Strength giver", "General tonic for physical strength.", "Root/Seed powder."),
    "Varun": ("Crataeva nurvala", "Kidney support", "Treats urinary stones and UTI.", "Bark decoction."),
    "Jatiphala": ("Myristica fragrans", "Sleep aid", "Induces sleep, treats diarrhea.", "Nutmeg powder in milk."),
    "Kankola": ("Piper cubeba", "Throat soothe", "Clears throat, treats cough.", "Chewed or powder."),
    "Latakaranja": ("Caesalpinia bonduc", "Fever fighter", "Anti-malarial, treats fever.", "Seed kernel powder."),
    "Mahanimba": ("Melia azedarach", "Skin healer", "Treats skin diseases, piles.", "Leaf/Bark paste."),
    "Amaltas": ("Cassia fistula", "Gentle laxative", "Treats constipation and skin issues.", "Fruit pulp."),
    "Bhumyamalaki": ("Phyllanthus niruri", "Liver protector", "Cures jaundice, hepatitis B.", "Whole plant juice."),
    "Pashanbheda": ("Bergenia ciliata", "Stone breaker", "Dissolves kidney stones.", "Rhizome decoction."),
    "Kutaja": ("Holarrhena antidysenterica", "Dysentery cure", "Treats severe diarrhea/IBS.", "Bark powder."),
    "Rakta Chandan": ("Pterocarpus santalinus", "Cooling wood", "Treats acne, pigmentation, cooling.", "Wood paste on face."),
    "Priyangu": ("Callicarpa macrophylla", "Coolant", "Treats burning sensation, bleeding.", "Fruit/Flower powder."),
    "Aguru": ("Aquilaria agallocha", "Aromatic", "Treats bad breath, skin issues.", "Oil or powder."),
    "Shallaki": ("Boswellia serrata", "Joint relief", "Treats osteoarthritis, pain.", "Resin/Gum."),
    "Shami": ("Prosopis cineraria", "Anti-inflammatory", "Treats skin disorders, asthma.", "Bark/Leaf."),
    "Nirgundi": ("Vitex negundo", "Pain reliever", "Treats joint pain, arthritis.", "Leaf poultice/oil."),
    "Dhataki": ("Woodfordia fruticosa", "Fermentation agent", "Used in Arishtas, treats bleeding.", "Flowers."),
    "Gunja": ("Abrus precatorius", "Hair growth", "Promotes hair growth (toxic if swallowed).", "Seed paste externally."),
    "Ishwari": ("Aristolochia indica", "Antidote", "Snake bite support (traditional), fever.", "Root."),
    "Daruharidra": ("Berberis aristata", "Eye tonic", "Treats eye infections, diabetes.", "Stem decoction."),
    "Kampillaka": ("Mallotus philippensis", "Worm killer", "Treats intestinal worms, skin.", "Glandular hair powder."),
    "Khadira": ("Acacia catechu", "Skin purifier", "Treats eczema, blood disorders.", "Heartwood decoction."),
    "Udumbar": ("Ficus racemosa", "Cooling fruit", "Treats heat, bleeding disorders.", "Bark/Fruit."),
    "Ajwain": ("Trachyspermum ammi", "Colic relief", "Treats gas, stomach ache.", "Chewed or water."),
    "Kutki": ("Picrorhiza kurroa", "Liver detox", "Potent liver tonic, treats fever.", "Root powder (bitter)."),
    "Chirata": ("Swertia chirata", "Blood purifier", "Treats skin diseases, fever.", "Whole plant decoction."),
    "Karanja": ("Pongamia pinnata", "Skin healer", "Treats eczema, psoriasis.", "Oil or bark."),
    "Jatamansi": ("Nardostachys jatamansi", "Calming herb", "Treats insomnia, stress, hair growth.", "Root powder."),
    "Parpata": ("Fumaria indica", "Fever cure", "Treats high fever, blood impurities.", "Whole plant."),
    "Talisapatra": ("Abies webbiana", "Respiratory", "Treats cough, asthma.", "Leaf powder."),
    "Vanshlochan": ("Bambusa arundinacea", "Calcium source", "Strengthens bones, lung tonic.", "Siliceous secretion."),
    "Vidanga": ("Embelia ribes", "Worm killer", "Best for intestinal worms.", "Fruit powder."),
    "Karkatshringi": ("Pistacia integerrima", "Pediatric cough", "Treats cough in children.", "Gall powder."),
    "Somlata": ("Ephedra gerardiana", "Bronchodilator", "Treats asthma, cardiac stimulant.", "Stem."),
    "Japa": ("Hibiscus rosa-sinensis", "Hair tonic", "Prevents hair fall, heart tonic.", "Flower/Leaf."),
    "Sariva": ("Hemidesmus indicus", "Cooling root", "Blood purifier, cooling.", "Root drink."),
    "Ativisha": ("Aconitum heterophyllum", "Pediatric tonic", "Treats fever/diarrhea in kids.", "Root."),
    "Shyonaka": ("Oroxylum indicum", "Pain relief", "Component of Dashamoola.", "Bark."),
    "Gambhari": ("Gmelina arborea", "Nerve tonic", "Treats weakness, vata disorders.", "Fruit/Bark."),
    "Patala": ("Stereospermum suaveolens", "Diuretic", "Treats edema, breathing issues.", "Root/Bark."),
    "Agnimantha": ("Premna integrifolia", "Anti-inflammatory", "Treats swelling, weight loss.", "Root/Leaf."),
    "Prishniparni": ("Uraria picta", "Fracture healing", "Treats fractures, diarrhea.", "Whole plant."),
    "Nagakeshara": ("Mesua ferrea", "Bleeding arrest", "Treats bleeding piles.", "Stamen."),
    "Lodhra": ("Symplocos racemosa", "Women's health", "Treats leucorrhea, skin.", "Bark."),
    "Bakuchi": ("Psoralea corylifolia", "Vitiligo cure", "Treats white spots (leucoderma).", "Seed oil/powder."),
    "Chakramarda": ("Cassia tora", "Ringworm cure", "Treats fungal infections.", "Seed paste."),
    "Bharangi": ("Clerodendrum serratum", "Respiratory", "Treats asthma, allergies.", "Root."),
    "Danti": ("Baliospermum montanum", "Purgative", "Treats severe constipation.", "Root."),
    "Eranda": ("Ricinus communis", "Rheumatism", "Treats joint pain, constipation.", "Root/Oil."),
    "Brihati": ("Solanum indicum", "Respiratory", "Treats asthma, cough.", "Root."),
    "Jyotishmati": ("Celastrus paniculatus", "Memory oil", "Improves intellect.", "Seed oil."),
    "Nimba": ("Azadirachta indica", "Antiseptic", "See 'Neem' entry.", "Leaves/Bark."),
    "Neem": ("Azadirachta indica","Antiseptic tree","Purifies blood, treats skin diseases, boosts immunity, antibacterial and antifungal.","Leaves paste, neem oil, or decoction."),
    "Tulsi": ("Ocimum sanctum", "Herb", "Boosts immunity, relieves stress, supports respiratory health.", "Leaves can be chewed or made into tea."),
    "Rose": ("Rosa indica", "Flower", "Improves skin health, reduces stress, has antioxidant properties.", "Petals can be used in tea, syrup, or skincare."),
    "Lemon": ("Citrus limon", "Fruit", "Rich in Vitamin C, aids digestion, detoxifies body.", "Juice can be consumed or used in water."),
    "Mint": ("Mentha spicata", "Herb", "Relieves indigestion, improves oral health, refreshes breath.", "Leaves can be chewed, made into tea, or used as garnish."),
    "Aloe Vera": ("Aloe barbadensis miller", "Succulent/Herb", "Soothes burns, improves skin health, aids digestion.", "Gel can be applied topically or consumed in juice form."),
    "Giloy": (
        "Tinospora cordifolia",
        "Immunity booster and detoxifier",
        "Boosts immunity, reduces inflammation, treats fever, diabetes, and respiratory issues.",
        "Juice, powder, decoction, or stem pieces."
    ),
    "Amla": (
        "Phyllanthus emblica",
        "Rich source of Vitamin C and antioxidant",
        "Improves immunity, strengthens hair, prevents aging, aids digestion and heart health.",
        "Fresh fruit, juice, powder, or dried pieces."
    ),
    "Cumin": (
        "Cuminum cyminum",
        "Digestive and antioxidant spice",
        "Improves digestion, reduces bloating, boosts immunity, and manages diabetes.",
        "Seeds used whole or powdered in food or decoction."
    ),
    "Turmeric": (
        "Curcuma longa",
        "Anti-inflammatory and antioxidant",
        "Reduces inflammation, improves liver function, supports skin and joint health.",
        "Powder, fresh root, capsules, or decoction with milk/water."
    ),
    "Brahmi": (
        "Bacopa monnieri",
        "Brain tonic and memory enhancer",
        "Improves memory, reduces stress, boosts concentration, and supports nervous system.",
        "Leaves used in juice, powder, or capsules."
    ),
    "Parijatak": (
        "Nyctanthes arbor-tristis",
        "Fever reducer and anti-inflammatory",
        "Reduces fever, relieves cough, improves digestion, and acts as a mild laxative.",
        "Leaves and flowers used in decoction or powder form."
    ),
    "Ashok": (
        "Saraca asoca",
        "Women’s reproductive health",
        "Regulates menstrual cycle, reduces menstrual pain, strengthens uterus, and improves fertility.",
        "Bark or powdered form used in decoction or tablets."
    ),
    "Methika": (
        "Trigonella foenum-graecum",
        "Metabolism and lactation booster",
        "Improves digestion, reduces cholesterol, controls blood sugar, and enhances milk production in lactating mothers.",
        "Seeds used in powder, decoction, or sprouted form."
    ),
    "Jyotishmati": (
        "Celastrus paniculatus",
        "Memory and nervous system tonic",
        "Enhances memory, reduces stress, supports brain and nerve health, and improves concentration.",
        "Seeds used in oil or powdered form."
    )


}

# Queue for speech messages
speech_queue = queue.Queue()

# Initialize TTS engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)  # you can change 0 or 1 for different voices

# Background thread that reads messages from the queue and speaks them
def speak_worker():
    while True:
        text = speech_queue.get()  # waits until there is a message
        engine.say(text)
        engine.runAndWait()
        speech_queue.task_done()

# Start the thread
threading.Thread(target=speak_worker, daemon=True).start()


@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.form.get("msg", "").lower()
    response = "Sorry, I don’t have information about that plant yet."
    speech_text = response

    # Check PLANT_DB for plant info
    for plant, details in PLANT_DB.items():
        if plant.lower() in msg:
            scientific, category, benefits, usage = details
            response = f"""
<b>{plant}</b><br>
<b>Scientific Name:</b> {scientific}<br>
<b>Category:</b> {category}<br>
<b>Benefits:</b> {benefits}<br>
<b>How to Use:</b> {usage}
"""
            speech_text = (
                f"{plant}. "
                f"Scientific name {scientific}. "
                f"Category {category}. "
                f"Benefits are {benefits}. "
                f"How to use: {usage}."
            )
            break

    # Add the speech text to the queue
    speech_queue.put(speech_text)

    return response






# ---------- RUN ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
