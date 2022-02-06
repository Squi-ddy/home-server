from quart import redirect, render_template

from settings import IS_HTTPS, SERVER_NAME, STATIC_SITE_NAME


def init(app):
    @app.route("/", subdomain="www")
    @app.route("/<path:path>", subdomain="www")
    async def direct(path=""):
        protocol = "https" if IS_HTTPS else "http"
        return redirect(f"{protocol}://{SERVER_NAME}/{path}")

    @app.route("/")
    async def base():
        return await render_template("index.html", static_site=STATIC_SITE_NAME)
