import json
import logging

import azure.functions as func

from db import get_connection

bp = func.Blueprint()


@bp.route(route='blog_lists', methods=['GET'])
def blog_lists_get(req: func.HttpRequest) -> func.HttpResponse:
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute('SELECT name, ids FROM blog_lists ORDER BY id ASC')
            rows = cur.fetchall()
        result = [{'name': r['name'], 'ids': r['ids']} for r in rows]
        return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype='application/json')
    except Exception:
        logging.exception('blog_lists_get failed')
        return func.HttpResponse('Internal error', status_code=500)


@bp.route(route='blog_lists', methods=['POST'])
def blog_lists_save(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        name = body['name']
        ids = body['ids']
    except (ValueError, KeyError):
        return func.HttpResponse("Invalid request body: 'name', 'ids' required", status_code=400)

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute('SELECT id FROM blog_lists WHERE name = %s', (name,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    'UPDATE blog_lists SET ids = %s WHERE name = %s',
                    (json.dumps(ids), name),
                )
            else:
                cur.execute(
                    'INSERT INTO blog_lists (name, ids) VALUES (%s, %s)',
                    (name, json.dumps(ids)),
                )
            conn.commit()
        return func.HttpResponse(status_code=204)
    except Exception:
        logging.exception('blog_lists_save failed')
        return func.HttpResponse('Internal error', status_code=500)


@bp.route(route='blog_lists', methods=['DELETE'])
def blog_lists_delete(req: func.HttpRequest) -> func.HttpResponse:
    name = req.params.get('name')
    if not name:
        return func.HttpResponse("Missing 'name' query parameter", status_code=400)

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute('DELETE FROM blog_lists WHERE name = %s', (name,))
            conn.commit()
        return func.HttpResponse(status_code=204)
    except Exception:
        logging.exception('blog_lists_delete failed')
        return func.HttpResponse('Internal error', status_code=500)
