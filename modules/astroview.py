import base64
import hashlib
from datetime import datetime

import bcrypt
from quart import jsonify, redirect, request

from settings import STATIC_IS_HTTPS, STATIC_SITE_NAME

from .postgresql import get_pool

subdomain = "astroview"
db_name = "astroview"


async def check_password():
    authorisation = request.headers.get("Authorization", default="")
    params = authorisation.split()
    if len(params) != 2 or params[0] != "Basic":
        return None
    try:
        username, password = base64.b64decode(params[1]).decode("utf-8").split(":")
    except ValueError:
        return None
    async with (await get_pool(db_name)).connection() as conn:
        async with conn.cursor() as acurs:
            await acurs.execute("SELECT hash FROM users WHERE name=%s", (username,))
            if (result := await acurs.fetchone()) is not None:
                pw_hash = (
                    hashlib.sha512(password.encode("utf-8")).hexdigest().encode("utf-8")
                )
                return (
                    username
                    if bcrypt.checkpw(pw_hash, result[0].encode("utf-8"))
                    else None
                )
            return None


async def modify_password(name, password):
    resp = await check_password()
    if resp is None or resp != name:
        return "Unauthorised", 401
    if password == "":
        return True
    async with (await get_pool(db_name)).connection() as conn:
        async with conn.cursor() as acurs:
            pw_hash = (
                hashlib.sha512(password.encode("utf-8")).hexdigest().encode("utf-8")
            )
            pw_salt_hash = bcrypt.hashpw(pw_hash, bcrypt.gensalt()).decode("utf-8")
            await acurs.execute(
                "UPDATE users SET hash = %s WHERE name = %s",
                (pw_salt_hash, name),
            )
            success = acurs.rowcount
    return bool(success)


def process_datetime(to_process):
    time = process_time(to_process)
    date = process_date(to_process)
    return_datetime = {}
    return_datetime.update(time)
    return_datetime.update(date)
    return return_datetime


def process_date(to_process):
    return {
        "day": to_process.day,
        "month": to_process.month,
        "year": to_process.year,
    }


def process_time(to_process):
    return {
        "hour": to_process.hour,
        "minute": to_process.minute,
        "second": to_process.second,
    }


def init(app):
    @app.route(
        "/pages/<int:page_number>/ratings/",
        subdomain=subdomain,
        methods=["GET", "POST"],
    )
    async def av_ratings(page_number):
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT id FROM pages WHERE id = %s",
                    (page_number,),
                )
                if acurs.rowcount < 1:
                    return "No such product", 404
        if request.method == "GET":
            return await get_ratings(page_number)
        elif request.method == "POST":
            return await post_rating(page_number)

    async def get_ratings(page_number):
        results = {"reviews": []}
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT rating, rating_ct FROM pages WHERE id = %s",
                    (page_number,),
                )
                if acurs.rowcount < 1:
                    return "No such product", 404
                record = await acurs.fetchone()
                results["summary"] = {"total": record[0], "count": record[1]}
                await acurs.execute(
                    """
                    SELECT
                       id,
                       page,
                       name,
                       rating,
                       content,
                       time
                    FROM ratings
                    WHERE page = %s
                    """,
                    (page_number,),
                )
                async for record in acurs:
                    results["reviews"].append(
                        {
                            "rating_id": record[0],
                            "page": record[1],
                            "user": record[2],
                            "rating": record[3],
                            "description": record[4],
                            "time": process_datetime(record[5]),
                        }
                    )

        return jsonify(results)

    async def post_rating(page_number):
        data = await request.json
        desc = data.get("description", "")
        rating = data.get("rating", -1)
        if desc == "" or rating < 0 or not isinstance(rating, int):
            return "Invalid", 400
        resp = await check_password()
        if resp is None:
            return "Unauthorised", 401
        name = resp
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                time = datetime.now()
                await acurs.execute(
                    "INSERT INTO ratings VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (name, desc, time, page_number, rating),
                )
                if acurs.rowcount:
                    record = await acurs.fetchone()
                    await acurs.execute(
                        """
                        UPDATE pages
                        SET rating = rating + %s, rating_ct = rating_ct + 1
                        WHERE id = %s
                        """,
                        (rating, page_number),
                    )
                    return (
                        jsonify(
                            {
                                "rating_id": record[0],
                                "user": name,
                                "rating": rating,
                                "description": desc,
                                "time": process_datetime(time),
                                "page": page_number,
                            }
                        )
                        if acurs.rowcount
                        else ("Invalid", 400)
                    )
                else:
                    return "Invalid", 400

    @app.route(
        "/users/<string:username>/",
        subdomain=subdomain,
        methods=["GET", "PATCH", "POST", "DELETE"],
    )
    async def av_user_action(username):
        username = username.strip()
        if request.method == "GET":
            return await check_user(username)
        elif request.method == "POST":
            return await add_user(username)
        elif request.method == "DELETE":
            return await delete_user(username)
        elif request.method == "PATCH":
            return await modify_user(username)

    async def check_user(name):
        resp = await check_password()
        if resp is None or resp != name:
            return "Unauthorised", 401
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT name FROM users WHERE name=%s", (name,))
                row = await acurs.fetchone()
                return jsonify({"name": row[0]})

    async def add_user(name):
        data = await request.json
        password = str(data.get("password", ""))
        if len(name) > 30 or name == "" or password == "":
            return "Invalid", 400
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT name FROM users WHERE name=%s", (name,))
                if acurs.rowcount > 0:
                    return "User already exists", 400
                pw_hash = (
                    hashlib.sha512(password.encode("utf-8")).hexdigest().encode("utf-8")
                )
                pw_salt_hash = bcrypt.hashpw(pw_hash, bcrypt.gensalt()).decode("utf-8")
                await acurs.execute(
                    "INSERT INTO users VALUES (%s, %s)", (name, pw_salt_hash)
                )
                success = acurs.rowcount
        return jsonify({"name": name}) if success else ("Invalid", 400)

    async def delete_user(name):
        resp = await check_password()
        if resp is None or resp != name:
            return "Unauthorised", 401
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("DELETE FROM users WHERE name=%s", (name,))
                return ("", 204) if acurs.rowcount else ("Invalid", 400)

    async def modify_user(name):
        data = await request.json
        password = data.get("password", "")
        res = await modify_password(name, password)
        return jsonify({"name": name}) if res else ("Invalid", 400)

    @app.route("/pages/name/<string:page_name>/", subdomain=subdomain)
    async def get_page_by_name(page_name):
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT id, name, file_name, rating, rating_ct FROM pages WHERE name = %s",
                    (page_name,),
                )
                return (
                    jsonify(
                        {
                            "page_number": record[0],
                            "name": record[1],
                            "file_name": record[2],
                            "rating": record[3],
                            "rating_ct": record[4],
                        }
                    )
                    if (record := await acurs.fetchone()) is not None
                    else ("Page not found", 404)
                )

    @app.route("/pages/number/<int:page_number>/", subdomain=subdomain)
    async def get_page_by_number(page_number):
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT id, name, file_name, rating, rating_ct FROM pages WHERE id = %s",
                    (page_number,),
                )
                return (
                    jsonify(
                        {
                            "page_number": record[0],
                            "name": record[1],
                            "file_name": record[2],
                            "rating": record[3],
                            "rating_ct": record[4],
                        }
                    )
                    if (record := await acurs.fetchone()) is not None
                    else ("Page not found", 404)
                )

    @app.route("/pages/name/<string:page_name>/link", subdomain=subdomain)
    async def redirect_page_by_name(page_name):
        protocol = "https" if STATIC_IS_HTTPS else "http"
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT file_name FROM pages WHERE name = %s", (page_name,)
                )
                return (
                    redirect(
                        f"{protocol}://{STATIC_SITE_NAME}/astroview/pages/{record[0]}"
                    )
                    if (record := await acurs.fetchone()) is not None
                    else ("Page not found", 404)
                )

    @app.route("/pages/number/<int:page_number>/link", subdomain=subdomain)
    async def redirect_page_by_number(page_number):
        protocol = "https" if STATIC_IS_HTTPS else "http"
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT file_name FROM pages WHERE id = %s", (page_number,)
                )
                return (
                    redirect(
                        f"{protocol}://{STATIC_SITE_NAME}/astroview/pages/{record[0]}"
                    )
                    if (record := await acurs.fetchone()) is not None
                    else ("Page not found", 404)
                )
