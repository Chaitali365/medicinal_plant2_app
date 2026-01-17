# disease_aliases.py

DISEASE_ALIASES = {

    # Diabetes
    "diabetes": ["diabetes", "sugar", "sugar problem", "blood sugar", "high sugar", "type 1 diabetes", "type 2 diabetes"],

    # Cold & Cough
    "cold": ["cold", "common cold", "running nose", "sneezing"],
    "cough": ["cough", "chronic cough", "dry cough", "wet cough", "whooping cough"],

    # Fever
    "fever": ["fever", "high fever", "digestive fever"],

    # Skin Diseases
    "skin disease": ["skin disease", "skin diseases", "skin ailments", "eczema", "acne", "scabies", "skin ulcers", "skin burns"],

    # Heart
    "heart disease": ["heart disease", "heart problem", "heart palpitation", "cholesterol", "high triglycerides"],

    # Blood Pressure
    "hypertension": ["hypertension", "high blood pressure", "bp"],

    # Digestive Issues
    "constipation": ["constipation", "severe constipation"],
    "diarrhea": ["diarrhea", "chronic diarrhea", "dysentery", "ibs"],
    "acidity": ["acidity", "acid reflux", "burning sensation"],

    # Kidney
    "kidney stones": ["kidney stones", "urinary calculi"],
    "urinary infection": ["urinary infection", "uti"],

    # Mental Health
    "stress": ["stress", "anxiety", "mental fatigue", "insomnia"],

    # Memory & Brain
    "memory loss": ["memory loss", "memory enhancement", "brain health", "parkinson's"],

    # Joint / Bones
    "arthritis": ["arthritis", "osteoarthritis", "joint pain", "joint inflammation"],

    # Liver
    "liver disease": ["liver disease", "fatty liver", "hepatitis", "liver disorders"],

    # Women Health
    "menstrual disorders": ["menstrual disorders"],

    # Others (can keep expanding)
    "toothache": ["toothache", "tooth sensitivity", "bad breath", "bleeding gums"],
    "asthma": ["asthma", "respiratory issues"],
}
def normalize_disease(user_input: str):
    user_input = user_input.lower().strip()

    for standard_disease, aliases in DISEASE_ALIASES.items():
        if user_input in aliases:
            return standard_disease

    # If no alias found, return input as-is
    return user_input