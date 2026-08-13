import os

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    conn_str = os.environ['PG_CONN']
    return psycopg2.connect(conn_str, cursor_factory=RealDictCursor)
