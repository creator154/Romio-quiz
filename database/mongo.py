from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

client = AsyncIOMotorClient(MONGO_URI)

db = client["quizbot"]

quizzes_collection = db["quizzes"]
games_collection = db["games"]
users_collection = db["users"]
