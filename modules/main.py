from quart import redirect, render_template

def init(app):
    @app.route('/', defaults={'path': ""}, subdomain = "www")
    @app.route('/<path>', subdomain = "www")
    async def direct(path):
        return redirect(f"https://squiddy.me/{path}")

    @app.route('/')
    async def base():
        return "a"#await render_template("index.html")