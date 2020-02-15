from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref
from dotenv import load_dotenv
import os

# LOAD ENV VALUES
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URI")
ROOT_PATH = "./share"

# CREATE APP OBJECT
app = Flask(__name__, static_folder=ROOT_PATH)

# SET DATABASE URI IN CONFIG
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

db = SQLAlchemy(app)

# DEFINE SCHEMA TABLE OF CAMER LIST
class Camera(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(80), nullable=False)
  ipaddress = db.Column(db.String(30), nullable=False)
  location = db.Column(db.String(120), nullable=False)
  thumbnail = db.Column(db.String(200))
  online = db.Column(db.String(4))
  thumbnails = db.relationship("Thumbnail", backref=backref("camera", lazy=True))
  videos = db.relationship("Video", backref=backref("camera", lazy=True))

  def __init__(self, name, ipaddress, location, thumbnail, online):
    self.name = name
    self.ipaddress = ipaddress
    self.location = location
    self.thumbnail = thumbnail
    self.online = online

# DEFINE SHCEMA TABLE OF VIDEO LIST
class Video(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  path = db.Column(db.String(80), nullable=False)
  time = db.Column(db.DateTime, nullable=False)
  camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'))

  def __init__(self, path, time, camera_id):
    self.path = path
    self.time = time
    self.camera_id = camera_id

# DEFINE SCHEMA Table OF THUMBNAIL LIST
class Thumbnail(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  path = db.Column(db.String(80), nullable=False)
  time = db.Column(db.DateTime, nullable=False)
  camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'))

  def __init__(self, path, time, camera_id):
    self.path = path
    self.time = time
    self.camera_id = camera_id
