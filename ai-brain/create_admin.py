from pymongo import MongoClient
from passlib.context import CryptContext

# === CONFIGURATION ===
# ⚠️ REPLACE THIS WITH YOUR REAL MONGODB URL
MONGO_URI = "mongodb+srv://eventhubuser:JLzCOCd27buyhWOQ@cluster0.frrybb1.mongodb.net/eventhub?retryWrites=true&w=majority&appName=Cluster0" 
# If using local, keep: "mongodb://localhost:27017"

client = MongoClient(MONGO_URI)
db = client["ai_project_manager"]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    username = "admin123"
    password = "password123"
    
    # Check if user already exists
    if db.users.find_one({"username": username}):
        print(f"❌ User '{username}' already exists!")
        return

    hashed_pw = pwd_context.hash(password)
    db.users.insert_one({"username": username, "password": hashed_pw})
    print(f"✅ SUCCESS: Created user '{username}' with password '{password}'")

if __name__ == "__main__":
    create_admin()