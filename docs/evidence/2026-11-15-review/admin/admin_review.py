"""Stage E, real HTTP/SQL review. Import only; run(r) after A-D is complete.

No product-source edits, concurrency, fault injection, seed-file edits, or claims
of a human signature. This script intentionally leaves its independent HTTP
fixtures in the isolated review database for later consistency checks.
"""
import datetime
from html.parser import HTMLParser
from urllib.parse import quote, urlencode
import requests


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.rows.append((tag, dict(attrs)))


def run(r):
    r.begin("E")

    def fresh():
        session = requests.Session()
        session.trust_env = False
        return session

    def get(path, expected=200, label="", session=None, base="a"):
        return r.req(session or r.a, base, "GET", path, expected=expected, label="E " + label)

    def post(path, data=None, expected=303, label="", zero=False, session=None, base="a", csrf=True):
        return r.req(session or r.a, base, "POST", path, data=data or {}, expected=expected,
                     label="E " + label, zero=zero, csrf=csrf)

    def one(query):
        rows = r.sql(query)
        return rows[0] if rows else {}

    def product(pid):
        return one(f"SELECT id,sku,category_id,name,price,stock,status,version,cover_image,summary,description,sort_order FROM product WHERE id={int(pid)}")

    def edit_data(p):
        return {"categoryId": p["category_id"], "name": p["name"], "price": p["price"],
                "summary": p.get("summary", ""), "description": p.get("description", ""),
                "coverImage": p["cover_image"], "sortOrder": p["sort_order"], "version": p["version"]}

    def eq(name, actual, expected):
        r.check("E " + name, actual == expected, {"actual": actual, "expected": expected})

    def attrs(response, name):
        return [d[name] for _, d in Tags(response.text).rows if name in d]

    def count(response, attr):
        values = attrs(response, attr)
        return int(values[0]) if values else None

    def dashboard(label, cards=False):
        expected = one("SELECT (SELECT COUNT(*) FROM product WHERE status='ON_SALE') AS on_sale,"
                       "(SELECT COUNT(*) FROM product WHERE status='DRAFT') AS draft,"
                       "(SELECT COUNT(*) FROM sales_order WHERE status='PAID') AS paid,"
                       "(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='ENABLED') AS enabled,"
                       "(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='DISABLED') AS disabled")
        page = get("/", label="A02 " + label)
        for key, attr in [("on_sale", "data-on-sale-count"), ("draft", "data-draft-count"),
                          ("paid", "data-paid-order-count"), ("enabled", "data-enabled-customer-count"),
                          ("disabled", "data-disabled-customer-count")]:
            eq(label + " dashboard " + key, count(page, attr), int(expected[key]))
        if cards:
            card_map = {"on-sale-products": ("on_sale", "data-product-count", "/products?status=ON_SALE"),
                        "draft-products": ("draft", "data-product-count", "/products?status=DRAFT"),
                        "paid-orders": ("paid", "data-order-count", "/orders?status=PAID"),
                        "enabled-customers": ("enabled", "data-customer-count", "/customers?status=ENABLED"),
                        "disabled-customers": ("disabled", "data-customer-count", "/customers?status=DISABLED")}
            links = {d["data-dashboard-card"]: d.get("href") for tag, d in Tags(page.text).rows
                     if tag == "a" and "data-dashboard-card" in d}
            for card, (key, total, expected_path) in card_map.items():
                eq("dashboard card target " + card, links.get(card), expected_path)
                if links.get(card):
                    filtered = get(links[card], label="dashboard card " + card)
                    eq("dashboard filtered count " + card, count(filtered, total), int(expected[key]))
        return page

    def order_number(key):
        value = r.state.get(key)
        if isinstance(value, dict):
            value = value.get("order_no") or value.get("orderNo")
        r.check("E " + key + " prerequisite from A-D", isinstance(value, str) and bool(value),
                "No fallback seed order is substituted for a missing new-order prerequisite.")
        return value if isinstance(value, str) else None

    def order(no):
        safe = no.replace("'", "''")
        return one("SELECT id,order_no,user_id,status,total_amount,payment_method,payment_no,"
                   "DATE_FORMAT(paid_at,'%Y-%m-%d %H:%i:%s.%f') AS paid_at,"
                   "DATE_FORMAT(shipped_at,'%Y-%m-%d %H:%i:%s.%f') AS shipped_at,"
                   "DATE_FORMAT(cancelled_at,'%Y-%m-%d %H:%i:%s.%f') AS cancelled_at "
                   f"FROM sales_order WHERE order_no='{safe}'")

    def nonnull(value):
        return value is not None and str(value).lower() not in ("", "null", "none", "\\n")

    # A01 / A02 and navigation: fresh public login page, then independent SQL counts.
    login = get("/login", label="A01 public login", session=fresh())
    eq("A01 page", attrs(login, "data-page-id"), ["A01"])
    dashboard("baseline", cards=True)
    for path, pageid in [("/categories", "A03"), ("/products", "A04"), ("/products/new", "A05"),
                         ("/orders", "A06"), ("/customers", "A08"), ("/customers/1", "A09")]:
        page = get(path, label=pageid + " core read")
        eq(pageid + " page marker", attrs(page, "data-page-id"), [pageid])

    # A03: independent categories, generated IDs, edit, referenced removal, empty removal.
    suffix = datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S%f")
    code = "RV" + suffix
    root_name = "复核主题" + suffix
    post("/categories", {"code": code, "name": root_name, "sortOrder": "901"}, label="A03 create root")
    root = one(f"SELECT id,code,parent_id,name,sort_order FROM category WHERE code='{code}'")
    r.check("E category generated id exists", bool(root) and int(root.get("id", 0)) > 0, root)
    if not root:
        r.finish("E", notes=["分类新增前置失败；后续独立商品/相册/分类写未执行。", "A-D前置保留，不使用旧证据补充。"])
        return
    root_id = int(root["id"])
    get(f"/categories/{root_id}/edit", label="A03 edit form")
    post(f"/categories/{root_id}", {"name": root_name + "改", "sortOrder": "902", "code": "IGNORED"}, label="A03 edit root")
    changed_root = one(f"SELECT id,code,parent_id,name,sort_order FROM category WHERE id={root_id}")
    eq("category edit preserves code", changed_root.get("code"), code)
    eq("category edit name", changed_root.get("name"), root_name + "改")
    post("/categories", {"parentId": str(root_id), "type": "STATIONERY", "name": "复核文具" + suffix,
                         "sortOrder": "0"}, label="A03 create child")
    child = one(f"SELECT id,code,parent_id FROM category WHERE code='{code}_STATIONERY'")
    r.check("E child generated id / parent / suffix", bool(child) and int(child.get("parent_id",0)) == root_id,
            child)
    post(f"/categories/{root_id}/remove", expected=409, zero=True, label="A03 referenced parent removal")
    post("/categories", {"code": "X" * 22, "name": "超长分类拒绝" + suffix, "sortOrder": "0"},
         expected=400, zero=True, label="A03 code22 rejected")
    empty_code = "EM" + suffix
    post("/categories", {"code": empty_code, "name": "空类目" + suffix, "sortOrder": "0"}, label="A03 create empty root")
    empty = one(f"SELECT id FROM category WHERE code='{empty_code}'")
    if empty:
        post(f"/categories/{int(empty['id'])}/remove", label="A03 remove empty root")
        eq("empty category deleted", r.sql(f"SELECT id FROM category WHERE code='{empty_code}'"), [])
    if not child:
        r.finish("E", notes=["二级分类新增前置失败；后续商品和相册写未执行。"])
        return
    cid = int(child["id"])

    # A04 / A05: writes target a new SKU, never the mainline seed stock.
    sku = "REVIEW-20261115-" + suffix
    create = {"sku": sku, "categoryId": str(cid), "name": "复核商品" + suffix, "price": "7.25",
              "stock": "4", "sortOrder": "900", "summary": "独立复核夹具", "description": "纯文本说明",
              "coverImage": "images/catalog-placeholder.svg"}
    post("/products", create, label="A05 create draft SKU")
    created = one(f"SELECT id FROM product WHERE sku='{sku}'")
    r.check("E product generated id exists", bool(created), created)
    if not created:
        r.finish("E", notes=["独立商品新增失败，相关后续抽查未执行。"])
        return
    pid = int(created["id"])
    r.state["admin_fixture_product"] = pid
    r.state["admin_fixture_category"] = {"root": root_id, "child": cid}
    p0 = product(pid)
    eq("new product initial state", (p0["status"], int(p0["version"]), int(p0["stock"])), ("DRAFT", 0, 4))
    get(f"/products/{pid}", expected=404, session=fresh(), base="u", label="draft not public")
    form = get(f"/products/{pid}/edit", label="A05 edit form")
    eq("A05 edit page marker", attrs(form, "data-page-id"), ["A05"])
    edit = edit_data(p0)
    edit.update({"name": "复核商品编辑" + suffix, "price": "8.50", "stock": "999", "sku": "TAMPERED",
                 "description": "<script>reviewTextOnly</script>"})
    post(f"/products/{pid}", edit, label="A05 edit ignores SKU and stock")
    p1 = product(pid)
    eq("edit SKU stock retained", (p1["sku"], int(p1["stock"])), (sku, 4))
    eq("edit increments product version", int(p1["version"]), 1)
    post(f"/products/{pid}", edit, expected=409, zero=True, label="A05 old edit 409")
    post(f"/products/{pid}/publish", {"version": p1["version"]}, label="A04 publish")
    p2 = product(pid)
    eq("publish status/version", (p2["status"], int(p2["version"])), ("ON_SALE", 2))
    public = get(f"/products/{pid}", session=fresh(), base="u", label="published public and escaped text")
    r.check("E description escaped in user HTML", "&lt;script&gt;reviewTextOnly&lt;/script&gt;" in public.text
            and "<script>reviewTextOnly</script>" not in public.text)
    post(f"/products/{pid}/publish", {"version": p2["version"]}, expected=409, zero=True, label="A04 repeated state 409")
    dashboard("after publish")
    post(f"/products/{pid}/unpublish", {"version": p2["version"]}, label="A04 unpublish")
    p3 = product(pid)
    eq("unpublish status/version", (p3["status"], int(p3["version"])), ("DRAFT", 3))
    get(f"/products/{pid}", expected=404, session=fresh(), base="u", label="unpublished public 404")
    old_edit = edit_data(p3)
    post(f"/products/{pid}/restock", {"quantity": "3", "stock": "999"}, label="A05 restock increment 3")
    p4 = product(pid)
    eq("restock stock/version", (int(p4["stock"]), int(p4["version"])), (7, 4))
    post(f"/products/{pid}", old_edit, expected=409, zero=True, label="A05 pre-restock edit 409")
    post(f"/products/{pid}/restock", {"quantity": "0"}, expected=400, zero=True, label="A05 invalid restock 400")
    post(f"/categories/{cid}/remove", expected=409, zero=True, label="A03 draft product reference removal409")
    post(f"/products/{pid}/publish", {"version": p4["version"]}, label="A04 publish fixture for A10")

    # A06 / A07: query NEW paid/cancelled orders supplied by mainline, then ship once.
    paid = order_number("paid_order")
    cancelled = order_number("cancelled_order")
    if paid:
        original = order(paid)
        safe_no = quote(paid, safe="")
        page = get(f"/orders/{safe_no}", label="A07 newly placed paid order")
        eq("A07 page marker", attrs(page, "data-page-id"), ["A07"])
        uid = int(original["user_id"])
        for query, expected_total in [({"orderNo": paid.lower()}, 1),
                                      ({"orderNo": paid[:-3]}, 0),
                                      ({"orderNo": paid.lower(), "status": "PAID", "userId": uid}, 1),
                                      ({"orderNo": paid, "userId": 2 if uid != 2 else 1}, 0)]:
            result = get("/orders?" + urlencode(query), label="A06 CI/exact/AND " + str(query))
            eq("order filter total " + str(query), count(result, "data-order-count"), expected_total)
        for query, status in [({"userId": "4"}, 404), ({"userId": "0"}, 400), ({"status": "BAD"}, 400)]:
            get("/orders?" + urlencode(query), expected=status, label="A06 invalid query")
        stocks_before = r.sql("SELECT id,stock,version FROM product ORDER BY id")
        post(f"/orders/{safe_no}/ship", label="A07 first ship")
        shipped = order(paid)
        r.check("E first ship SHIPPED with timestamp", shipped.get("status") == "SHIPPED"
                and nonnull(shipped.get("shipped_at")), shipped)
        eq("ship payment retained", (shipped.get("payment_method"), shipped.get("payment_no"), shipped.get("paid_at")),
           (original.get("payment_method"), original.get("payment_no"), original.get("paid_at")))
        eq("ship stocks and versions unchanged", r.sql("SELECT id,stock,version FROM product ORDER BY id"), stocks_before)
        post(f"/orders/{safe_no}/ship", zero=True, label="A07 repeat ship idempotent")
        eq("repeat ship original order fields", order(paid), shipped)
        user_page = get(f"/orders/{safe_no}", session=r.u, base="u", label="U08 sees shipped")
        eq("user sees SHIPPED", attrs(user_page, "data-order-status"), ["SHIPPED"])
        dashboard("after ship")
    if cancelled:
        post(f"/orders/{quote(cancelled,safe='')}/ship", expected=409, zero=True, label="A07 cancelled ship409")
    pending = one("SELECT order_no FROM sales_order WHERE status='PENDING_PAYMENT' ORDER BY id LIMIT 1")
    if pending:
        post(f"/orders/{quote(pending['order_no'],safe='')}/ship", expected=409, zero=True, label="A07 pending ship409")

    # A08 / A09: CUSTOMER-only queries, safe detail, idempotent status, stamps, old sessions.
    all_customers = get("/customers?size=50", label="A08 CUSTOMER only")
    expected_ids = [str(x["id"]) for x in r.sql("SELECT id FROM store_user WHERE role='CUSTOMER' ORDER BY id")]
    eq("A08 customer row ids", attrs(all_customers, "data-customer-id"), expected_ids)
    for state in ["ENABLED", "DISABLED"]:
        page = get("/customers?status=" + state, label="A08 " + state)
        total = one(f"SELECT COUNT(*) AS n FROM store_user WHERE role='CUSTOMER' AND status='{state}'")
        eq("A08 filtered count " + state, count(page, "data-customer-count"), int(total["n"]))
    filtered = get("/customers?q=alice&size=1", label="A08 username literal/page")
    eq("A08 alice filter", attrs(filtered, "data-customer-id"), ["1"])
    get("/customers/4", expected=404, label="A09 ADMIN excluded")
    get("/customers/999999999", expected=404, label="A09 unknown excluded")
    customer_detail = get("/customers/1", label="A09 safe detail")
    r.check("E A09 no password hash", "password_hash" not in customer_detail.text
            and "$2a$" not in customer_detail.text and "$2b$" not in customer_detail.text)
    orders_links = [d.get("href") for tag,d in Tags(customer_detail.text).rows
                    if tag == "a" and "data-customer-orders-link" in d]
    eq("A09 to A06 customer link", orders_links, ["/orders?userId=1"])
    get("/orders?userId=1&page=1&size=1", label="A06 customer paging")
    old_user = r.login("u", "alice")
    old_user_quiet = r.login("u", "alice")
    target_columns = "id,username,display_name,role,status,DATE_FORMAT(updated_at,'%Y-%m-%d %H:%i:%s.%f') AS stamp"
    before_user = one(f"SELECT {target_columns} FROM store_user WHERE id=1")
    persistent_before = {"cart": r.sql("SELECT id,user_id,product_id,quantity,version FROM cart_item ORDER BY id"),
                         "orders": r.sql("SELECT id,user_id,status,total_amount,payment_no FROM sales_order ORDER BY id"),
                         "products": r.sql("SELECT id,stock,version,status FROM product ORDER BY id")}
    post("/customers/1/status", {"targetStatus": "DISABLED"}, label="A09 disable alice")
    disabled = one(f"SELECT {target_columns} FROM store_user WHERE id=1")
    r.check("E disable stamp strictly increases", disabled["stamp"] > before_user["stamp"],
            {"before": before_user, "after": disabled})
    post("/customers/1/status", {"targetStatus": "DISABLED"}, zero=True, label="A09 repeated disable no-write")
    eq("repeat disable stamp unchanged", one(f"SELECT {target_columns} FROM store_user WHERE id=1"), disabled)
    get("/cart", expected=302, session=old_user, base="u", label="old user next protected read302")
    post("/customers/1/status", {"targetStatus": "ENABLED"}, label="A09 enable alice")
    enabled = one(f"SELECT {target_columns} FROM store_user WHERE id=1")
    r.check("E enable stamp strictly increases", enabled["stamp"] > disabled["stamp"], {"before": disabled, "after": enabled})
    post("/customers/1/status", {"targetStatus": "ENABLED"}, zero=True, label="A09 repeated enable no-write")
    get("/orders", expected=302, session=old_user_quiet, base="u", label="quiet old session disabled-enabled302")
    get("/cart", expected=302, session=old_user, base="u", label="cleared old user remains302")
    persistent_after = {"cart": r.sql("SELECT id,user_id,product_id,quantity,version FROM cart_item ORDER BY id"),
                        "orders": r.sql("SELECT id,user_id,status,total_amount,payment_no FROM sales_order ORDER BY id"),
                        "products": r.sql("SELECT id,stock,version,status FROM product ORDER BY id")}
    eq("status changes retain cart/orders/stocks", persistent_after, persistent_before)
    for path, data, expected in [("/customers/4/status", {"targetStatus": "DISABLED"}, 404),
                                  ("/customers/1/status", {"targetStatus": "BAD"}, 400)]:
        post(path, data, expected=expected, zero=True, label="A09 rejected target/status")
    post("/customers/1/status", {"targetStatus": "DISABLED"}, expected=403, zero=True, csrf=False, label="A09 missing csrf403")
    r.u = r.login("u", "alice")
    get("/cart", session=r.u, base="u", label="reenabled normal relogin200")
    dashboard("after customer toggle")

    # A10: album changes share parent version, order, ownership, final cover fallback.
    prior = product(pid)
    old_product_form = edit_data(prior)
    get(f"/products/{pid}/images", label="A10 initial empty")
    post(f"/products/{pid}/images", {"imagePath": "images/catalog-placeholder.svg", "altText": "复核后图", "sortOrder": "20"},
         expected=409, zero=True, label="A10 missing parent version409 doc discrepancy")
    for alt, sort in [("复核后图", "20"), ("复核前图", "10")]:
        p = product(pid)
        post(f"/products/{pid}/images", {"imagePath": "images/catalog-placeholder.svg", "altText": alt,
                                              "sortOrder": sort, "productVersion": p["version"]}, label="A10 add " + alt)
        eq("album add parent version+1 " + alt, int(product(pid)["version"]), int(p["version"]) + 1)
    images = r.sql(f"SELECT id,image_path,alt_text,sort_order FROM product_image WHERE product_id={pid} ORDER BY sort_order,id")
    admin_album = get(f"/products/{pid}/images", label="A10 album order")
    user_album = get(f"/products/{pid}", session=r.u, base="u", label="U03 album order")
    expected_image_ids = [str(x["id"]) for x in images]
    eq("A10 SQL order", attrs(admin_album, "data-image-id"), expected_image_ids)
    eq("U03 SQL order", attrs(user_album, "data-image-id"), expected_image_ids)
    post(f"/products/{pid}", old_product_form, expected=409, zero=True, label="A05 old form after album409")
    if images:
        image = images[0]
        iid = int(image["id"])
        p = product(pid)
        same = {"imagePath": image["image_path"], "altText": image["alt_text"],
                "sortOrder": image["sort_order"], "productVersion": p["version"]}
        post(f"/products/{pid}/images/{iid}", same, zero=True, label="A10 same-value edit idempotent")
        changed = dict(same, sortOrder="30", altText="复核已改排序")
        post(f"/products/{pid}/images/{iid}", changed, label="A10 actual edit")
        eq("album edit parent version+1", int(product(pid)["version"]), int(p["version"]) + 1)
        post(f"/products/{pid}/images/{iid}", changed, expected=409, zero=True, label="A10 stale parent409")
        foreign = one(f"SELECT id FROM product_image WHERE product_id <> {pid} ORDER BY id LIMIT 1")
        if foreign:
            current = product(pid)
            cross = dict(changed, productVersion=current["version"])
            post(f"/products/{pid}/images/{int(foreign['id'])}", cross, expected=404, zero=True, label="A10 cross-parent404")
    before_delete = product(pid)
    for image in r.sql(f"SELECT id FROM product_image WHERE product_id={pid} ORDER BY id"):
        p = product(pid)
        post(f"/products/{pid}/images/{int(image['id'])}/remove", {"productVersion": p["version"]}, label="A10 remove image")
        eq("album remove parent version+1 " + image["id"], int(product(pid)["version"]), int(p["version"]) + 1)
    empty_album = get(f"/products/{pid}/images", label="A10 after final deletion")
    empty_public = get(f"/products/{pid}", session=r.u, base="u", label="U03 after final deletion cover fallback")
    r.check("E final album empty UI", "data-image-empty" in empty_album.text and "data-gallery-empty" in empty_public.text)
    eq("no album rows remain", r.sql(f"SELECT id FROM product_image WHERE product_id={pid}"), [])
    after_delete = product(pid)
    eq("album removes retain sku/cover/stock/status", [after_delete[k] for k in ["sku","cover_image","stock","status"]],
       [before_delete[k] for k in ["sku","cover_image","stock","status"]])
    placeholder = "images/catalog-placeholder.svg"
    for base in ["u", "a"]:
        asset = get("/" + placeholder, session=fresh(), base=base, label="shared asset remains " + base)
        r.check("E shared asset SVG " + base, "svg" in asset.headers.get("Content-Type", ""), asset.headers.get("Content-Type"))
    dashboard("final", cards=True)
    r.finish("E", notes=["全部为本轮顺序HTTP请求与隔离库SQL；未执行并发、竞争或故障注入。",
                         "独立HTTP新增分类/SKU保留给F核对；未编辑seed SQL文件。",
                         "补货仅按quantity增量；以补货后的旧商品表单409验证版本保护，不宣称补货接收版本参数。",
                         "缺失productVersion当前实现409，与TST-40缺失400并列记录；不改旧文档。",
                         "主库五项统计及卡片过滤已重跑；空业务库/错误配置未在本阶段重跑，应列未验证。",
                         "AI执行的新复核证据不等于本人或组员已完成手工复核。"])

