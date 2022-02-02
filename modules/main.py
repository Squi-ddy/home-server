from quart import redirect, render_template
from settings import SERVER_NAME, IS_HTTPS

def init(app):
    @app.route('/', subdomain = "www")
    @app.route('/<path:path>', subdomain = "www")
    async def direct(path = ""):
        protocol = 'https' if IS_HTTPS else 'http'
        return redirect(f"{protocol}://{SERVER_NAME}/{path}")

    @app.route('/')
    async def base():
        return await render_template("index.html")

    @app.route('/is-up/')
    async def is_up():
        return "1"