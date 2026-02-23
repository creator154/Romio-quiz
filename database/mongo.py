from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

client = AsyncIOMotorClient(MONGO_URI)
db = client.quizbot

users = db.users
quizzes = db.quizzes
games = db.games
