SET time_zone='+00:00';
START TRANSACTION;
DELETE ci FROM cart_item ci JOIN store_user u ON u.id=ci.user_id WHERE u.username='alice';
INSERT INTO cart_item(user_id,product_id,quantity,version)
SELECT u.id,p.id,CASE p.sku WHEN 'CSU-LMK-NOTE-01' THEN 2 ELSE 1 END,0
FROM store_user u CROSS JOIN product p
WHERE u.username='alice' AND p.sku IN ('CSU-LMK-NOTE-01','CSU-GRAD-BOX-01');
COMMIT;
SELECT ci.id AS cart_item_id,u.username,p.id AS product_id,p.sku,ci.quantity,ci.version AS cart_version,p.version AS product_version,p.price,p.stock,p.status,p.price*ci.quantity AS subtotal
FROM cart_item ci JOIN store_user u ON u.id=ci.user_id JOIN product p ON p.id=ci.product_id WHERE u.username='alice' ORDER BY p.id;
SELECT COUNT(*) AS sku_rows,SUM(ci.quantity) AS pieces,SUM(ci.quantity*p.price) AS total_amount FROM cart_item ci JOIN store_user u ON u.id=ci.user_id JOIN product p ON p.id=ci.product_id WHERE u.username='alice';
