from quart import Quart

import modules.enabled as modules
from settings import SERVER_NAME

app = Quart(__name__)
app.config["SERVER_NAME"] = SERVER_NAME

modules.init_all(app)
