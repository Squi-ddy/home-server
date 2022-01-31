from .postgresql import get_pool
from quart import jsonify, request
from datetime import datetime
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

    @app.route('/products/<product_id>/', subdomain = subdomain)
    async def get_product_by_id(product_id):
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM products WHERE product_id = %s", (str(product_id),))
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
                dict_record["expiry"] = [record[8].day, record[8].month, record[8].year]
                dict_record["stock"] = record[9]
                dict_record["images"] = record[10]
        return jsonify(dict_record)

    @app.route('/users/<username>/', subdomain = subdomain, methods=["GET", "PUT", "POST", "DELETE"])
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
        if (password == ""): return ("Invalid", 400)
        resp = await check_password(name)
        if resp == False: 
            return ("Unauthorised", 401)
        elif resp == None: 
            return ("No such user", 404)
        async with (await get_pool(db_name)).connection() as conn:
            async with conn.cursor() as acurs:
                pw_hash = hashlib.sha512(password.encode('utf-8')).hexdigest().encode('utf-8')
                pw_salt_hash = bcrypt.hashpw(pw_hash, bcrypt.gensalt()).decode('utf-8')
                await acurs.execute("UPDATE users SET hash = %s WHERE name = %s", (pw_salt_hash, name))
                success = acurs.rowcount
        return str(success)
