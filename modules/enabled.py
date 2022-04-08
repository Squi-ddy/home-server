from modules import main
from modules import supervend
from modules import updatescript
from modules import astroview


def init_all(app):
    main.init(app)
    updatescript.init(app)
    supervend.init(app)
    astroview.init(app)
