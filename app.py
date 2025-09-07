from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from db import get_connection, ensure_table, fetch_all_items, insert_item, fetch_item, update_item, delete_item, fetch_items_paginated, sell_item, fetch_item_by_name, get_next_sno, fetch_item_by_name_and_dealer


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "dev-secret-key"

    @app.route("/")
    def index():
        return redirect(url_for("items"))

    # Placeholder routes; will be implemented after db module extraction
    @app.route("/items")
    def items():
        table_name = request.args.get("table", "Stationery")
        q = request.args.get("q")
        sort_by = request.args.get("sort", "SNo")
        sort_dir = request.args.get("dir", "asc")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per", 10))
        connection = get_connection()
        ensure_table(connection, table_name)
        items, total = fetch_items_paginated(connection, table_name, q, sort_by, sort_dir, page, per_page)
        return render_template(
            "items/list.html",
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            q=q or "",
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    @app.route("/items/new", methods=["GET", "POST"])
    def item_new():
        table_name = request.args.get("table", "Stationery")
        if request.method == "POST":
            form = request.form
            cost = float(form.get("CostPrice", 0))
            sell = float(form.get("SellingPrice", 0))
            profit = max(sell - cost, 0)
            loss = max(cost - sell, 0)
            gst = sell * 0.18
            bought = int(form.get("StockBought", 0))
            sold = int(form.get("StockSold", 0))
            remaining = bought - sold
            sno = form.get("SNo")
            if not sno:
                connection = get_connection()
                ensure_table(connection, table_name)
                sno = get_next_sno(connection, table_name)
            item = {
                "SNo": int(sno),
                "ItemName": form["ItemName"],
                "NameOfDealer": form["NameOfDealer"],
                "CostPrice": cost,
                "SellingPrice": sell,
                "Profit": profit,
                "Loss": loss,
                "GST": gst,
                "StockBought": bought,
                "StockSold": sold,
                "StockRemaining": remaining,
                "DateOfPurchase": form.get("DateOfPurchase"),
            }
            connection = get_connection()
            ensure_table(connection, table_name)
            try:
                insert_item(connection, table_name, item)
            except Exception as e:
                flash(f"Could not add item: {e}", "danger")
                # Re-render with previous values
                return render_template("items/form.html", item=item)
            flash("Item added successfully", "success")
            return redirect(url_for("items", table=table_name))
        # GET - prefill SNo suggestion
        connection = get_connection()
        ensure_table(connection, table_name)
        suggested = get_next_sno(connection, table_name)
        return render_template("items/form.html", item={"SNo": suggested})

    @app.route("/items/<int:sno>/edit", methods=["GET", "POST"])
    def item_edit(sno: int):
        table_name = request.args.get("table", "Stationery")
        connection = get_connection()
        ensure_table(connection, table_name)
        existing = fetch_item(connection, table_name, sno)
        if not existing:
            flash("Item not found")
            return redirect(url_for("items", table=table_name))
        if request.method == "POST":
            form = request.form
            cost = float(form.get("CostPrice", existing["CostPrice"]))
            sell = float(form.get("SellingPrice", existing["SellingPrice"]))
            profit = max(sell - cost, 0)
            loss = max(cost - sell, 0)
            gst = sell * 0.18
            bought = int(form.get("StockBought", existing["StockBought"]))
            sold = int(form.get("StockSold", existing["StockSold"]))
            remaining = bought - sold
            item = {
                "ItemName": form.get("ItemName", existing["ItemName"]),
                "NameOfDealer": form.get("NameOfDealer", existing["NameOfDealer"]),
                "CostPrice": cost,
                "SellingPrice": sell,
                "Profit": profit,
                "Loss": loss,
                "GST": gst,
                "StockBought": bought,
                "StockSold": sold,
                "StockRemaining": remaining,
                "DateOfPurchase": form.get("DateOfPurchase", existing["DateOfPurchase"]),
            }
            try:
                update_item(connection, table_name, sno, item)
            except Exception as e:
                flash(f"Could not update item: {e}", "danger")
                merged = dict(existing)
                merged.update(item)
                return render_template("items/form.html", item=merged)
            flash("Item updated", "success")
            return redirect(url_for("items", table=table_name))
        return render_template("items/form.html", item=existing)

    @app.route("/items/<int:sno>/delete", methods=["POST"])
    def item_delete(sno: int):
        table_name = request.args.get("table", "Stationery")
        connection = get_connection()
        ensure_table(connection, table_name)
        try:
            delete_item(connection, table_name, sno)
        except Exception as e:
            flash(f"Could not delete: {e}", "danger")
            return redirect(url_for("items", table=table_name))
        flash("Item deleted", "success")
        return redirect(url_for("items", table=table_name))

    @app.route("/bills")
    def bill_all():
        table_name = request.args.get("table", "Stationery")
        connection = get_connection()
        ensure_table(connection, table_name)
        items = fetch_all_items(connection, table_name)
        import datetime as _dt
        now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return render_template("bills/all.html", items=items, now=now)

    @app.route("/bills/<int:sno>")
    def bill_single(sno: int):
        table_name = request.args.get("table", "Stationery")
        connection = get_connection()
        ensure_table(connection, table_name)
        item = fetch_item(connection, table_name, sno)
        import datetime as _dt
        now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return render_template("bills/single.html", item=item, now=now)

    @app.route("/sell", methods=["GET", "POST"])
    def sell():
        table_name = request.args.get("table", "Stationery")
        if request.method == "POST":
            # Accept both form and JSON
            is_json = request.is_json or 'application/json' in (request.headers.get('Accept',''))
            payload = request.get_json(silent=True) if is_json else request.form
            name = (payload.get("ItemName", "") or "").strip()
            dealer = (payload.get("NameOfDealer", "") or "").strip()
            qty_str = payload.get("Quantity", "0")
            try:
                qty = int(qty_str)
            except Exception:
                qty = -1
            connection = get_connection()
            ensure_table(connection, table_name)
            item = None
            # Priority: name + dealer, then name only
            if name and dealer:
                item = fetch_item_by_name_and_dealer(connection, table_name, name, dealer)
            if not item and name:
                item = fetch_item_by_name(connection, table_name, name)
            if not item:
                if is_json:
                    return jsonify({"ok": False, "error": "Item not found"}), 400
                flash("Item not found", "danger")
                return render_template("bills/sell.html", receipt=None)
            try:
                updated = sell_item(connection, table_name, int(item["SNo"]), qty)
            except Exception as e:
                if is_json:
                    return jsonify({"ok": False, "error": str(e)}), 400
                flash(str(e), "danger")
                return render_template("bills/sell.html", receipt=None)
            # Build receipt context
            import datetime as _dt
            now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total = float(item["SellingPrice"]) * qty
            receipt = {
                "name": item["ItemName"],
                "sno": int(item["SNo"]),
                "qty": qty,
                "unit_price": float(item["SellingPrice"]),
                "total": total,
                "time": now,
                "remaining": int(updated.get("StockRemaining", 0)),
            }
            if is_json:
                return jsonify({"ok": True, "receipt": receipt})
            flash("Sale recorded", "success")
            return render_template("bills/sell.html", receipt=receipt)
        return render_template("bills/sell.html", receipt=None)

    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(debug=True)


