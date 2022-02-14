import base64
import hashlib
from datetime import datetime

import bcrypt
from quart import jsonify, redirect, request

from settings import STATIC_IS_HTTPS, STATIC_SITE_NAME

from .postgresql import get_pool

subdomain = "supervend"
db_name = "supervend"


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
            await acurs.execute("SELECT * FROM users WHERE name=%s", (username,))
            if (result := await acurs.fetchone()) is not None:
                pw_hash = (
                    hashlib.sha512(password.encode("utf-8")).hexdigest().encode("utf-8")
                )
                return (
                    username
                    if bcrypt.checkpw(pw_hash, result[1].encode("utf-8"))
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


async def add_money(name, money):
    try:
        money = int(money)
    except ValueError:
        return "Invalid amount", 400
    if money < 0:
        return "Invalid amount", 400
    async with (await get_pool(db_name)).connection() as conn:
        async with conn.cursor() as acurs:
            await acurs.execute(
                "UPDATE users SET wallet = wallet + %s WHERE name = %s",
                (money, name),
            )
            return str(acurs.rowcount)


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
    @app.route("/products/", subdomain=subdomain)
    async def get_products():
        category = request.args.get("category", default=None)
        result = []
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    """
                    SELECT
                        product_id,
                        name,
                        description,
                        category,
                        preview,
                        price,
                        rating,
                        rating_ct
                    FROM products
                    WHERE category = COALESCE(%s, category)
                    """,
                    (category,),
                )
                async for record in acurs:
                    result.append(
                        {
                            "id": record[0],
                            "name": record[1],
                            "description": record[2],
                            "category": record[3],
                            "preview": record[4],
                            "price": record[5],
                            "ratings": {"rating_total": record[6], "count": record[7]},
                        }
                    )
        return jsonify(result)

    @app.route("/products/<string:product_id>/", subdomain=subdomain)
    async def get_product_by_id(product_id):
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT * FROM products WHERE product_id = %s",
                    (product_id,),
                )
                if acurs.rowcount < 1:
                    return "No such product", 404
                record = await acurs.fetchone()
                return jsonify(
                    {
                        "id": record[0],
                        "name": record[1],
                        "description": record[2],
                        "company": record[3],
                        "price": record[4],
                        "temperature": record[5],
                        "size": record[6],
                        "country": record[7],
                        "expiry": process_date(record[8]),
                        "stock": record[9],
                        "images": record[10],
                        "category": record[11],
                        "preview": record[12],
                        "ratings": {"rating_total": record[13], "count": record[14]},
                    }
                )

    @app.route(
        "/products/<string:product_id>/ratings/",
        subdomain=subdomain,
        methods=["GET", "POST"],
    )
    async def ratings(product_id):
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT * FROM products WHERE product_id = %s",
                    (product_id,),
                )
                if acurs.rowcount < 1:
                    return "No such product", 404
        if request.method == "GET":
            return await get_ratings(product_id)
        elif request.method == "POST":
            return await post_rating(product_id)

    async def get_ratings(product_id):
        results = {"reviews": []}
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT rating, rating_ct FROM products WHERE product_id = %s",
                    (product_id,),
                )
                if acurs.rowcount < 1:
                    return "No such product", 404
                record = await acurs.fetchone()
                results["summary"] = {"rating_total": record[0], "count": record[1]}
                await acurs.execute(
                    "SELECT * FROM ratings WHERE product_id = %s",
                    (product_id,),
                )
                async for record in acurs:
                    results["reviews"].append(
                        {
                            "user": record[0],
                            "rating": record[1],
                            "description": record[2],
                            "time": process_datetime(record[3]),
                            "product_id": record[4],
                        }
                    )

        return jsonify(results)

    async def post_rating(product_id):
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
                    "INSERT INTO ratings VALUES (%s, %s, %s, %s, %s)",
                    (name, rating, desc, time, product_id),
                )
                if acurs.rowcount:
                    await acurs.execute(
                        """
                        UPDATE products
                        SET rating = rating + %s, rating_ct = rating_ct + 1
                        WHERE product_id = %s
                        """,
                        (rating, product_id),
                    )
                    return (
                        jsonify(
                            {
                                "user": name,
                                "rating": rating,
                                "description": desc,
                                "time": process_datetime(time),
                                "product_id": product_id,
                            }
                        )
                        if acurs.rowcount
                        else "Invalid",
                        400,
                    )
                else:
                    return "Invalid", 400

    @app.route(
        "/users/<string:username>/",
        subdomain=subdomain,
        methods=["GET", "PATCH", "POST", "DELETE"],
    )
    async def user_action(username):
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
                await acurs.execute(
                    "SELECT name, wallet FROM users WHERE name=%s", (name,)
                )
                row = await acurs.fetchone()
                return jsonify({"name": row[0], "balance": row[1]})

    async def add_user(name):
        data = await request.json
        password = data.get("password", "")
        if len(name) > 30 or name == "" or password == "":
            return "Invalid", 400
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM users WHERE name=%s", (name,))
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
        return jsonify({"name": name, "balance": 0}) if success else ("Invalid", 400)

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
        if not res:
            return res if res else "0"
        money = data.get("deposit", "0")
        res = await add_money(name, money)
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT wallet FROM users WHERE name=%s", (name,))
                row = await acurs.fetchone()
                return (
                    jsonify({"name": name, "balance": row[0]})
                    if res
                    else ("Invalid", 400)
                )

    @app.route("/users/<string:username>/buy/", subdomain=subdomain, methods=["POST"])
    async def buy_product(username):
        resp = await check_password()
        if resp is None or resp != username:
            return "Unauthorised", 401
        data = await request.json
        total = 0
        orders = []
        for order in data:
            qty = order.get("quantity", 0)
            if not isinstance(qty, int) or qty < 0:
                return "Invalid quantity", 400
            product_id = order.get("product_id", "")
            orders.append((product_id, qty))
            async with (await get_pool(db_name)).connection() as conn:
                async with conn.cursor() as acurs:
                    await acurs.execute(
                        "SELECT price, stock FROM products WHERE product_id = %s",
                        (product_id,),
                    )
                    if acurs.rowcount < 1:
                        return "No such product", 404
                    row = await acurs.fetchone()
                    price, stock = row
                    if stock < qty:
                        return "Not enough stock", 400
                    total += price * qty
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute(
                    "SELECT wallet FROM users WHERE name = %s", (username,)
                )
                wallet = (await acurs.fetchone())[0]
                if total > wallet:
                    return "Not enough money", 400
                await acurs.execute(
                    "UPDATE users SET wallet = wallet - %s WHERE name = %s",
                    (total, username),
                )
        for product_id, qty in orders:
            async with (await get_pool(db_name)).connection() as conn:
                async with conn.cursor() as acurs:
                    await acurs.execute(
                        "UPDATE products SET stock = stock - %s WHERE product_id = %s",
                        (qty, product_id),
                    )
        receipt = {"total": total, "balance": wallet - total, "order": data}
        return jsonify(receipt)

    @app.route("/categories/", subdomain=subdomain)
    async def get_categories():
        result = []
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM categories")
                async for record in acurs:
                    result.append({"short_name": record[0], "full_name": record[1]})
        return jsonify(result)

    @app.route("/images/<string:image_name>/", subdomain=subdomain)
    async def redir_image(image_name):
        protocol = "https" if STATIC_IS_HTTPS else "http"
        return redirect(
            f"{protocol}://{STATIC_SITE_NAME}/supervend/images/{image_name}"
        )
