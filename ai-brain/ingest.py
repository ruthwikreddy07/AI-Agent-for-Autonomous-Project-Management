import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# ==========================================
# 1. CONFIGURATION
# ==========================================
PINECONE_API_KEY = "pcsk_5UKF8V_TiR2tKu8izJQ7isSeMW6pxQAsyC359FNaF3EasPSMUD1km3xwfMw8Rr17k4ffzg"  # <--- PASTE KEY
INDEX_NAME = "project-memory"

# ==========================================
# 2. INITIALIZE CONNECTION
# ==========================================
print("🔌 Connecting to Pinecone...")
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

print("🧠 Loading Embedding Model (This takes 10s)...")
# This is the free model that turns text into numbers (384 dimensions)
model = SentenceTransformer('all-MiniLM-L6-v2') 

# ==========================================
# 3. READ & EMBED
# ==========================================
file_path = "project_info.txt"

if not os.path.exists(file_path):
    print(f"❌ Error: {file_path} not found!")
    exit()

print(f"📖 Reading {file_path}...")
with open(file_path, "r") as f:
    text = f.read()

# We split the text into lines so the AI can find specific facts
chunks = [line for line in text.split('\n') if line.strip() != ""]

print(f"🔢 Converting {len(chunks)} facts into vectors...")
vectors = []

for i, chunk in enumerate(chunks):
    # Convert text to numbers
    vector_values = model.encode(chunk).tolist()
    
    # Prepare data for Pinecone
    vectors.append({
        "id": f"fact_{i}",
        "values": vector_values,
        "metadata": {"text": chunk}
    })

# ==========================================
# 4. UPLOAD
# ==========================================
print("🚀 Uploading to Memory...")
index.upsert(vectors=vectors)

print("✅ SUCCESS! The AI has memorized the project info.")