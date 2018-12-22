from unittest import TestCase

from tests.app import models
from tests.app.app import create_app

from json import dumps
from ySanic import MyEncoder

class Tests(TestCase):
  def setUp(self):
    self.app = create_app()

  def testMinimal(self):
    self.app.log.info(dumps(self.app.openapi_v3(), indent = 2, cls = MyEncoder))
