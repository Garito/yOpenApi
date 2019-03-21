from marshmallow import fields
from marshmallow.validate import Length, Range, Regexp

from sanic import response

from yModel.mongo import ObjectId, Decimal

class yOpenSanic():
  async def openapi(self, request):
    return response.json(self.openapi_v3())

  def openapi_v3(self):
    result = {
      "openapi": "3.0.1", "info": self._openapi_v3_info(), "servers": self._openapi_v3_servers(), "paths": self._openapi_v3_paths(),
      "components": {"schemas": self._openapi_v3_schemas()}
    }
    rootClass = getattr(self.models, list(filter(lambda tup: tup[1]["type"] == "root", self._inspected.items()))[0][0])
    if "yAuth" in [base.__name__ for base in rootClass.__bases__]:
      result["components"]["securitySchemes"] = self._openapi_v3_security()

    return result

  def schema2model(self, name, schema):
    fields = {}
    for prop_name, prop in schema["properties"].items():
      fields[prop_name] = self.openapiType2marshmallow(prop, prop_name in schema["required"])

    return type(name, (self.models.MongoTree,), fields)

  def _openapi_v3_info(self):
    return {
      "title": self.config["TITLE"],
      "description": self.config["DESCRIPTION"],
      "termsOfService": self.config["TERMS_OF_SERVICE"],
      "contact": self.config["CONTACT"],
      "license": self.config["LICENSE"],
      "version": self.config["VERSION"]
    }

  def _openapi_v3_servers(self):
    return [{"url": self.config["API_SERVER_NAME"], "description": "{}'s main server".format(self.config.get("TITLE", "API"))}]

  def _openapi_v3_paths(self):
    paths = {}
    for model_name, model in self._inspected.items():
      if model["type"] == "independent":
        paths.update(self._v3_independent(model_name, model))
      elif model["type"] == "root":
        paths.update(self._v3_root(model_name, model))

        if model["recursive"]:
          paths.update(self._v3_tree(model_name, model))
      elif model["type"] == "tree":
        paths.update(self._v3_tree(model_name, model))

    return paths

  def _operation_security(self, method):
    if "allowed" in method.__decorators__:
      if callable(method.__decorators__["allowed"]["condition"]):
        return {"description": method.__decorators__["allowed"]["condition"].__doc__, "name": method.__decorators__["allowed"]["condition"].__name__}
      else:
        return method.__decorators__["allowed"]["condition"]
    elif "permission" in method.__decorators__:
      return method.__qualname__.replace("__call__", "call").replace(".", "/")

  def _v3_tree(self, name, model):
    model_class = getattr(self.models, name)
    prefix = getattr(model_class, "url_prefix", "")
    metadata_prefix = self.config.get("OAV3_METADATA_PREFIX", "x-yrest-")
    result = {}
    if "out" in model:
      if "views" in model["out"]:
        verb = "get"
        for method_name, data in model["out"]["views"].items():
          if not data["method"].__decorators__.get("notaroute", False):
            url = "{}/{{{}_Path}}/".format(prefix, name) if method_name == "__call__" else "{}/{{{}_Path}}/{}".format(prefix, name, method_name)
            if url not in result:
              result[url] = {}
            result[url][verb] = {"operationId": "{}/{}".format(model_class.__name__, "call" if method_name == "__call__" else method_name)}

            description = data["method"].__doc__ or None
            if description:
              result[url][verb]["description"] = description

            result[url]["parameters"] = [{"name": "{}_Path".format(name), "in": "path", "required": True, "schema": {"type": "string"}}]
            result[url][verb]["responses"] = self._v3_responses(data["decorators"])
            
            if {"allowed", "permission"}.intersection(set(data["method"].__decorators__.keys())):
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"])

      if "removers" in model["out"]:
        verb = "delete"
        for method_name, data in model["out"]["removers"].items():
          if not data["method"].__decorators__.get("notaroute", False):
            url = "{}/{{{}_Path}}/".format(prefix, name)
            if url not in result:
              result[url] = {}
            result[url][verb] = {"operationId": "{}/{}".format(model_class.__name__, "call" if method_name == "__call__" else method_name)}

            description = data["method"].__doc__ or None
            if description:
              result[url][verb]["description"] = description

            result[url]["parameters"] = [{"name": "{}_Path".format(name), "in": "path", "required": True, "schema": {"type": "string"}}]
            result[url][verb]["responses"] = self._v3_responses(data["decorators"])

            # if "allowed" in data["method"].__decorators__:
            if {"allowed", "permission"}.intersection(set(data["method"].__decorators__.keys())):
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"])

    if "in" in model:
      if "factories" in model["in"]:
        verb = "post"
        for method_name, data in model["in"]["factories"].items():
          if not data["method"].__decorators__.get("notaroute", False):
            factories = getattr(model_class, "factories", {})
            index = list(factories.values()).index(method_name)
            factory_list = list(factories.keys())[index]

            url = "{}/{{{}_Path}}/new/{}".format(prefix, name, factory_list)
            if url not in result:
              result[url] = {}
            result[url][verb] = {"operationId": "{}/{}".format(model_class.__name__, "call" if method_name == "__call__" else method_name)}

            description = data["method"].__doc__ or None
            if description:
              result[url][verb]["description"] = description

            result[url][verb].update(self._v3_consumes(data["decorators"]["consumes"]))
            if "parameters" not in result[url]:
              result[url]["parameters"] = []
            if not any(map(lambda x: x["name"] == "{}_Path".format(name), result[url]["parameters"])):
              result[url]["parameters"].append({"name": "{}_Path".format(name), "in": "path", "required": True, "schema": {"type": "string"}})
            result[url][verb]["requestBody"] = self._v3_requestBody(data["decorators"]["consumes"])
            result[url][verb]["responses"] = self._v3_responses(data["decorators"])

            # if "allowed" in data["method"].__decorators__:
            if {"allowed", "permission"}.intersection(set(data["method"].__decorators__.keys())):
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"])

      if "updaters" in model["in"]:
        verb = "put"
        for method_name, data in model["in"]["updaters"].items():
          if not data["method"].__decorators__.get("notaroute", False):
            url = "{}/{{{}_Path}}/".format(prefix, name) if method_name == "update" else "{}/{{{}_Path}}/{}".format(prefix, name, method_name)
            if url not in result:
              result[url] = {}
            result[url][verb] = {"operationId": "{}/{}".format(model_class.__name__, "call" if method_name == "__call__" else method_name)}

            description = data["method"].__doc__ or None
            if description:
              result[url][verb]["description"] = description

            result[url][verb].update(self._v3_consumes(data["decorators"]["consumes"]))
            if "parameters" not in result[url]:
              result[url]["parameters"] = []
            if not any(map(lambda x: x["name"] == "{}_Path".format(name), result[url]["parameters"])):
              result[url]["parameters"].append({"name": "{}_Path".format(name), "in": "path", "required": True, "schema": {"type": "string"}})
            result[url][verb]["requestBody"] = self._v3_requestBody(data["decorators"]["consumes"])
            result[url][verb]["responses"] = self._v3_responses(data["decorators"])

            # if "allowed" in data["method"].__decorators__:
            if {"allowed", "permission"}.intersection(set(data["method"].__decorators__.keys())):
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"])

    return result

  def _v3_root(self, name, model):
    model_class = getattr(self.models, name)
    prefix = getattr(model_class, "url_prefix", "")
    metadata_prefix = self.config.get("OAV3_METADATA_PREFIX", "x-yrest-")
    result = {}
    if "out" in model:
      if "views" in model["out"]:
        verb = "get"
        for method_name, data in model["out"]["views"].items():
          if not data["method"].__decorators__.get("notaroute", False):
            url = "{}/".format(prefix) if method_name == "__call__" else "{}/{}".format(prefix, method_name)
            if url not in result:
              result[url] = {}
            result[url][verb] = {"operationId": "{}/{}".format(model_class.__name__, "call" if method_name == "__call__" else method_name)}

            description = data["method"].__doc__ or None
            if description:
              result[url][verb]["description"] = description

            result[url][verb]["responses"] = self._v3_responses(data["decorators"])

            # if "allowed" in data["method"].__decorators__:
            if {"allowed", "permission"}.intersection(set(data["method"].__decorators__.keys())):
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"])

      if "removers" in model["out"]:
        verb = "delete"
        for method_name, data in model["out"]["removers"].items():
          if not data["method"].__decorators__.get("notaroute", False):
            url = "{}/".format(prefix)
            if url not in result:
              result[url] = {}
            result[url][verb] = {"operationId": "{}/{}".format(model_class.__name__, "call" if method_name == "__call__" else method_name)}

            description = data["method"].__doc__ or None
            if description:
              result[url][verb]["description"] = description

            result[url][verb]["responses"] = self._v3_responses(data["decorators"])

            # if "allowed" in data["method"].__decorators__:
            if {"allowed", "permission"}.intersection(set(data["method"].__decorators__.keys())):
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"])

    if "in" in model:
      if "factories" in model["in"]:
        verb = "post"
        for method_name, data in model["in"]["factories"].items():
          if not data["method"].__decorators__.get("notaroute", False):
            factories = getattr(model_class, "factories", {})
            index = list(factories.values()).index(method_name)
            factory_list = list(factories.keys())[index]

            url = "{}/new/{}".format(prefix, factory_list)
            if url not in result:
              result[url] = {}
            result[url][verb] = {"operationId": "{}/{}".format(model_class.__name__, "call" if method_name == "__call__" else method_name)}

            description = data["method"].__doc__ or None
            if description:
              result[url][verb]["description"] = description

            result[url][verb].update(self._v3_consumes(data["decorators"]["consumes"]))
            result[url][verb]["responses"] = self._v3_responses(data["decorators"])

            # if "allowed" in data["method"].__decorators__:
            if {"allowed", "permission"}.intersection(set(data["method"].__decorators__.keys())):
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"])

      if "updaters" in model["in"]:
        verb = "put"
        for method_name, data in model["in"]["updaters"].items():
          if not data["method"].__decorators__.get("notaroute", False):
            url = "{}/{}".format(prefix, method_name)
            if url not in result:
              result[url] = {}
            result[url][verb] = {"operationId": "{}/{}".format(model_class.__name__, "call" if method_name == "__call__" else method_name)}

            description = data["method"].__doc__ or None
            if description:
              result[url][verb]["description"] = description

            result[url][verb].update(self._v3_consumes(data["decorators"]["consumes"]))
            result[url][verb]["responses"] = self._v3_responses(data["decorators"])

            # if "allowed" in data["method"].__decorators__:
            if {"allowed", "permission"}.intersection(set(data["method"].__decorators__.keys())):
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"])

    return result

  def _v3_independent(self, name, model):
    model_class = getattr(self.models, name)
    prefix = getattr(model_class, "url_prefix", "")
    result = {}
    if "out" in model:
      if "views" in model["out"]:
        verb = "get"
        for method_name, data in model["out"]["views"].items():
          if method_name == "__call__":
            url = "{}/{{Id}}".format(prefix)
          elif method_name == "get_all":
            url = "{}{}".format(prefix, "" if bool(prefix) else "/")
          else:
            url = "{}/{}".format(prefix, method_name)
          if url not in result:
            result[url] = {}
          result[url][verb] = {}

          description = data["method"].__doc__ or None
          if description:
            result[url][verb]["description"] = description

          result[url][verb]["responses"] = self._v3_responses(data["decorators"])

      if "removers" in model["out"]:
        verb = "delete"
        for method_name, data in model["out"]["removers"].items():
          url = "{}/{{Id}}".format(prefix)
          if url not in result:
            result[url] = {}
          result[url][verb] = {}

          description = data["method"].__doc__ or None
          if description:
            result[url][verb]["description"] = description

          result[url][verb]["responses"] = self._v3_responses(data["decorators"])

    if "in" in model:
      if "factories" in model["in"]:
        verb = "post"
        for method_name, data in model["in"]["factories"].items():
          url = "{}{}".format(prefix, "" if bool(prefix) else "/")
          if url not in result:
            result[url] = {}
          result[url][verb] = {}

          description = data["method"].__doc__ or None
          if description:
            result[url][verb]["description"] = description

          result[url][verb]["requestBody"] = self._v3_requestBody(data["decorators"]["consumes"])
          result[url][verb]["responses"] = self._v3_responses(data["decorators"])

      if "updaters" in model["in"]:
        verb = "put"
        for method_name, data in model["in"]["updaters"].items():
          url = "{}/{{Id}}".format(prefix)
          if url not in result:
            result[url] = {}
          result[url][verb] = {}

          description = data["method"].__doc__ or None
          if description:
            result[url][verb]["description"] = description

          result[url][verb]["requestBody"] = self._v3_requestBody(data["decorators"]["consumes"])
          result[url][verb]["responses"] = self._v3_responses(data["decorators"])

    return result

  def _v3_responses(self, decorators):
    result = {}

    if "produces" in decorators:
      result["200"] = self._v3_response(decorators["produces"])

    if "can_crash" in decorators:
      for exc_name, exception in decorators["can_crash"].items():
        result[exception["code"]] = self._v3_response(exception)

    return result

  def _v3_response(self, decorator):
    result = {}
    if decorator["description"]:
      result["description"] = decorator["description"]

    renderer = decorator["renderer"]
    if renderer:
      rendered = renderer({})
      if hasattr(rendered, "content_type"):
        content_type = rendered.content_type
      else:
        content_type = None
    else:
      content_type = "application/json"
    # content_type = renderer({}).content_type if renderer else "application/json"

    result["content"] = {}

    if content_type:
      schema = getattr(self.models, decorator["model"]) if isinstance(decorator["model"], str) else decorator["model"]

      if not hasattr(self, "_used_schemas"):
        self._used_schemas = set()
      self._used_schemas.add(schema)

      result["content"][content_type] = {"schema": {"$ref": "#/components/schemas/{}".format(schema().__class__.__name__)}}

    return result

  def _v3_consumes(self, consumes):
    result = {}

    if not isinstance(consumes, list):
      consumes = [consumes]

    for decorator in consumes:
      if decorator["from"] in ["json", "form"]:
        result["requestBody"] = self._v3_requestBody(decorator)
      else:
        if "parameters" not in result:
          result["parameters"] = []
        result["parameters"].append(self._v3_params(decorator))

    return result

  def _v3_requestBody(self, decorator):
    result = {}
    if decorator["description"]:
      result["description"] = decorator["description"]

    if decorator["from"] == "json":
      content_type = "application/json"
    elif decorator["from"] == "form":
      pass

    result["content"] = {}

    schema = getattr(self.models, decorator["model"]) if isinstance(decorator["model"], str) else decorator["model"]

    if not hasattr(self, "_used_schemas"):
      self._used_schemas = set()
    self._used_schemas.add(schema)

    result["content"][content_type] = {"schema": {"$ref": "#/components/schemas/{}".format(schema().__class__.__name__)}}
    return result

  def _v3_params(self, decorator):
    schema = getattr(self.models, decorator["model"]) if isinstance(decorator["model"], str) else decorator["model"]
    schema_name = schema().__class__.__name__

    result = {"name": schema_name}

    if decorator["from"] == "query":
      result["in"] = "query"
    elif decorator["from"] == "headers":
      result["in"] = "header"
    elif decorator["from"] == "cookies":
      result["in"] = "cookie"

    if decorator["description"]:
      result["description"] = decorator["description"]

    result["required"] = True

    if not hasattr(self, "_used_schemas"):
      self._used_schemas = set()
    self._used_schemas.add(schema)
    result["schema"] = {"$ref": "#/components/schemas/{}".format(schema_name)}
    
    result["style"] = "simple"

    return result

  def _openapi_v3_schemas(self):
    return {model().__class__.__name__: self._v3_schema(model()) for model in self._used_schemas}

  def _v3_schema(self, model):
    schema = {"type": "object", "properties": {}}
    required = []

    metadata_prefix = self.config.get("OAV3_METADATA_PREFIX", "x-yrest-")
    exclusions = getattr(model, "exclusions", False)
    for field_name in model.fields:
      if not exclusions or field_name not in exclusions:
        field = model.fields[field_name]
        schema["properties"][field.name] = {}

        if field.required:
          required.append(field.name)

        schema["properties"][field.name] = getattr(self, self.marshmallow2openapiTypes(field))(field)

        regex = list(filter(lambda validator: isinstance(validator, Regexp), field.validate or []))
        if regex:
          schema["properties"][field.name]["pattern"] = regex[0].regex.pattern

        for key, value in field.metadata.items():
          schema["properties"][field.name]["{}{}".format(metadata_prefix, key.lower())] = value

    if required:
      schema["required"] = required

    if hasattr(model, "form"):
      schema["{}form".format(metadata_prefix)] = model.form

    return schema

  def _openapi_v3_security(self):
    return {"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}

  def marshmallow2openapiTypes(self, field):
    if field.__class__.__name__ in ["ObjectId", "UUID", "DateTime", "Date", "TimeDelta", "Url", "Email"]:
      return "string"
    elif field.__class__.__name__ in ["List"]:
      return "array"
    elif field.__class__.__name__ in ["Decimal", "Float"]:
      return "number"
    elif field.__class__.__name__ in ["yGeoField"]:
      return "geo"
    elif field.__class__.__name__ in ["Dict"]:
      return "object"
    else:
      return field.__class__.__name__.lower()

  def openapiType2marshmallow(self, schema, required):
    if schema["type"] == "string":
      return self.from_string(schema, required)
    elif schema["type"] == "array":
      return self.from_array(schema, required)
    elif schema["type"] == "number":
      return self.from_number(schema, required)
    elif schema["type"] == "geo":
      return self.from_geo(schema, required)
    elif schema["type"] == "object":
      return self.from_object(schema, required)
    else:
      return getattr(self, "from_{}".format(schema["type"]))

  def string(self, field):
    schema = {"type": "string"}

    class_name = field.__class__.__name__
    if class_name == "Date":
      schema["format"] = "date"
    elif class_name == "DateTime":
      schema["format"] = "date-time"
    elif class_name == "Email":
      schema["format"] = "email"
    elif class_name == "UUID":
      schema["format"] = "uuid"
    elif class_name == "Url":
      schema["format"] = "uri"
    elif class_name == "ObjectId":
      if field.allow_none:
        schema["type"] = ["string", "null"]

    for validator in field.validators:
      if validator.__class__.__name__ == "Length":
        if validator.max is not None:
          schema["maxLength"] = validator.max

        if validator.min is not None:
          schema["minLength"] = validator.min

    return schema

  def from_string(self, schema, required):
    params = {}
    if required:
      params["required"] = required

    length_params = {}
    if "maxLength" in schema:
      length_params["max"] = schema["maxLength"]
    if "minLength" in schema:
      length_params["min"] = schema["minLength"]
    if length_params:
      params["validate"] = Length(**length_params)

    if schema.get("format", None) == "date":
      return fields.Date(**params)
    elif schema.get("format", None) == "date-time":
      return fields.DateTime(**params)
    elif schema.get("format", None) == "email":
      return fields.Email(**params)
    elif schema.get("format", None) == "uuid":
      return fields.UUID(**params)
    elif schema.get("format", None) == "uri":
      return fields.Url(**params)
    elif schema["type"] == ["string", "null"]:
      return ObjectId(**params)
    else:
      return fields.Str(**params)

  def number(self, field):
    schema = {"type": "number"}

    class_name = field.__class__.__name__
    if class_name == "Float":
      schema["format"] = "float"
    elif class_name == "Decimal":
      schema["format"] = "double"

    for validator in field.validators:
      if validator.__class__.__name__ == "Range":
        if validator.max is not None:
          schema["maximum"] = validator.max

        if validator.min is not None:
          schema["minimum"] = validator.min

    return schema

  def from_number(self, schema, required):
    params = {}
    if required:
      params["required"] = required

    range_params = {}
    if "maximum" in schema:
      range_params["max"] = schema["maximum"]
    if "minimum" in schema:
      range_params["min"] = schema["minimum"]
    if range_params:
      params["validate"] = range_params

    if schema.get("format", None) == "float":
      return fields.Float(**params)
    else:
      return Decimal(**params)

  def integer(self, field):
    schema = {"type": "integer"}

    for validator in field.validators:
      if validator.__class__.__name__ == "Range":
        if validator.max is not None:
          schema["maximum"] = validator.max

        if validator.min is not None:
          schema["minimum"] = validator.min

    return schema

  def from_integer(self, schema, required):
    params = {}
    if required:
      params["required"] = required
    
    range_params = {}
    if "maximum" in schema:
      range_params["max"] = schema["maximum"]
    if "minimum" in schema:
      range_params["min"] = schema["minimum"]
    if range_params:
      params["validate"] = range_params

    return fields.Int(**params)

  def boolean(self, field):
    return {"type": "boolean"}

  def from_boolean(self, schema, required):
    return fields.Bool(required = required)

  def array(self, field):
    schema = {"type": "array", "items": {"type": self.marshmallow2openapiTypes(field.container)}}

    for validator in field.validators:
      if validator.__class__.__name__ == "Range":
        if validator.max is not None:
          schema["maximum"] = validator.max
        
        if validator.min is not None:
          schema['minimum'] = validator.min
      elif validator.__class__.__name__ == "Length":
        if validator.max is not None:
          schema["maxItems"] = validator.max

        if validator.min is not None:
          schema["minItems"] = validator.min

        if validator.equal is not None:
          schema["maxItems"] = validator.equal
          schema["minItems"] = validator.equal

    return schema

  def from_array(self, schema, required):
    params = {}
    range_params = {}
    if "maximum" in schema:
      range_params["max"] = schema["maximum"]
    if "minimum" in schema:
      range_params["min"] = schema["minimum"]
    
    length_params = {}
    if "maxItems" in schema and "minItems" in schema:
      length_params["equal"] = schema["maxItems"]
    else:
      if "maxItems" in schema:
        length_params["max"] = schema["maxItems"]
      if "minItems" in schema:
        length_params["min"] = schema["minItems"]

    if range_params and length_params:
      params["validate"] = [Range(**range_params), Length(**length_params)]
    else:
      if range_params:
        params["validate"] = Range(**range_params)
      if length_params:
        params["validate"] = Length(**length_params)

    submodel = self.openapiType2marshmallow(schema["items"], False)
    return fields.List(submodel.__class__, **params)

  def geo(self, field):
    return {"type": "object", "x-yrest-input_type": "geo"}

  def from_geo(self, schema, required):
    from yGeoField import yGeoField
    return yGeoField(required = required)

  def object(self, field):
    return {"type": "object"}

  def from_object(self, schema, required):
    return fields.Dict(required = required)
