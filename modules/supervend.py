from .postgresql import get_pool
from quart import jsonify
from datetime import datetime

subdomain = "supervend"
pool = None

def init(app):
    @app.route('/get-products', subdomain = subdomain)
    async def get_products():
        global pool
        result = []
        if pool == None:
            pool = await get_pool("supervend")
        async with pool.connection() as conn:
            async with conn.cursor() as acurs:
                await acurs.execute("SELECT * FROM products")
                async for record in acurs:
                    dict_record = {}
                    dict_record["product_id"] = record[0]
                    dict_record["name"] = record[1]
                    dict_record["desc"] = record[2]
                    dict_record["company"] = record[3]
                    dict_record["price"] = record[4]
                    dict_record["temp"] = record[5]
                    dict_record["size"] = record[6]
                    dict_record["country"] = record[7]
                    dict_record["expiry"] = [record[8].day, record[8].month, record[8].year]
                    dict_record["stock"] = record[9]
                    dict_record["images"] = record[10]
                    result.append(dict_record)
        return jsonify(result)

