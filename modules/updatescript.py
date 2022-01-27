import subprocess
import os
from quart import redirect, request
from settings import UPDATE_PASSWORD

def init(app):
    @app.route('/update', methods = ["POST","GET"])
    async def updater():
        if (request.method == "GET"): return redirect("https://squiddy.me/")
        password = request.headers.get("Password", default="")
        if (password != UPDATE_PASSWORD): return ("Unauthorised", 401)
        subprocess.Popen("/usr/bin/sudo /usr/bin/systemctl start website-updater", shell=True)
        return "1"