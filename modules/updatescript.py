import subprocess

from quart import request, url_for

from settings import UPDATE_PASSWORD


def init(app):
    @app.route("/update", methods=["POST", "GET"])
    async def updater():
        if request.method == "GET":
            return url_for("base")
        password = request.headers.get("Password", default="")
        if password != UPDATE_PASSWORD:
            return "Unauthorised", 401
        subprocess.Popen(
            "/usr/bin/sudo /usr/bin/systemctl start website-updater",
            shell=True,
        )
        return "1"
