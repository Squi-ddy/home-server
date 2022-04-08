from modules import astroview, main, supervend, updatescript


def init_all(app):
    main.init(app)
    updatescript.init(app)
    supervend.init(app)
    astroview.init(app)
