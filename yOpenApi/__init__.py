from marshmallow.validate import Regexp

class yOpenSanic():
  def openapi_v3(self):
    result = {
      "openapi": "3.0.1", "info": self._openapi_v3_info(), "servers": self._openapi_v3_servers(), "paths": self._openapi_v3_paths(),
      "components": {"schemas": self._openapi_v3_schemas()}
    }
    if hasattr(self, "auth"):
      result["components"]["securitySchemes"] = self._openapi_v3_security()

    # if hasattr(self, "auth"):
    #   self._process_auth()

    return result

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

  def _operation_security(self, decorators):
    if callable(decorators["allowed"]["condition"]):
      return {"description": decorators["allowed"]["condition"].__doc__, "name": decorators["allowed"]["condition"].__name__}
    else:
      return decorators["allowed"]["condition"]

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
            
            if "allowed" in data["method"].__decorators__:
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"].__decorators__)

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

            if "allowed" in data["method"].__decorators__:
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"].__decorators__)

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

            if "allowed" in data["method"].__decorators__:
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"].__decorators__)

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

            if "allowed" in data["method"].__decorators__:
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"].__decorators__)

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

            if "allowed" in data["method"].__decorators__:
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"].__decorators__)

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

            if "allowed" in data["method"].__decorators__:
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"].__decorators__)

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

            if "allowed" in data["method"].__decorators__:
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"].__decorators__)

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

            if "allowed" in data["method"].__decorators__:
              result[url][verb]["{}security".format(metadata_prefix)] = self._operation_security(data["method"].__decorators__)

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

  def _process_auth(self):
    from json import dumps

    self.log.info(dumps(dir(self.auth), indent = 2))
    self.log.info(dumps(dir(self.auth.config), indent = 2))
    self.log.info(self.auth.config.path_to_authenticate())
    self.log.info(self.auth.config.path_to_refresh())
    self.log.info(self.auth.config.path_to_retrieve_user())
    self.log.info(self.auth.config.path_to_verify())

  def marshmallow2openapiTypes(self, field):
    if field.__class__.__name__ in ["ObjectId", "UUID", "DateTime", "LocalDateTime", "Date", "TimeDelta", "Url", "Email"]:
      return "string"
    elif field.__class__.__name__ in ["List"]:
      return "array"
    elif field.__class__.__name__ in ["Decimal", "Float"]:
      return "number"
    elif field.__class__.__name__ in ["Dict"]:
        return "object"
    else:
      return field.__class__.__name__.lower()

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

  def integer(self, field):
    schema = {"type": "integer"}

    for validator in field.validators:
      if validator.__class__.__name__ == "Range":
        if validator.max is not None:
          schema["maximum"] = validator.max

        if validator.min is not None:
          schema["minimum"] = validator.min

    return schema

  def boolean(self, field):
    return {"type": "boolean"}

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

  def object(self, field):
    schema = {"type": "object"}

    return schema
