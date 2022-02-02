from .postgresql import get_pool
from quart import jsonify, request, redirect
from datetime import datetime
from settings import STATIC_IS_HTTPS, STATIC_SITE_NAME
import bcrypt
import hashlib

subdomain = "supervend"
db_name = "supervend"

async def check_password(name):
    password = request.headers.get("Password", default="")
    if (len(name) > 30 or name == ""): return None
    if (password == ""): return False
    async with (await get_pool(db_name)).connection() as conn:
        async with conn.cursor() as acurs:
            await acurs.execute("SELECT * FROM users WHERE name=%s", (name,))
            if (result := await acurs.fetchone()) != None:
                pw_hash = hashlib.sha512(password.encode('utf-8')).hexdigest().encode('utf-8')
                return bcrypt.checkpw(pw_hash, result[1].encode('utf-8'))
            return None

async def modify_password(name, password):
    resp = await check_password(name)
    if resp == False: 
        print(resp)
        return ("Unauthorised", 401)
    elif resp == None: 
        return ("No such user", 404)
    if (password == ""): return True
    async with (await get_pool(db_name)).connection() as conn:
        async with conn.cursor() as acurs:
            pw_hash = hashlib.sha512(password.encode('utf-8')).hexdigest().encode('utf-8')
            pw_salt_hash = bcrypt.hashpw(pw_hash, bcrypt.gensalt()).decode('utf-8')
            await acurs.execute("UPDATE users SET hash = %s WHERE name = %s", (pw_salt_hash, name))
            success = acurs.rowcount
    return bool(success)

async def add_money(name, money):
    try:
        money = int(money)
    except ValueError:
        return ("Invalid amount", 400)
    if (money < 0): return ("Invalid amount", 400)
    async with (await get_pool(db_name)).connection() as conn:
        async with conn.cursor() as acurs:
            await acurs.execute("UPDATE users SET wallet = wallet + %s WHERE name = %s", (money, name))
            return str(acurs.rowcount)

def process_datetime(to_process):
    time = process_time(to_process)
    date = process_date(to_process)
    return {"time": time, "date": date}

def process_date(to_process):
    return {'day': to_process.day, 'month':to_process.month, 'year':to_process.year}

def process_time(to_process):
    return {'hour':to_process.hour, 'minute':to_process.minute, 'second':to_process.second}

def init(app):
    @app.route('/products/', subdomain = subdomain)
    async def get_products():
        result = []
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM products")
                async for record in acurs:
                    result.append({"id": record[0], "name": record[1], "description": record[2]})
        return jsonify({"products": result})

    @app.route('/products/<string:product_id>/', subdomain = subdomain, methods = ["GET", "POST"])
    async def product_api(product_id):
        if request.method == "GET":
            return await get_product_by_id(product_id)
        elif request.method == "POST":
            return await buy_product(product_id)

    async def get_product_by_id(product_id):
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
                if (acurs.rowcount < 1): return ("No such product", 404)
                record = await acurs.fetchone()
                dict_record = {}
                dict_record["id"] = record[0]
                dict_record["name"] = record[1]
                dict_record["description"] = record[2]
                dict_record["company"] = record[3]
                dict_record["price"] = record[4]
                dict_record["temp"] = record[5]
                dict_record["size"] = record[6]
                dict_record["country"] = record[7]
                dict_record["expiry"] = process_date(record[8])
                dict_record["stock"] = record[9]
                dict_record["images"] = record[10]
        return jsonify(dict_record)

    async def buy_product(product_id):
        try:
            qty = int(request.args.get("quantity", default="0"))
        except ValueError:
            return ("Invalid quantity", 400)
        if (qty < 0): return ("Invalid quantity", 400)
        name = request.args.get("username", default="")
        resp = await check_password(name)
        if resp == False: 
            return ("Unauthorised", 401)
        elif resp == None: 
            return ("No such user", 404)
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT price, stock FROM products WHERE product_id = %s", (product_id,))
                if (acurs.rowcount < 1): return ("No such product", 404)
                row = await acurs.fetchone()
                price, stock = row
                if stock < qty: return ("Not enough stock", 400)
                await acurs.execute("SELECT wallet FROM users WHERE name = %s", (name,))
                wallet = (await acurs.fetchone())[0]
                if price * qty > wallet: return ("Not enough money", 400)
                await acurs.execute("UPDATE users SET wallet = wallet - %s WHERE name = %s", (price * qty, name))
                await acurs.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (qty, product_id))
        return '1'


    @app.route('/products/<string:product_id>/ratings/', subdomain = subdomain, methods=["GET", "POST"])
    async def ratings(product_id):
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
                if (acurs.rowcount < 1): return ("No such product", 404)
        if request.method == "GET":
            return await get_ratings(product_id)
        elif request.method == "POST":
            return await post_rating(product_id)

    async def get_ratings(product_id):
        results = []
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM ratings WHERE product_id = %s", (product_id,))
                async for record in acurs:
                    dict_record = {}
                    dict_record["user"] = record[0]
                    dict_record["rating"] = record[1]
                    dict_record["description"] = record[2]
                    dict_record["time"] = process_datetime(record[3])
                    dict_record["product_id"] = record[4]
                    results.append(dict_record)
        return jsonify({"ratings": results})

    async def post_rating(product_id):
        name = request.args.get("username", default="")
        desc = request.args.get("description", default="")
        rating = request.args.get("rating", default="")
        if (desc == "" or name == "" or rating == ""): return ("Invalid", 400)
        try:
            rating = int(rating)
        except ValueError:
            return ("Invalid", 400)
        resp = await check_password(name)
        if resp == False: 
            return ("Unauthorised", 401)
        elif resp == None: 
            return ("No such user", 404)
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("INSERT INTO ratings VALUES (%s, %s, %s, %s, %s)", 
                    (name, rating, desc, datetime.now(), product_id))
                return str(acurs.rowcount)


    @app.route('/users/<string:username>/', subdomain = subdomain, methods=["GET", "PUT", "POST", "DELETE"])
    async def user_action(username):
        username = username.strip()
        if request.method == "GET":
            return await check_user(username)
        elif request.method == "POST":
            return await add_user(username)
        elif request.method == "DELETE":
            return await delete_user(username)
        elif request.method == "PUT":
            return await modify_user(username)

    async def check_user(name):
        resp = await check_password(name)
        if resp == False: 
            return ("Unauthorised", 401)
        elif resp == None: 
            return ("No such user", 404)
        return str(int(resp))

    async def add_user(name):
        password = request.headers.get("Password", default="")
        if (len(name) > 30 or name == "" or password == ""): return ("Invalid", 400)
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM users WHERE name=%s", (name,))
                if acurs.rowcount > 0:
                    return ("User already exists", 400)
                pw_hash = hashlib.sha512(password.encode('utf-8')).hexdigest().encode('utf-8')
                pw_salt_hash = bcrypt.hashpw(pw_hash, bcrypt.gensalt()).decode('utf-8')
                await acurs.execute("INSERT INTO users VALUES (%s, %s)", (name, pw_salt_hash))
                success = acurs.rowcount
        return str(success)

    async def delete_user(name):
        resp = await check_password(name)
        if resp == False: 
            return ("Unauthorised", 401)
        elif resp == None: 
            return ("No such user", 404)
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("DELETE FROM users WHERE name=%s", (name,))
                return str(acurs.rowcount)

    async def modify_user(name):
        password = request.headers.get("New-Password", default="")
        res = await modify_password(name, password)
        print(type(res))
        if (res != True): return (res if res != False else '0')
        money = request.args.get("money", default="0")
        res = await add_money(name, money)
        return res

    @app.route('/categories/', subdomain = subdomain)
    async def get_categories():
        result = []
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM categories")
                async for record in acurs:
                    result.append({"short_name": record[0], "full_name": record[1]})
        return jsonify(result)

    @app.route('/images/<string:image_name>/', subdomain = subdomain)
    async def redir_image(image_name):
        protocol = 'https' if STATIC_IS_HTTPS else 'http'
        return redirect(f'{protocol}://{STATIC_SITE_NAME}/supervend/images/{image_name}')