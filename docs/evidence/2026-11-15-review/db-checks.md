# 本轮关键SQL与真实结果

全部查询明确使用本轮隔离实例59315/csucampuscraft、UTC会话。主流程每个POST另保存七表完整有序行SHA前后，见http.jsonl；SQL夹具与业务HTTP写分开标注。无完整收货字段、密码散列或会话值归档。

## 本轮新主单与明细金额

```sql
SELECT o.id,o.order_no,o.user_id,o.status,o.total_amount,COUNT(i.id) AS line_count,SUM(i.line_amount) AS sum_lines FROM sales_order o JOIN sales_order_item i ON i.order_id=o.id WHERE o.order_no IN ('CSU-7df1c3e8521677d7043e92066497667f','CSU-6a124d4369e78aa809a309373a609d09') GROUP BY o.id,o.order_no,o.user_id,o.status,o.total_amount ORDER BY o.id;
```

```json
[
  {
    "id": "16",
    "order_no": "CSU-7df1c3e8521677d7043e92066497667f",
    "user_id": "1",
    "status": "SHIPPED",
    "total_amount": "85.00",
    "line_count": "2",
    "sum_lines": "85.00"
  },
  {
    "id": "17",
    "order_no": "CSU-6a124d4369e78aa809a309373a609d09",
    "user_id": "1",
    "status": "CANCELLED",
    "total_amount": "85.00",
    "line_count": "2",
    "sum_lines": "85.00"
  }
]
```

## 支付及履约配套字段

```sql
SELECT order_no,status,payment_method,payment_no,paid_at,cancelled_at,shipped_at,completed_at FROM sales_order WHERE order_no IN ('CSU-7df1c3e8521677d7043e92066497667f','CSU-6a124d4369e78aa809a309373a609d09') ORDER BY id;
```

```json
[
  {
    "order_no": "CSU-7df1c3e8521677d7043e92066497667f",
    "status": "SHIPPED",
    "payment_method": "MOCK",
    "payment_no": "CSUPAY-940160a21530cfb5d0ea0951d7446b0a",
    "paid_at": "2026-11-14 17:05:07.277356",
    "cancelled_at": "NULL",
    "shipped_at": "2026-11-14 17:06:39.158863",
    "completed_at": "NULL"
  },
  {
    "order_no": "CSU-6a124d4369e78aa809a309373a609d09",
    "status": "CANCELLED",
    "payment_method": "NULL",
    "payment_no": "NULL",
    "paid_at": "NULL",
    "cancelled_at": "2026-11-14 17:05:12.828133",
    "shipped_at": "NULL",
    "completed_at": "NULL"
  }
]
```

## 成交明细快照

```sql
SELECT o.order_no,i.product_id,i.sku_snapshot,i.product_name_snapshot,i.cover_image_snapshot,i.unit_price,i.quantity,i.line_amount FROM sales_order_item i JOIN sales_order o ON o.id=i.order_id WHERE o.order_no IN ('CSU-7df1c3e8521677d7043e92066497667f','CSU-6a124d4369e78aa809a309373a609d09') ORDER BY o.id,i.product_id;
```

```json
[
  {
    "order_no": "CSU-7df1c3e8521677d7043e92066497667f",
    "product_id": "1",
    "sku_snapshot": "CSU-LMK-NOTE-01",
    "product_name_snapshot": "潇湘校区图书馆方格本",
    "cover_image_snapshot": "images/catalog-placeholder.svg",
    "unit_price": "18.00",
    "quantity": "2",
    "line_amount": "36.00"
  },
  {
    "order_no": "CSU-7df1c3e8521677d7043e92066497667f",
    "product_id": "56",
    "sku_snapshot": "CSU-GRAD-BOX-01",
    "product_name_snapshot": "中南毕业纪念礼盒",
    "cover_image_snapshot": "images/catalog-placeholder.svg",
    "unit_price": "49.00",
    "quantity": "1",
    "line_amount": "49.00"
  },
  {
    "order_no": "CSU-6a124d4369e78aa809a309373a609d09",
    "product_id": "1",
    "sku_snapshot": "CSU-LMK-NOTE-01",
    "product_name_snapshot": "潇湘校区图书馆方格本",
    "cover_image_snapshot": "images/catalog-placeholder.svg",
    "unit_price": "18.00",
    "quantity": "2",
    "line_amount": "36.00"
  },
  {
    "order_no": "CSU-6a124d4369e78aa809a309373a609d09",
    "product_id": "56",
    "sku_snapshot": "CSU-GRAD-BOX-01",
    "product_name_snapshot": "中南毕业纪念礼盒",
    "cover_image_snapshot": "images/catalog-placeholder.svg",
    "unit_price": "49.00",
    "quantity": "1",
    "line_amount": "49.00"
  }
]
```

## 全种子库存公式

```sql
SELECT COUNT(*) AS products,SUM(x.stock<>x.expected_stock) AS mismatches FROM (SELECT p.id,p.stock,ref.stock-COALESCE(SUM(CASE WHEN o.order_no IN ('CSU-7df1c3e8521677d7043e92066497667f','CSU-6a124d4369e78aa809a309373a609d09') AND o.status<>'CANCELLED' THEN i.quantity ELSE 0 END),0) AS expected_stock FROM product p JOIN review_reference.product ref ON ref.sku=p.sku LEFT JOIN sales_order_item i ON i.product_id=p.id LEFT JOIN sales_order o ON o.id=i.order_id GROUP BY p.id,p.stock,ref.stock) x;
```

```json
[
  {
    "products": "60",
    "mismatches": "0"
  }
]
```

## 主线与独立商品当前库存版本

```sql
SELECT id,sku,stock,status,version,cover_image FROM product WHERE id IN (1,56,61) ORDER BY id;
```

```json
[
  {
    "id": "1",
    "sku": "CSU-LMK-NOTE-01",
    "stock": "8",
    "status": "DRAFT",
    "version": "9",
    "cover_image": "images/review-missing-cover.svg"
  },
  {
    "id": "56",
    "sku": "CSU-GRAD-BOX-01",
    "stock": "11",
    "status": "ON_SALE",
    "version": "4",
    "cover_image": "images/catalog-placeholder.svg"
  },
  {
    "id": "61",
    "sku": "REVIEW-20261115-170629952093",
    "stock": "7",
    "status": "ON_SALE",
    "version": "14",
    "cover_image": "images/catalog-placeholder.svg"
  }
]
```

## 全行购物车徽标

```sql
SELECT user_id,COUNT(*) AS sku_rows,SUM(quantity) AS badge FROM cart_item GROUP BY user_id ORDER BY user_id;
```

```json
[
  {
    "user_id": "1",
    "sku_rows": "1",
    "badge": "1"
  },
  {
    "user_id": "2",
    "sku_rows": "4",
    "badge": "5"
  }
]
```

## 控制台五项独立SQL

```sql
SELECT (SELECT COUNT(*) FROM product WHERE status='ON_SALE') AS on_sale,(SELECT COUNT(*) FROM product WHERE status='DRAFT') AS draft,(SELECT COUNT(*) FROM sales_order WHERE status='PAID') AS paid,(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='ENABLED') AS enabled,(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='DISABLED') AS disabled;
```

```json
[
  {
    "on_sale": "54",
    "draft": "7",
    "paid": "2",
    "enabled": "2",
    "disabled": "1"
  }
]
```

## 动作时的独立前后结果

以下摘自本轮checks.jsonl保存的实际观测，不由当前状态反推过去。

### inventory10/12 to8/11 and version+1

```json
{
  "at": "2026-11-14T17:05:02.431149+00:00",
  "stage": "C",
  "name": "inventory10/12 to8/11 and version+1",
  "passed": true,
  "detail": {
    "before": [
      {
        "id": "1",
        "sku": "CSU-LMK-NOTE-01",
        "name": "潇湘校区图书馆方格本",
        "price": "18.00",
        "stock": "10",
        "status": "ON_SALE",
        "version": "0",
        "cover_image": "images/catalog-placeholder.svg"
      },
      {
        "id": "56",
        "sku": "CSU-GRAD-BOX-01",
        "name": "中南毕业纪念礼盒",
        "price": "49.00",
        "stock": "12",
        "status": "ON_SALE",
        "version": "1",
        "cover_image": "images/catalog-placeholder.svg"
      }
    ],
    "after": [
      {
        "id": "1",
        "sku": "CSU-LMK-NOTE-01",
        "name": "潇湘校区图书馆方格本",
        "price": "18.00",
        "stock": "8",
        "status": "ON_SALE",
        "version": "1",
        "cover_image": "images/catalog-placeholder.svg"
      },
      {
        "id": "56",
        "sku": "CSU-GRAD-BOX-01",
        "name": "中南毕业纪念礼盒",
        "price": "49.00",
        "stock": "11",
        "status": "ON_SALE",
        "version": "2",
        "cover_image": "images/catalog-placeholder.svg"
      }
    ]
  }
}
```

### cancel returns2/1 and increments each version once

```json
{
  "at": "2026-11-14T17:05:13.170501+00:00",
  "stage": "D",
  "name": "cancel returns2/1 and increments each version once",
  "passed": true,
  "detail": {
    "before": [
      {
        "id": "1",
        "sku": "CSU-LMK-NOTE-01",
        "name": "潇湘校区图书馆方格本",
        "price": "18.00",
        "stock": "6",
        "status": "DRAFT",
        "version": "7",
        "cover_image": "images/catalog-placeholder.svg"
      },
      {
        "id": "56",
        "sku": "CSU-GRAD-BOX-01",
        "name": "中南毕业纪念礼盒",
        "price": "49.00",
        "stock": "10",
        "status": "ON_SALE",
        "version": "3",
        "cover_image": "images/catalog-placeholder.svg"
      }
    ],
    "after": [
      {
        "id": "1",
        "sku": "CSU-LMK-NOTE-01",
        "name": "潇湘校区图书馆方格本",
        "price": "18.00",
        "stock": "8",
        "status": "DRAFT",
        "version": "8",
        "cover_image": "images/catalog-placeholder.svg"
      },
      {
        "id": "56",
        "sku": "CSU-GRAD-BOX-01",
        "name": "中南毕业纪念礼盒",
        "price": "49.00",
        "stock": "11",
        "status": "ON_SALE",
        "version": "4",
        "cover_image": "images/catalog-placeholder.svg"
      }
    ]
  }
}
```

### all seven full-row hashes unchanged across app restarts

```json
{
  "at": "2026-11-14T17:13:47.202592+00:00",
  "stage": "persistence",
  "name": "all seven full-row hashes unchanged across app restarts",
  "passed": true,
  "detail": {
    "before": {
      "store_user": {
        "rows": 4,
        "sha256": "21c6139ff37fc486d20caedcb8b089207fd8cf49c319e7e4a6edd009cbdfcef3"
      },
      "category": {
        "rows": 17,
        "sha256": "e44ab86ca824a748e401ddd3c7e632613173654a7fc4a7f7c6c41fe4658f8c33"
      },
      "product": {
        "rows": 61,
        "sha256": "6829cb9ab651ac3ad3d2d62f742ea502ec7fdc9a42d7c4312e6f78e6b4a5e692"
      },
      "product_image": {
        "rows": 100,
        "sha256": "71d50d87824e3788f70de71619ff9bb1c9b915a1eb4be73287b09b0cf6bb0561"
      },
      "cart_item": {
        "rows": 5,
        "sha256": "219ba9efaee880ea2a1aebbdd7e6d5ddba31accf6ddfa4460b5faa7bb7d25f37"
      },
      "sales_order": {
        "rows": 12,
        "sha256": "370c85a7faf9db0ba0103769532c82b29b3888053431d1d20d7682789c064efb"
      },
      "sales_order_item": {
        "rows": 24,
        "sha256": "9560bbc68392b239806a21ce9a1c91c35942cc3cbb4bcb20136e784780f8d3e6"
      }
    },
    "after": {
      "store_user": {
        "rows": 4,
        "sha256": "21c6139ff37fc486d20caedcb8b089207fd8cf49c319e7e4a6edd009cbdfcef3"
      },
      "category": {
        "rows": 17,
        "sha256": "e44ab86ca824a748e401ddd3c7e632613173654a7fc4a7f7c6c41fe4658f8c33"
      },
      "product": {
        "rows": 61,
        "sha256": "6829cb9ab651ac3ad3d2d62f742ea502ec7fdc9a42d7c4312e6f78e6b4a5e692"
      },
      "product_image": {
        "rows": 100,
        "sha256": "71d50d87824e3788f70de71619ff9bb1c9b915a1eb4be73287b09b0cf6bb0561"
      },
      "cart_item": {
        "rows": 5,
        "sha256": "219ba9efaee880ea2a1aebbdd7e6d5ddba31accf6ddfa4460b5faa7bb7d25f37"
      },
      "sales_order": {
        "rows": 12,
        "sha256": "370c85a7faf9db0ba0103769532c82b29b3888053431d1d20d7682789c064efb"
      },
      "sales_order_item": {
        "rows": 24,
        "sha256": "9560bbc68392b239806a21ce9a1c91c35942cc3cbb4bcb20136e784780f8d3e6"
      }
    }
  }
}
```

## 不变量与CHECK边界

全库总额/行金额/孤儿/车唯一/凭证唯一由stage-F实跑。全部支付配套与取消/发货/完成时间状态配套、时间链由final-invariants.json逐项SQL实跑，全部零违规。两库35个CHECK元数据均启用，运行拒绝仅负库存3819代表样本，不称所有非法样本已穷举。

临时SQL夹具：A账号role/status/stamp与同库主题完整恢复；B库存200/下架边界恢复库存和状态；C改价夹具恢复价与version。C/D/E与补充的管理维护和业务成交留在隔离库，绝不触及开发库或改写seed文件。独立REVIEW商品起始4、补货3、现库存7；种子60SKU按参照库初值减本轮未取消净成交逐一核对。
