from datetime import datetime, timedelta

import bson

from marshmallow import fields, pre_load
from marshmallow.validate import ValidationError

from sanic import response
from sanic.exceptions import Unauthorized

from yModel import Schema, OkSchema, ErrorSchema, OkResult, OkDictResult, OkListResult, consumes, produces, can_crash
from yModel.mongo import ObjectId, MongoSchema, MongoTree, NotFound
from ySanic import notaroute
from yAuth import yAuth, Auth, AuthToken, generate_password_hash, check_password_hash, allowed

def myself(args, kwargs, actor):
  if actor:
    self = args[0]
    return self._id == actor._id
  return False

def owner(args, kwargs, actor):
  return self.path.startswith("/{}".format(actor.slug))

async def can_actor_change_password(args, kwargs, actor):
  user, request, model = args[:3]
  return (actor and actor._id == user._id and check_password_hash(user.password, model.old)) or await user.check_reset_code(model.code, request.app.models.ResetPasswordRequest(request.app.table))

class ExistsException(Exception):
  pass

class SilentErrorSchema(ErrorSchema):
  ok = fields.Bool(required = True, missing = True)

class ResetPasswordRequest(MongoSchema):
  _id = ObjectId()
  type_ = fields.Str(attribute = "type", missing = "ResetPassword")
  email = fields.Email(required = True)
  code = fields.Str(required = True, missing = lambda: str(uuid4()))
  date = fields.DateTime(required = True, missing = (datetime.utcnow() + timedelta(minutes = 5)).isoformat())

class ChangePasswordRequest(Schema):
  code = fields.Str()
  old = fields.Str()
  new = fields.Str(required = True)

class NameRequest(Schema):
  name = fields.Str(required = True)
  slug = fields.Str(required = True)

class Node(MongoTree):
  _id = ObjectId()
  type_ = fields.Str(attribute = "type", missing = "Node")
  name = fields.Str(required = True)
  slug = fields.Str(required = True)
  path = fields.Str(required = True)
  nodes = fields.List(fields.Str, missing = [])

  children_models = {"nodes": "Node"}
  factories = {"nodes": "create_child"}

  @can_crash(Unauthorized, code = 401, description = "Returns an error if the actor is not the owner")
  @can_crash(ValidationError, code = 400, description = "Returns the fields that don't validate")
  @produces(OkDictResult, as_ = "result")
  @consumes("Node")
  @allowed(owner)
  async def create_child(self, request, as_, model):
    return await super().create_child(model, as_)

  @can_crash(Unauthorized, code = 401, description = "Returns an error if the actor is not the owner")
  @produces(OkListResult, as_ = "result")
  @allowed(owner)
  async def get_children(self, request):
    result = await self.children("nodes", request.app.models)
    return result.to_plain_dict()

  @can_crash(Unauthorized, code = 401, description = "Returns an error if the actor is not the owner")
  @produces(OkListResult, as_ = "result")
  @allowed(owner)
  async def get_ancestors(self, request):
    nodes = await self.ancestors(request.app.models)
    return [node.to_plain_dict() for node in nodes]

  @can_crash(Unauthorized, code = 401, description = "Returns an error if the actor is not the owner")
  @produces(OkDictResult, as_ = "result")
  @allowed(owner)
  async def __call__(self, request):
    return self.to_plain_dict()

  @can_crash(Unauthorized, code = 401, description = "Returns an error if the actor is not the owner")
  @can_crash(ValidationError, code = 400, description = "Returns the fields that don't validate")
  @consumes(NameRequest)
  @produces(OkDictResult, as_ = "result")
  @allowed(owner)
  async def update(self, request, model):
    result = await super().update(model.get_data(), request.app.models)
    return result.to_plain_dict()

  @can_crash(Unauthorized, code = 401, description = "Returns an error if the actor is not the owner")
  @produces(OkResult, as_ = "result")
  @allowed(owner)
  async def remove(self, request):
    _id = str(self._id)
    result = await self.delete(request.app.models)
    return _id

class User(MongoTree):
  _id = ObjectId()
  type_ = fields.Str(attribute = "type", missing = "User")
  path = fields.Str(required = True, missing = "/")
  name = fields.Str(required = True)
  slug = fields.Str(required = True)
  email = fields.Email(required = True)
  password = fields.Str(required = True)
  trees = fields.List(fields.Str, required = True, missing = [])
  roles = fields.List(fields.Str, required = True, missing = ['user'])

  children_models = {"trees": "Node"}
  factories = {"trees": "create_tree"}

  @pre_load
  def pre_load(self, data):
    if "_id" not in data and "password" in data and not data["password"].startswith("pbkdf2:sha256:"):
      data["password"] = generate_password_hash(data["password"])
    return data

  @classmethod  
  async def exists(cls, table, email, get_model = False):
    model = cls(table = table)
    try:
      await model.get(email = email)
      return model if get_model else True
    except Exception:
      return False

  @produces(OkDictResult, as_ = "result", description = "Returns a dictionary with the user's content")
  async def __call__(self, request):
    return self.to_plain_dict()

  async def check_reset_code(self, code, model):
    try:
      await model.get(code = code)
      return self.email == model.email
    except Exception:
      return False

  @can_crash(Unauthorized, code = 401, description = "Returns an error if the actor is not the user")
  @produces(OkSchema, description = "Returns ok = True if the password has been changed")
  @consumes(ChangePasswordRequest)
  @allowed(can_actor_change_password)
  async def change_password(self, request, model):
    if getattr(model, "code", False):
      resetModel = ResetPasswordRequest(self.table)
      await resetModel.get(code = model.code)
      await resetModel.delete()
    await self.update({"password": generate_password_hash(model.new)})

  @can_crash(Unauthorized, code = 401, description = "Returns an error if the actor is not the user")
  @can_crash(ValidationError, code = 400, description = "Returns the fields that don't validate")
  @produces(OkDictResult, as_ = "result", description = "Returns a dictionary with the new tree's content")
  @consumes(Node)
  @allowed(myself)
  async def create_tree(self, request, as_, model):
    return await super().create_child(model, as_)

  @can_crash(Unauthorized, code = 401, description = "Returns an error if the actor is not the user")
  @produces(OkListResult, as_ = "result", description = "Returns a list of the user's trees")
  @allowed(myself)
  async def get_trees(self, request):
    result = await self.children("trees", request.app.models)
    return result.to_plain_dict()

class Invitation(MongoTree):
  _id = ObjectId()
  type_ = fields.Str(attribute = "type", missing = "Invitation")
  email = fields.Email(required = True)
  slug = fields.Str(required = True)
  path = fields.Str(required = True, missing = "/")

  slugable = "email"

  @classmethod
  async def exists(cls, table, email, get_model = False):
    model = cls(table)
    try:
      await model.get(email = email)
      return model if get_model else True
    except NotFound:
      return False

  @produces(OkDictResult, as_ = "result", description = "Returns a dictionary with the invitation's content")
  async def __call__(self, request):
    return self.to_plain_dict()

class Community(MongoTree, yAuth):
  _id = ObjectId()
  type_ = fields.Str(attribute = "type", missing = "Community")
  path = fields.Str(required = True)
  name = fields.Str(required = True)
  slug = fields.Str(required = True)
  description = fields.Str()
  users = fields.List(ObjectId, required = True, missing = [])
  invitations = fields.List(ObjectId, required = True, missing = [])

  children_models = {"users": "User", "invitations": "Invitation"}
  factories = {"users": "create_user", "invitations": "create_invitation"}

  @produces(OkDictResult, as_ = "result", description = "Returns a dictionary with the community's data")
  async def __call__(self, request):
    return self.to_plain_dict()

  @can_crash(ExistsException, SilentErrorSchema, code = 409, description = "Returns ok = True even if the invitation is not found")
  @can_crash(ValidationError, code = 400, description = "Returns the fields that don't validate")
  @produces(OkSchema, description = "Returns ok = True if the invitation has been created successfuly")
  @consumes(Invitation)
  async def create_invitation(self, request, as_, model):
    """Creates a new invitation"""
    if await model.__class__.exists(self.table, model.email):
      raise ExistsException("Already invited")

    model.table = self.table
    await self.create_child(model, as_)

  @produces(OkListResult, as_ = "result", description = "Returns a list of invitations in the community in the key result")
  @allowed(["admin"])
  async def get_invitations(self, request):
    """Returns the list of invitations in the community"""
    result = await self.children("invitations", request.app.models)
    return result.to_plain_dict()

  @can_crash(NotFound, code = 404, description = "Returns not found if there is no invitation for that user")
  @can_crash(ValidationError, code = 400, description = "Returns the fields that don't validate")
  @produces(OkSchema, description = "Returns ok = True if the user has been created successfuly")
  @consumes(User)
  async def create_user(self, request, as_, model):
    """Creates a new user from a previous invitation"""
    invitation = Invitation(self.table)
    await invitation.get(_id = bson.ObjectId(request.json.get("code", None)))
    await invitation.delete()
    await self.create_child(model, as_)

  @produces(OkListResult, as_ = "result", description = "Returns a list of users in the community in the key result")
  @allowed(["admin"])
  async def get_users(self, request):
    """Returns the list of users in the community"""
    result = await self.children("users", request.app.models)
    return result.to_plain_dict()

  @can_crash(NotFound, code = 404, renderer = lambda model: response.json(model, status = 404))
  @produces(OkSchema, description = "Returns ok = True when the reset password has been done")
  @consumes(ResetPasswordRequest)
  async def reset_password(self, request, model):
    model.table = request.app.table
    user = User(request.app.table)
    await user.get(email = model.email)
    await model.create()

    await request.app.notify("reset_password", request, {"user": user.get_data(), "data": model.get_data()})
