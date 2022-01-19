from quart import Quart, redirect, render_template
import psycopg
import modules.supervend

app = Quart(__name__)
app.config['SERVER_NAME'] = 'squiddy.me'

@app.route('/', defaults={'path': ""}, subdomain = "www")
@app.route('/<path>', subdomain = "www")
async def direct(path):
    return await redirect(f"https://squiddy.me/{path}")

@app.route('/')
async def base():
    return await render_template("index.html")

modules.supervend.init(app)