import json
import logging

import azure.functions as func

from db import get_connection

bp = func.Blueprint()


@bp.route(route='keyword_corrections', methods=['POST'])
def keyword_corrections_save(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        post_title = body['post_title']
        grade = body['grade']
        keyword = body['keyword']
    except (ValueError, KeyError):
        return func.HttpResponse(
            "Invalid request body: 'post_title', 'grade', 'keyword' required", status_code=400
        )

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                'INSERT INTO keyword_corrections (post_title, grade, keyword) VALUES (%s, %s, %s)',
                (post_title, grade, keyword),
            )
            conn.commit()
        return func.HttpResponse(status_code=204)
    except Exception:
        logging.exception('keyword_corrections_save failed')
        return func.HttpResponse('Internal error', status_code=500)


@bp.route(route='keyword_corrections/fetch', methods=['POST'])
def keyword_corrections_fetch(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        titles = body['titles']
        grade = body['grade']
    except (ValueError, KeyError):
        return func.HttpResponse("Invalid request body: 'titles', 'grade' required", status_code=400)

    if not titles:
        return func.HttpResponse(json.dumps({}), mimetype='application/json')

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                '''
                SELECT post_title, keyword
                FROM keyword_corrections
                WHERE grade = %s AND post_title = ANY(%s)
                ORDER BY id DESC
                ''',
                (grade, titles),
            )
            rows = cur.fetchall()
        result = {}
        for row in rows:
            result.setdefault(row['post_title'], row['keyword'])  # id.desc 순이므로 첫 항목이 최신
        return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype='application/json')
    except Exception:
        logging.exception('keyword_corrections_fetch failed')
        return func.HttpResponse('Internal error', status_code=500)
