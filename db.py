import os
import re
from typing import Any, Dict, List, Optional, Tuple
import mysql.connector
from mysql.connector import pooling


db_config = {
    "pool_name": "mypool",
    "pool_size": 5,
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
    "ssl_ca": os.getenv("MYSQL_SSL_CA", "/etc/ssl/certs/ca-certificates.crt"),
    "ssl_verify_cert": True
}


def _sanitize_identifier(identifier: str) -> str:
    if not identifier:
        raise ValueError("Empty identifier is not allowed")
    if not re.fullmatch(r"[A-Za-z0-9_]+", identifier):
        raise ValueError("Identifier contains invalid characters")
    return identifier


def _quote_identifier(identifier: str) -> str:
    safe = _sanitize_identifier(identifier)
    return f"`{safe}`"


def get_connection() -> mysql.connector.connection.MySQLConnection:
    db_name = os.getenv("MYSQL_DATABASE") or "StationeryDB"

    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "22bce0449"),
    )

    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {_quote_identifier(db_name)}")
    cursor.execute(f"USE {_quote_identifier(db_name)}")
    connection.commit()
    return connection


def ensure_table(connection: mysql.connector.connection.MySQLConnection, table_name: str) -> None:
    cursor = connection.cursor()
    t = _quote_identifier(table_name)
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {t} (
            SNo INT PRIMARY KEY,
            ItemName VARCHAR(20) NOT NULL,
            NameOfDealer VARCHAR(20) NOT NULL,
            CostPrice FLOAT,
            SellingPrice FLOAT,
            Profit FLOAT,
            Loss FLOAT,
            GST FLOAT,
            StockBought INT,
            StockSold INT,
            StockRemaining INT,
            DateOfPurchase DATE
        )
        """
    )
    connection.commit()


def fetch_all_items(connection: mysql.connector.connection.MySQLConnection, table_name: str) -> List[Dict[str, Any]]:
    cursor = connection.cursor(dictionary=True)
    t = _quote_identifier(table_name)
    cursor.execute(f"SELECT * FROM {t}")
    records = cursor.fetchall() or []
    return records


ALLOWED_COLUMNS = [
    "SNo",
    "ItemName",
    "NameOfDealer",
    "CostPrice",
    "SellingPrice",
    "Profit",
    "Loss",
    "GST",
    "StockBought",
    "StockSold",
    "StockRemaining",
    "DateOfPurchase",
]


def fetch_items_paginated(
    connection: mysql.connector.connection.MySQLConnection,
    table_name: str,
    search: Optional[str],
    sort_by: str,
    sort_dir: str,
    page: int,
    per_page: int,
) -> Tuple[List[Dict[str, Any]], int]:
    t = _quote_identifier(table_name)
    # Whitelist sorting
    sort_col = sort_by if sort_by in ALLOWED_COLUMNS else "SNo"
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    order_sql = f"ORDER BY `{sort_col}` {direction}"

    where_sql = ""
    params: List[Any] = []
    if search:
        where_sql = "WHERE (ItemName LIKE %s OR NameOfDealer LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like])

    offset = max(page - 1, 0) * max(per_page, 1)

    # Count total
    count_sql = f"SELECT COUNT(*) AS cnt FROM {t} {where_sql}"
    c = connection.cursor(dictionary=True)
    c.execute(count_sql, params)
    total = int((c.fetchone() or {"cnt": 0})["cnt"])

    # Fetch page
    list_sql = f"SELECT * FROM {t} {where_sql} {order_sql} LIMIT %s OFFSET %s"
    list_params = list(params)
    list_params.extend([per_page, offset])
    cur = connection.cursor(dictionary=True)
    cur.execute(list_sql, list_params)
    rows = cur.fetchall() or []
    return rows, total


def insert_item(connection: mysql.connector.connection.MySQLConnection, table_name: str, item: Dict[str, Any]) -> None:
    t = _quote_identifier(table_name)
    sql = (
        f"INSERT INTO {t} (SNo, ItemName, NameOfDealer, CostPrice, SellingPrice, Profit, Loss, GST, StockBought, StockSold, StockRemaining, DateOfPurchase) "
        "VALUES (%(SNo)s, %(ItemName)s, %(NameOfDealer)s, %(CostPrice)s, %(SellingPrice)s, %(Profit)s, %(Loss)s, %(GST)s, %(StockBought)s, %(StockSold)s, %(StockRemaining)s, %(DateOfPurchase)s)"
    )
    cursor = connection.cursor()
    cursor.execute(sql, item)
    connection.commit()


def fetch_item(connection: mysql.connector.connection.MySQLConnection, table_name: str, sno: int) -> Optional[Dict[str, Any]]:
    cursor = connection.cursor(dictionary=True)
    t = _quote_identifier(table_name)
    cursor.execute(f"SELECT * FROM {t} WHERE SNo = %s", (sno,))
    return cursor.fetchone()


def fetch_item_by_name(connection: mysql.connector.connection.MySQLConnection, table_name: str, name: str) -> Optional[Dict[str, Any]]:
    cursor = connection.cursor(dictionary=True)
    t = _quote_identifier(table_name)
    cursor.execute(f"SELECT * FROM {t} WHERE ItemName = %s LIMIT 1", (name,))
    return cursor.fetchone()


def fetch_item_by_name_and_dealer(
    connection: mysql.connector.connection.MySQLConnection,
    table_name: str,
    name: str,
    dealer: str,
) -> Optional[Dict[str, Any]]:
    cursor = connection.cursor(dictionary=True)
    t = _quote_identifier(table_name)
    cursor.execute(
        f"SELECT * FROM {t} WHERE ItemName = %s AND NameOfDealer = %s LIMIT 1",
        (name, dealer),
    )
    return cursor.fetchone()


def get_next_sno(connection: mysql.connector.connection.MySQLConnection, table_name: str) -> int:
    t = _quote_identifier(table_name)
    cursor = connection.cursor()
    cursor.execute(f"SELECT COALESCE(MAX(SNo), 0) + 1 AS next FROM {t}")
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 1


def update_item(connection: mysql.connector.connection.MySQLConnection, table_name: str, sno: int, item: Dict[str, Any]) -> None:
    t = _quote_identifier(table_name)
    sql = (
        f"UPDATE {t} SET ItemName=%(ItemName)s, NameOfDealer=%(NameOfDealer)s, CostPrice=%(CostPrice)s, SellingPrice=%(SellingPrice)s, Profit=%(Profit)s, Loss=%(Loss)s, GST=%(GST)s, StockBought=%(StockBought)s, StockSold=%(StockSold)s, StockRemaining=%(StockRemaining)s, DateOfPurchase=%(DateOfPurchase)s WHERE SNo=%(SNo)s"
    )
    data = dict(item)
    data["SNo"] = sno
    cursor = connection.cursor()
    cursor.execute(sql, data)
    connection.commit()


def delete_item(connection: mysql.connector.connection.MySQLConnection, table_name: str, sno: int) -> None:
    cursor = connection.cursor()
    t = _quote_identifier(table_name)
    cursor.execute(f"DELETE FROM {t} WHERE SNo=%s", (sno,))
    connection.commit()


def sell_item(
    connection: mysql.connector.connection.MySQLConnection,
    table_name: str,
    sno: int,
    quantity: int,
) -> Dict[str, Any]:
    """Decrease remaining stock by quantity, increase sold; return updated item.
    Raises ValueError if insufficient stock.
    """
    item = fetch_item(connection, table_name, sno)
    if not item:
        raise ValueError("Item not found")
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    remaining_before = int(item["StockRemaining"]) if item["StockRemaining"] is not None else 0
    if quantity > remaining_before:
        raise ValueError("Insufficient stock")
    new_sold = int(item["StockSold"]) + quantity
    new_remaining = remaining_before - quantity
    t = _quote_identifier(table_name)
    cur = connection.cursor()
    cur.execute(
        f"UPDATE {t} SET StockSold=%s, StockRemaining=%s WHERE SNo=%s",
        (new_sold, new_remaining, sno),
    )
    connection.commit()
    updated = fetch_item(connection, table_name, sno) or item
    return updated


