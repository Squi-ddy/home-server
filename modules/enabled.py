import modules.main as main
import modules.supervend as supervend
import modules.updatescript as updatescript


def init_all(app):
    main.init(app)
    updatescript.init(app)
    supervend.init(app)
