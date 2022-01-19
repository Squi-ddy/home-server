from quart import redirect, render_template

def init(app):
    @app.route('/', defaults={'path': ""}, subdomain = "www")
    @app.route('/<path>', subdomain = "www")
    async def direct(path):
        return await redirect(f"https://squiddy.me/{path}")

    @app.route('/')
    async def base():
        return await render_template("index.html")