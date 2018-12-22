from os import urandom
from os.path import exists
from binascii import hexlify

class Config:
  DEBUG = True
  DEBUG_EMAILS = True
  TESTING = True

  HOST = "localhost"
  PUBLIC_HOST = HOST
  PORT = 8000
  SERVER_NAME = "http://{}:{}".format(PUBLIC_HOST, PORT)
  API_SERVER_NAME = SERVER_NAME

  MONGO_TABLE = "tests"
  MONGO = {"host": PUBLIC_HOST, "port": 27017, "db": MONGO_TABLE}
  MONGO_URI = "mongodb://{host}:{port}/{db}".format(**MONGO)

  jwt_secret_file_path = "/run/secrets/jwt_secret"
  if exists(jwt_secret_file_path):
    with open(jwt_secret_file_path) as f:
      JWT_SECRET = f.read()
  else:
    JWT_SECRET = hexlify(urandom(32))

  TITLE = "yOpenApi test app"
  DESCRIPTION = "This app allows to test yOpenApy"
  TERMS_OF_SERVICE = "{}/#/about".format(SERVER_NAME)
  CONTACT = {"name": "Sistes.net", "url": SERVER_NAME, "email": "info@sistes.net"}
  LICENSE = {"name": "Sistes license", "url": "{}/#/license".format(SERVER_NAME)}
  VERSION = "1.0.0"
