-- CSUCampusCraft 实验一 MySQL 初始化
-- 适用 MySQL 8.4，使用 InnoDB。在 mysql 客户端选择预先创建的 UTF-8 空库 csucampuscraft 后执行。
-- 01-schema.sql 与 02-schema-with-demo.sql 二选一。使用批处理模式，遇错停止，请勿使用 --force。
-- 建表语句分别提交。若导入失败，检查错误并在另一个空库重试。
-- 正常应用启动不会执行本脚本。

SET NAMES utf8mb4 COLLATE utf8mb4_0900_as_ci;
SET SESSION time_zone = '+00:00';

-- ===== 七张表的统一结构开始 =====

-- 1. 教学账号：登录身份与普通用户/管理员角色。
CREATE TABLE store_user (
    id BIGINT NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(50) NOT NULL,
    role VARCHAR(16) COLLATE utf8mb4_0900_bin NOT NULL,
    status VARCHAR(16) COLLATE utf8mb4_0900_bin NOT NULL DEFAULT 'ENABLED',
    email VARCHAR(100) NULL,
    phone VARCHAR(30) NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT ck_user_username CHECK (CHAR_LENGTH(TRIM(username)) > 0),
    CONSTRAINT ck_user_password CHECK (CHAR_LENGTH(TRIM(password_hash)) > 0),
    CONSTRAINT ck_user_display_name CHECK (CHAR_LENGTH(TRIM(display_name)) > 0),
    CONSTRAINT ck_user_role CHECK (role IN ('CUSTOMER', 'ADMIN')),
    CONSTRAINT ck_user_status CHECK (status IN ('ENABLED', 'DISABLED')),
    UNIQUE KEY uk_user_username (username)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;

-- 2. 两级分类：parent_id为空表示一级；二级必须指向一级，由Service校验。
-- parent_key是生成列：插入/更新实体时不要写入它。
CREATE TABLE category (
    id BIGINT NOT NULL AUTO_INCREMENT,
    code VARCHAR(32) NOT NULL,
    parent_id BIGINT NULL,
    parent_key BIGINT GENERATED ALWAYS AS (COALESCE(parent_id, 0)) STORED,
    name VARCHAR(50) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT fk_category_parent FOREIGN KEY (parent_id) REFERENCES category (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_category_code CHECK (CHAR_LENGTH(TRIM(code)) > 0),
    CONSTRAINT ck_category_name CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    CONSTRAINT ck_category_sort CHECK (sort_order >= 0),
    UNIQUE KEY uk_category_code (code),
    UNIQUE KEY uk_category_sibling_name (parent_key, name),
    KEY idx_category_parent_sort (parent_id, sort_order, id)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;

-- 3. 一个商品对应一个可销售SKU，不做多规格；下架代替删除。
CREATE TABLE product (
    id BIGINT NOT NULL AUTO_INCREMENT,
    sku VARCHAR(40) NOT NULL,
    category_id BIGINT NOT NULL,
    name VARCHAR(120) NOT NULL,
    summary VARCHAR(500) NULL,
    description TEXT NULL,
    cover_image VARCHAR(255) NOT NULL DEFAULT 'images/catalog-placeholder.svg',
    price DECIMAL(12,2) NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(16) COLLATE utf8mb4_0900_bin NOT NULL DEFAULT 'DRAFT',
    sort_order INTEGER NOT NULL DEFAULT 0,
    version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES category (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_product_sku CHECK (CHAR_LENGTH(TRIM(sku)) > 0),
    CONSTRAINT ck_product_name CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    CONSTRAINT ck_product_cover CHECK (CHAR_LENGTH(TRIM(cover_image)) > 0),
    CONSTRAINT ck_product_price CHECK (price > 0),
    CONSTRAINT ck_product_stock CHECK (stock >= 0),
    CONSTRAINT ck_product_status CHECK (status IN ('DRAFT', 'ON_SALE')),
    CONSTRAINT ck_product_sort CHECK (sort_order >= 0),
    CONSTRAINT ck_product_version CHECK (version >= 0),
    UNIQUE KEY uk_product_sku (sku),
    KEY idx_product_category_status_sort (category_id, status, sort_order, id),
    KEY idx_product_status_sort (status, sort_order, id)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;

-- 4. 图片相册与封面分开；多个商品可复用相同的教学图片。
CREATE TABLE product_image (
    id BIGINT NOT NULL AUTO_INCREMENT,
    product_id BIGINT NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    alt_text VARCHAR(120) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    CONSTRAINT fk_image_product FOREIGN KEY (product_id) REFERENCES product (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_image_path CHECK (CHAR_LENGTH(TRIM(image_path)) > 0),
    CONSTRAINT ck_image_sort CHECK (sort_order >= 0),
    KEY idx_image_product_sort (product_id, sort_order, id)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;

-- 5. 登录用户的持久购物车：价格不存这里；购物车不占库存。
CREATE TABLE cart_item (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uk_cart_user_product (user_id, product_id),
    CONSTRAINT fk_cart_user FOREIGN KEY (user_id) REFERENCES store_user (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_cart_product FOREIGN KEY (product_id) REFERENCES product (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_cart_quantity CHECK (quantity BETWEEN 1 AND 99),
    CONSTRAINT ck_cart_version CHECK (version >= 0),
    KEY idx_cart_product (product_id)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;

-- 6. 订单主表：模拟付款成功即PAID（待发货），没有真实支付渠道或退款。
CREATE TABLE sales_order (
    id BIGINT NOT NULL AUTO_INCREMENT,
    order_no VARCHAR(40) NOT NULL,
    user_id BIGINT NOT NULL,
    status VARCHAR(16) COLLATE utf8mb4_0900_bin NOT NULL DEFAULT 'PENDING_PAYMENT',
    total_amount DECIMAL(12,2) NOT NULL,
    receiver_name VARCHAR(50) NOT NULL,
    receiver_phone VARCHAR(30) NOT NULL,
    receiver_address VARCHAR(255) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    payment_method VARCHAR(16) COLLATE utf8mb4_0900_bin NULL,
    payment_no VARCHAR(40) NULL,
    paid_at TIMESTAMP(6) NULL,
    cancelled_at TIMESTAMP(6) NULL,
    shipped_at TIMESTAMP(6) NULL,
    completed_at TIMESTAMP(6) NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES store_user (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_order_no CHECK (CHAR_LENGTH(TRIM(order_no)) > 0),
    CONSTRAINT ck_order_total CHECK (total_amount > 0),
    CONSTRAINT ck_order_receiver CHECK (
        CHAR_LENGTH(TRIM(receiver_name)) > 0 AND
        CHAR_LENGTH(TRIM(receiver_phone)) > 0 AND
        CHAR_LENGTH(TRIM(receiver_address)) > 0
    ),
    CONSTRAINT ck_order_status CHECK (status IN ('PENDING_PAYMENT', 'PAID', 'SHIPPED', 'COMPLETED', 'CANCELLED')),
    CONSTRAINT ck_order_payment_info CHECK (
        (status IN ('PENDING_PAYMENT', 'CANCELLED')
            AND payment_method IS NULL AND payment_no IS NULL AND paid_at IS NULL)
        OR
        (status IN ('PAID', 'SHIPPED', 'COMPLETED')
            AND payment_method IS NOT NULL AND payment_method = 'MOCK'
            AND payment_no IS NOT NULL AND CHAR_LENGTH(TRIM(payment_no)) > 0
            AND paid_at IS NOT NULL)
    ),
    CONSTRAINT ck_order_cancel_time CHECK (
        (status = 'CANCELLED' AND cancelled_at IS NOT NULL)
        OR (status <> 'CANCELLED' AND cancelled_at IS NULL)
    ),
    CONSTRAINT ck_order_ship_time CHECK (
        (status IN ('SHIPPED', 'COMPLETED') AND shipped_at IS NOT NULL)
        OR (status NOT IN ('SHIPPED', 'COMPLETED') AND shipped_at IS NULL)
    ),
    CONSTRAINT ck_order_complete_time CHECK (
        (status = 'COMPLETED' AND completed_at IS NOT NULL)
        OR (status <> 'COMPLETED' AND completed_at IS NULL)
    ),
    CONSTRAINT ck_order_time_sequence CHECK (
        (paid_at IS NULL OR paid_at >= created_at) AND
        (cancelled_at IS NULL OR cancelled_at >= created_at) AND
        (shipped_at IS NULL OR shipped_at >= paid_at) AND
        (completed_at IS NULL OR completed_at >= shipped_at)
    ),
    UNIQUE KEY uk_order_no (order_no),
    UNIQUE KEY uk_order_payment_no (payment_no),
    KEY idx_order_user_created (user_id, created_at, id),
    KEY idx_order_status_created (status, created_at, id)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;

-- 7. 订单明细：保留成交时快照，不随商品后续变化而更新。
CREATE TABLE sales_order_item (
    id BIGINT NOT NULL AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    sku_snapshot VARCHAR(40) NOT NULL,
    product_name_snapshot VARCHAR(120) NOT NULL,
    cover_image_snapshot VARCHAR(255) NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    quantity INTEGER NOT NULL,
    line_amount DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_order_item_product (order_id, product_id),
    CONSTRAINT fk_order_item_order FOREIGN KEY (order_id) REFERENCES sales_order (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_order_item_product FOREIGN KEY (product_id) REFERENCES product (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_order_item_sku CHECK (CHAR_LENGTH(TRIM(sku_snapshot)) > 0),
    CONSTRAINT ck_order_item_name CHECK (CHAR_LENGTH(TRIM(product_name_snapshot)) > 0),
    CONSTRAINT ck_order_item_cover CHECK (CHAR_LENGTH(TRIM(cover_image_snapshot)) > 0),
    CONSTRAINT ck_order_item_price CHECK (unit_price > 0),
    CONSTRAINT ck_order_item_quantity CHECK (quantity BETWEEN 1 AND 99),
    CONSTRAINT ck_order_item_amount CHECK (line_amount > 0 AND line_amount = unit_price * quantity),
    KEY idx_order_item_product (product_id)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;
-- ===== 七张表的统一结构结束 =====

-- 标识列按 utf8mb4_0900_as_ci 使用普通等值查询，大小写不区分，重音不同可区分。
-- 状态与角色等枚举列按 utf8mb4_0900_bin 比较。支付号唯一索引允许多个 NULL。
-- Service 校验分类层级、二级商品归属、身份及资源归属，负责购物车上限、库存和版本、
-- 状态流转及主单汇总。创建订单、写明细、扣库存、清理本次车条目属于同一 Service 事务。

-- ===== 演示数据开始 =====
-- 演示数据在一个事务中导入，显式种子 ID 由 InnoDB 自动推进 AUTO_INCREMENT。
START TRANSACTION;

-- 教学演示密码统一为 CSUCampusCraft123!；BCrypt cost=10，每个账号独立盐。
-- 教学账号仅用于本地演示。密码校验使用 BCryptPasswordEncoder.matches。

INSERT INTO store_user
    (id, username, password_hash, display_name, role, status, email, phone)
VALUES
    (1, 'alice', '$2a$10$waT5E94UChp6TlLehqRdN.sqZ/l8CubIaYlUEew4idnNam7.K4Cp.', '林同学', 'CUSTOMER', 'ENABLED', 'alice@example.test', NULL),
    (2, 'bob', '$2a$10$5aZBeO9kwfh87QRvBLmmUuz/3Ki8NPpMxFOFg.WwuQk6.eDG34Zji', '陈同学', 'CUSTOMER', 'ENABLED', 'bob@example.test', NULL),
    (3, 'disabled', '$2a$10$Hc0M7oHn35X368OOycJjYu8MZhILn/pYWdqwWpOacS3SBuQhupMIq', '禁用教学账号', 'CUSTOMER', 'DISABLED', 'disabled@example.test', NULL),
    (4, 'admin', '$2a$10$ZPOz0tj2SRebbCmJp1oi9OOeT6N3Gj6SEPSWdJFMNpLM66h9TjXRi', '商城管理员', 'ADMIN', 'ENABLED', 'admin@example.test', NULL);

-- 一级分类先插入。各主题固定使用文具和纪念周边两个二级编码。
INSERT INTO category (id, code, parent_id, name, sort_order) VALUES
    (1, 'LANDMARK', NULL, '校园地标', 10),
    (2, 'COLLEGE', NULL, '学院风采', 20),
    (3, 'CLUB', NULL, '社团活动', 30),
    (4, 'SPORTS', NULL, '校园运动', 40),
    (5, 'GRADUATION', NULL, '毕业纪念', 50);

INSERT INTO category (id, code, parent_id, name, sort_order) VALUES
    (101, 'LANDMARK_STATIONERY', 1, '文具', 10),
    (102, 'LANDMARK_SOUVENIR', 1, '纪念周边', 20),
    (201, 'COLLEGE_STATIONERY', 2, '文具', 10),
    (202, 'COLLEGE_SOUVENIR', 2, '纪念周边', 20),
    (301, 'CLUB_STATIONERY', 3, '文具', 10),
    (302, 'CLUB_SOUVENIR', 3, '纪念周边', 20),
    (401, 'SPORTS_STATIONERY', 4, '文具', 10),
    (402, 'SPORTS_SOUVENIR', 4, '纪念周边', 20),
    (501, 'GRADUATION_STATIONERY', 5, '文具', 10),
    (502, 'GRADUATION_SOUVENIR', 5, '纪念周边', 20);

-- 每个二级类目 6 件商品，按 ID 保持稳定排序。礼盒按独立成品库存计量。
-- 缺图示例 CSU-CLB-STAND-01 的无效封面路径用于验证占位回退。
INSERT INTO product
    (id, sku, category_id, name, summary, description, cover_image, price, stock, status, sort_order, version)
    VALUES
    (1, 'CSU-LMK-NOTE-01', 101, '潇湘校区图书馆方格本', '以潇湘校区图书馆为主题的方格本。演示库初始化后可售 10 本，用于购买与补货并发验证。', '以潇湘校区图书馆为主题的方格本。演示库初始化后可售 10 本，用于购买与补货并发验证。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 18.00, 10, 'ON_SALE', 10, 0),
    (2, 'CSU-LMK-BOOKMARK-01', 101, '玉带河书签', '以潇湘校区玉带河为主题的纸质书签。', '以潇湘校区玉带河为主题的纸质书签。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 8.00, 25, 'ON_SALE', 20, 0),
    (3, 'CSU-LMK-FOLDER-01', 101, '潇湘阅览文件夹', '校园文创课程样品。设计主题为潇湘阅览文件夹。', '校园文创课程样品。设计主题为潇湘阅览文件夹。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 16.90, 22, 'ON_SALE', 30, 0),
    (4, 'CSU-LMK-TABS-01', 101, '图书馆索引便利贴', '校园文创课程样品。设计主题为图书馆索引便利贴。', '校园文创课程样品。设计主题为图书馆索引便利贴。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 9.90, 45, 'ON_SALE', 40, 0),
    (5, 'CSU-LMK-NOTE-02', 101, '玉带河横线本', '校园文创课程样品。设计主题为玉带河横线本。', '校园文创课程样品。设计主题为玉带河横线本。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 16.00, 24, 'ON_SALE', 50, 0),
    (6, 'CSU-LMK-NOTE-03', 101, '校史参观纪事册', '校园文创课程样品。设计主题为校史参观纪事册。', '校园文创课程样品。设计主题为校史参观纪事册。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 22.00, 8, 'ON_SALE', 60, 0),
    (7, 'CSU-LMK-MAGNET-01', 102, '校史馆冰箱贴', '以玉带河畔的中南大学校史馆为设计主题。', '以玉带河畔的中南大学校史馆为设计主题。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 24.00, 25, 'ON_SALE', 70, 0),
    (8, 'CSU-LMK-CARDS-01', 102, '潇湘校区地标明信片套装', '固定套装，按套购买及计库存。', '固定套装，按套购买及计库存。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 19.90, 30, 'ON_SALE', 80, 0),
    (9, 'CSU-LMK-KEY-01', 102, '图书馆线稿挂件', '校园文创课程样品。设计主题为图书馆线稿挂件。', '校园文创课程样品。设计主题为图书馆线稿挂件。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 12.90, 14, 'ON_SALE', 90, 0),
    (10, 'CSU-LMK-PIN-01', 102, '校史馆线描徽章', '校园文创课程样品。设计主题为校史馆线描徽章。', '校园文创课程样品。设计主题为校史馆线描徽章。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 14.90, 20, 'ON_SALE', 100, 0),
    (11, 'CSU-LMK-ART-01', 102, '玉带河插画装饰画', '上架售罄示例，可浏览，不能购买。', '上架售罄示例，可浏览，不能购买。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 32.00, 0, 'ON_SALE', 110, 0),
    (12, 'CSU-LMK-STICKER-01', 102, '潇湘地标贴纸包', '下架示例。', '下架示例。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 9.90, 18, 'DRAFT', 120, 0),
    (13, 'CSU-COL-MEMO-01', 201, '计算机学院代码便签', '以计算机学院为主题的代码风格便签。', '以计算机学院为主题的代码风格便签。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 12.80, 35, 'ON_SALE', 130, 0),
    (14, 'CSU-COL-NOTE-01', 201, '材料科学与工程学院晶格笔记本', '校园文创课程样品。设计主题为材料科学与工程学院晶格笔记本。', '校园文创课程样品。设计主题为材料科学与工程学院晶格笔记本。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 25.00, 23, 'ON_SALE', 140, 0),
    (15, 'CSU-COL-SKETCH-01', 201, '建筑与艺术学院草图本', '校园文创课程样品。设计主题为建筑与艺术学院草图本。', '校园文创课程样品。设计主题为建筑与艺术学院草图本。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 28.00, 12, 'ON_SALE', 150, 0),
    (16, 'CSU-COL-BOOKMARK-01', 201, '材料科学与工程学院晶格书签', '校园文创课程样品。设计主题为材料科学与工程学院晶格书签。', '校园文创课程样品。设计主题为材料科学与工程学院晶格书签。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 8.80, 17, 'ON_SALE', 160, 0),
    (17, 'CSU-COL-NOTE-02', 201, '计算机学院算法练习本', '校园文创课程样品。设计主题为计算机学院算法练习本。', '校园文创课程样品。设计主题为计算机学院算法练习本。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 15.50, 12, 'ON_SALE', 170, 0),
    (18, 'CSU-COL-PEN-01', 201, '建筑与艺术学院线稿铅笔套装', '低库存示例，购物车可预置超过当前库存的数量。', '低库存示例，购物车可预置超过当前库存的数量。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 13.00, 1, 'ON_SALE', 180, 0),
    (19, 'CSU-COL-PIN-01', 202, '计算机学院像素徽章', '校园文创课程样品。设计主题为计算机学院像素徽章。', '校园文创课程样品。设计主题为计算机学院像素徽章。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 16.00, 26, 'ON_SALE', 190, 0),
    (20, 'CSU-COL-STAND-01', 202, '建筑与艺术学院建筑线稿立牌', '校园文创课程样品。设计主题为建筑与艺术学院建筑线稿立牌。', '校园文创课程样品。设计主题为建筑与艺术学院建筑线稿立牌。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 29.90, 15, 'ON_SALE', 200, 0),
    (21, 'CSU-COL-MAGNET-01', 202, '材料科学与工程学院晶格磁贴', '校园文创课程样品。设计主题为材料科学与工程学院晶格磁贴。', '校园文创课程样品。设计主题为材料科学与工程学院晶格磁贴。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 19.00, 17, 'ON_SALE', 210, 0),
    (22, 'CSU-COL-KEY-01', 202, '计算机学院像素钥匙扣', '校园文创课程样品。设计主题为计算机学院像素钥匙扣。', '校园文创课程样品。设计主题为计算机学院像素钥匙扣。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 14.90, 20, 'ON_SALE', 220, 0),
    (23, 'CSU-COL-CARDS-01', 202, '学院风采明信片套装', '校园文创课程样品。设计主题为学院风采明信片套装。', '校园文创课程样品。设计主题为学院风采明信片套装。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 23.00, 18, 'ON_SALE', 230, 0),
    (24, 'CSU-COL-STICKER-01', 202, '学院风采插画贴纸包', '下架示例。', '下架示例。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 12.90, 12, 'DRAFT', 240, 0),
    (25, 'CSU-CLB-FOLDER-01', 301, '社团招新文件夹', '校园文创课程样品。设计主题为社团招新文件夹。', '校园文创课程样品。设计主题为社团招新文件夹。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 11.90, 30, 'ON_SALE', 250, 0),
    (26, 'CSU-CLB-NOTE-01', 301, '校园摄影手账本', '校园文创课程样品。设计主题为校园摄影手账本。', '校园文创课程样品。设计主题为校园摄影手账本。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 21.00, 30, 'ON_SALE', 260, 0),
    (27, 'CSU-CLB-NOTE-02', 301, '校园乐队练习记事本', '校园文创课程样品。设计主题为校园乐队练习记事本。', '校园文创课程样品。设计主题为校园乐队练习记事本。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 16.90, 15, 'ON_SALE', 270, 0),
    (28, 'CSU-CLB-MEMO-01', 301, '校园志愿活动便利贴', '校园文创课程样品。设计主题为校园志愿活动便利贴。', '校园文创课程样品。设计主题为校园志愿活动便利贴。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 8.90, 35, 'ON_SALE', 280, 0),
    (29, 'CSU-CLB-BOOKMARK-01', 301, '社团读书会纸质书签', '上架售罄示例。', '上架售罄示例。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 6.90, 0, 'ON_SALE', 290, 0),
    (30, 'CSU-CLB-FOLDER-02', 301, '社团活动记录册', '下架示例。', '下架示例。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 18.50, 6, 'DRAFT', 300, 0),
    (31, 'CSU-CLB-KEY-01', 302, '摄影主题钥匙扣', '校园文创课程样品。设计主题为摄影主题钥匙扣。', '校园文创课程样品。设计主题为摄影主题钥匙扣。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 14.00, 22, 'ON_SALE', 310, 0),
    (32, 'CSU-CLB-PIN-01', 302, '校园乐队主题徽章', '校园文创课程样品。设计主题为校园乐队主题徽章。', '校园文创课程样品。设计主题为校园乐队主题徽章。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 15.00, 19, 'ON_SALE', 320, 0),
    (33, 'CSU-CLB-CARDS-01', 302, '社团活动主题明信片套装', '校园文创课程样品。设计主题为社团活动主题明信片套装。', '校园文创课程样品。设计主题为社团活动主题明信片套装。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 18.00, 13, 'ON_SALE', 330, 0),
    (34, 'CSU-CLB-STICKER-01', 302, '校园舞台贴纸套装', '校园文创课程样品。设计主题为校园舞台贴纸套装。', '校园文创课程样品。设计主题为校园舞台贴纸套装。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 9.90, 24, 'ON_SALE', 340, 0),
    (35, 'CSU-CLB-MAGNET-01', 302, '摄影取景框冰箱贴', '校园文创课程样品。设计主题为摄影取景框冰箱贴。', '校园文创课程样品。设计主题为摄影取景框冰箱贴。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 21.00, 9, 'ON_SALE', 350, 0),
    (36, 'CSU-CLB-STAND-01', 302, '校园演出亚克力立牌', '覆盖封面资源缺失的教学场景，页面应回退到默认占位图。', '覆盖封面资源缺失的教学场景，页面应回退到默认占位图。 商品和价格均为教学演示数据。', 'images/demo-missing.svg', 29.00, 7, 'ON_SALE', 360, 0),
    (37, 'CSU-SPT-NOTE-01', 401, '潇湘校区体育场赛事记录本', '以潇湘校区体育场为主题的比赛记录本。', '以潇湘校区体育场为主题的比赛记录本。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 19.00, 18, 'ON_SALE', 370, 0),
    (38, 'CSU-SPT-CASE-01', 401, '跑道主题笔袋', '校园文创课程样品。设计主题为跑道主题笔袋。', '校园文创课程样品。设计主题为跑道主题笔袋。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 24.00, 20, 'ON_SALE', 380, 0),
    (39, 'CSU-SPT-MEMO-01', 401, '训练计划便利贴', '校园文创课程样品。设计主题为训练计划便利贴。', '校园文创课程样品。设计主题为训练计划便利贴。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 10.00, 16, 'ON_SALE', 390, 0),
    (40, 'CSU-SPT-NOTE-02', 401, '校园运动积分记录册', '校园文创课程样品。设计主题为校园运动积分记录册。', '校园文创课程样品。设计主题为校园运动积分记录册。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 16.00, 21, 'ON_SALE', 400, 0),
    (41, 'CSU-SPT-BOOKMARK-01', 401, '田径主题书签', '校园文创课程样品。设计主题为田径主题书签。', '校园文创课程样品。设计主题为田径主题书签。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 7.90, 18, 'ON_SALE', 410, 0),
    (42, 'CSU-SPT-FOLDER-01', 401, '校园球赛文件夹', '下架示例。', '下架示例。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 13.00, 11, 'DRAFT', 420, 0),
    (43, 'CSU-SPT-PIN-01', 402, '校园运动纪念章', '校园文创课程样品。设计主题为校园运动纪念章。', '校园文创课程样品。设计主题为校园运动纪念章。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 17.00, 18, 'ON_SALE', 430, 0),
    (44, 'CSU-SPT-KEY-01', 402, '体育场跑道挂件', '校园文创课程样品。设计主题为体育场跑道挂件。', '校园文创课程样品。设计主题为体育场跑道挂件。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 15.00, 21, 'ON_SALE', 440, 0),
    (45, 'CSU-SPT-MAGNET-01', 402, '潇湘校区体育场冰箱贴', '校园文创课程样品。设计主题为潇湘校区体育场冰箱贴。', '校园文创课程样品。设计主题为潇湘校区体育场冰箱贴。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 22.00, 14, 'ON_SALE', 450, 0),
    (46, 'CSU-SPT-CARDS-01', 402, '校园运动主题明信片套装', '校园文创课程样品。设计主题为校园运动主题明信片套装。', '校园文创课程样品。设计主题为校园运动主题明信片套装。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 18.90, 11, 'ON_SALE', 460, 0),
    (47, 'CSU-SPT-STAND-01', 402, '校园田径主题立牌', '上架售罄示例。', '上架售罄示例。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 27.00, 0, 'ON_SALE', 470, 0),
    (48, 'CSU-SPT-STICKER-01', 402, '校运会纪念贴纸包', '校园文创课程样品。设计主题为校运会纪念贴纸包。', '校园文创课程样品。设计主题为校运会纪念贴纸包。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 10.90, 16, 'ON_SALE', 480, 0),
    (49, 'CSU-GRAD-NOTE-01', 501, '毕业留言本', '校园文创课程样品。设计主题为毕业留言本。', '校园文创课程样品。设计主题为毕业留言本。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 25.00, 26, 'ON_SALE', 490, 0),
    (50, 'CSU-GRAD-CARDS-01', 501, '毕业祝福卡片套装', '多张祝福卡片成套出售，按套计库存。', '多张祝福卡片成套出售，按套计库存。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 18.00, 19, 'ON_SALE', 500, 0),
    (51, 'CSU-GRAD-FOLDER-01', 501, '毕业合影收纳夹', '校园文创课程样品。设计主题为毕业合影收纳夹。', '校园文创课程样品。设计主题为毕业合影收纳夹。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 19.90, 16, 'ON_SALE', 510, 0),
    (52, 'CSU-GRAD-BOOKMARK-01', 501, '毕业季书签', '校园文创课程样品。设计主题为毕业季书签。', '校园文创课程样品。设计主题为毕业季书签。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 9.90, 20, 'ON_SALE', 520, 0),
    (53, 'CSU-GRAD-MEMO-01', 501, '毕业季纪念便签', '校园文创课程样品。设计主题为毕业季纪念便签。', '校园文创课程样品。设计主题为毕业季纪念便签。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 12.90, 16, 'ON_SALE', 530, 0),
    (54, 'CSU-GRAD-NOTE-02', 501, '毕业季回忆册', '下架示例。', '下架示例。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 29.90, 13, 'DRAFT', 540, 0),
    (55, 'CSU-GRAD-KEY-01', 502, '毕业帽钥匙扣', '独立 SKU。作为礼盒成分另行销售时使用自身库存。', '独立 SKU。作为礼盒成分另行销售时使用自身库存。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 12.00, 29, 'ON_SALE', 550, 0),
    (56, 'CSU-GRAD-BOX-01', 502, '中南毕业纪念礼盒', '成品礼盒含潇湘校区地标明信片套装、毕业徽章和毕业帽钥匙扣。按盒定价、按盒计库存。', '成品礼盒含潇湘校区地标明信片套装、毕业徽章和毕业帽钥匙扣。按盒定价、按盒计库存。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 49.00, 13, 'ON_SALE', 560, 0),
    (57, 'CSU-GRAD-PIN-01', 502, '毕业徽章', '独立 SKU。作为礼盒成分另行销售时使用自身库存。', '独立 SKU。作为礼盒成分另行销售时使用自身库存。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 15.00, 30, 'ON_SALE', 570, 0),
    (58, 'CSU-GRAD-MAGNET-01', 502, '毕业合影主题磁贴', '校园文创课程样品。设计主题为毕业合影主题磁贴。', '校园文创课程样品。设计主题为毕业合影主题磁贴。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 21.00, 18, 'ON_SALE', 580, 0),
    (59, 'CSU-GRAD-STAND-01', 502, '毕业帽亚克力立牌', '校园文创课程样品。设计主题为毕业帽亚克力立牌。', '校园文创课程样品。设计主题为毕业帽亚克力立牌。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 28.00, 11, 'ON_SALE', 590, 0),
    (60, 'CSU-GRAD-STICKER-01', 502, '毕业寄语贴纸套装', '下架示例。', '下架示例。 商品和价格均为教学演示数据。', 'images/catalog-placeholder.svg', 11.90, 10, 'DRAFT', 600, 0);

-- 初始化阶段复用同一张站内教学占位图。两组 SKU 分别准备 4 条和 1 条相册记录，其余用封面回退。
INSERT INTO product_image (product_id, image_path, alt_text, sort_order)
SELECT p.id, p.cover_image, CONCAT(p.name, ' · 教学占位图 ', image_slot.slot_no), image_slot.slot_no * 10
FROM product p
CROSS JOIN (SELECT 1 AS slot_no UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) AS image_slot
WHERE p.sku IN (
    'CSU-LMK-NOTE-01', 'CSU-LMK-BOOKMARK-01', 'CSU-LMK-MAGNET-01', 'CSU-LMK-CARDS-01',
    'CSU-COL-MEMO-01', 'CSU-COL-NOTE-01', 'CSU-COL-PIN-01', 'CSU-COL-STAND-01',
    'CSU-CLB-FOLDER-01', 'CSU-CLB-NOTE-01', 'CSU-CLB-KEY-01', 'CSU-CLB-PIN-01',
    'CSU-SPT-NOTE-01', 'CSU-SPT-CASE-01', 'CSU-SPT-PIN-01', 'CSU-SPT-KEY-01',
    'CSU-GRAD-NOTE-01', 'CSU-GRAD-CARDS-01', 'CSU-GRAD-KEY-01', 'CSU-GRAD-BOX-01'
)
ORDER BY p.id, image_slot.slot_no;

INSERT INTO product_image (product_id, image_path, alt_text, sort_order)
SELECT p.id, p.cover_image, CONCAT(p.name, ' · 教学占位图'), 10
FROM product p
WHERE p.sku IN (
    'CSU-LMK-FOLDER-01', 'CSU-LMK-TABS-01', 'CSU-LMK-KEY-01', 'CSU-LMK-PIN-01',
    'CSU-COL-SKETCH-01', 'CSU-COL-BOOKMARK-01', 'CSU-COL-MAGNET-01', 'CSU-COL-KEY-01',
    'CSU-CLB-NOTE-02', 'CSU-CLB-MEMO-01', 'CSU-CLB-CARDS-01', 'CSU-CLB-STICKER-01',
    'CSU-SPT-MEMO-01', 'CSU-SPT-NOTE-02', 'CSU-SPT-MAGNET-01', 'CSU-SPT-CARDS-01',
    'CSU-GRAD-FOLDER-01', 'CSU-GRAD-BOOKMARK-01', 'CSU-GRAD-PIN-01', 'CSU-GRAD-MAGNET-01'
)
ORDER BY p.id;

-- ===== 交易演示数据开始 =====
-- alice、bob 各有五张历史订单，每单两条明细，覆盖五种状态。
-- 临时表只在当前连接可见，临时表建表不会隐式提交演示数据事务。
CREATE TEMPORARY TABLE _csucampuscraft_demo_orders (
    order_no VARCHAR(40) PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    status VARCHAR(16) NOT NULL,
    age_hours INTEGER NOT NULL,
    receiver_name VARCHAR(50) NOT NULL,
    receiver_phone VARCHAR(30) NOT NULL,
    receiver_address VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;

CREATE TEMPORARY TABLE _csucampuscraft_demo_items (
    order_no VARCHAR(40) NOT NULL,
    sku VARCHAR(40) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (order_no, sku)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;

CREATE TEMPORARY TABLE _csucampuscraft_demo_cart (
    username VARCHAR(50) NOT NULL,
    sku VARCHAR(40) NOT NULL,
    quantity INTEGER NOT NULL,
    PRIMARY KEY (username, sku)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;

INSERT INTO _csucampuscraft_demo_orders
    (order_no, username, status, age_hours, receiver_name, receiver_phone, receiver_address)
VALUES
    ('DEMO-202611-AL-01', 'alice', 'PENDING_PAYMENT', 1, '林同学', '13800000001', '课程测试地址 A'),
    ('DEMO-202611-AL-02', 'alice', 'PAID', 25, '林同学', '13800000001', '课程测试地址 A'),
    ('DEMO-202611-AL-03', 'alice', 'SHIPPED', 72, '林同学', '13800000001', '课程测试地址 A'),
    ('DEMO-202611-AL-04', 'alice', 'COMPLETED', 168, '林同学', '13800000001', '课程测试地址 A'),
    ('DEMO-202611-AL-05', 'alice', 'CANCELLED', 48, '林同学', '13800000001', '课程测试地址 A'),
    ('DEMO-202611-BO-01', 'bob', 'PENDING_PAYMENT', 2, '陈同学', '13800000002', '课程测试地址 B'),
    ('DEMO-202611-BO-02', 'bob', 'PAID', 49, '陈同学', '13800000002', '课程测试地址 B'),
    ('DEMO-202611-BO-03', 'bob', 'SHIPPED', 96, '陈同学', '13800000002', '课程测试地址 B'),
    ('DEMO-202611-BO-04', 'bob', 'COMPLETED', 192, '陈同学', '13800000002', '课程测试地址 B'),
    ('DEMO-202611-BO-05', 'bob', 'CANCELLED', 24, '陈同学', '13800000002', '课程测试地址 B');
INSERT INTO _csucampuscraft_demo_items (order_no, sku, quantity, unit_price) VALUES
    ('DEMO-202611-AL-01', 'CSU-COL-MEMO-01', 2, 12.80),
    ('DEMO-202611-AL-01', 'CSU-GRAD-BOX-01', 1, 49.00),
    ('DEMO-202611-AL-02', 'CSU-LMK-MAGNET-01', 1, 24.00),
    ('DEMO-202611-AL-02', 'CSU-CLB-NOTE-01', 1, 21.00),
    ('DEMO-202611-AL-03', 'CSU-COL-NOTE-01', 2, 25.00),
    ('DEMO-202611-AL-03', 'CSU-COL-PIN-01', 1, 16.00),
    ('DEMO-202611-AL-04', 'CSU-SPT-NOTE-01', 2, 17.00),
    ('DEMO-202611-AL-04', 'CSU-SPT-KEY-01', 1, 15.00),
    ('DEMO-202611-AL-05', 'CSU-CLB-PIN-01', 1, 15.00),
    ('DEMO-202611-AL-05', 'CSU-LMK-CARDS-01', 2, 19.90),
    ('DEMO-202611-BO-01', 'CSU-GRAD-NOTE-01', 2, 25.00),
    ('DEMO-202611-BO-01', 'CSU-CLB-KEY-01', 1, 14.00),
    ('DEMO-202611-BO-02', 'CSU-COL-STAND-01', 1, 29.90),
    ('DEMO-202611-BO-02', 'CSU-LMK-BOOKMARK-01', 2, 8.00),
    ('DEMO-202611-BO-03', 'CSU-GRAD-KEY-01', 1, 10.00),
    ('DEMO-202611-BO-03', 'CSU-GRAD-CARDS-01', 1, 18.00),
    ('DEMO-202611-BO-04', 'CSU-LMK-CARDS-01', 1, 19.90),
    ('DEMO-202611-BO-04', 'CSU-SPT-PIN-01', 2, 17.00),
    ('DEMO-202611-BO-05', 'CSU-CLB-CARDS-01', 1, 18.00),
    ('DEMO-202611-BO-05', 'CSU-SPT-CASE-01', 1, 24.00);

INSERT INTO _csucampuscraft_demo_cart (username, sku, quantity) VALUES
    ('alice', 'CSU-LMK-NOTE-01', 2),
    ('alice', 'CSU-GRAD-BOX-01', 1),
    ('alice', 'CSU-COL-PEN-01', 2),
    ('alice', 'CSU-CLB-FOLDER-02', 1),
    ('alice', 'CSU-SPT-STAND-01', 1),
    ('alice', 'CSU-COL-NOTE-01', 1),
    ('bob', 'CSU-LMK-CARDS-01', 1),
    ('bob', 'CSU-GRAD-KEY-01', 1),
    ('bob', 'CSU-CLB-NOTE-01', 2),
    ('bob', 'CSU-SPT-PIN-01', 1);

-- 按导入时间生成过去一小时至八天的订单，保留原有状态和时间间隔。
INSERT INTO sales_order
    (order_no, user_id, status, total_amount, receiver_name, receiver_phone, receiver_address,
     created_at, updated_at, payment_method, payment_no, paid_at, cancelled_at, shipped_at, completed_at)
WITH order_created AS (
    SELECT d.*, u.id AS user_id, DATE_SUB(CURRENT_TIMESTAMP(6), INTERVAL d.age_hours HOUR) AS created_at
    FROM _csucampuscraft_demo_orders d
    JOIN store_user u ON u.username = d.username
    WHERE u.role = 'CUSTOMER' AND u.status = 'ENABLED'
), order_timed AS (
    SELECT c.*,
           CASE WHEN status IN ('PAID', 'SHIPPED', 'COMPLETED') THEN created_at + INTERVAL 5 MINUTE END AS paid_at,
           CASE WHEN status = 'CANCELLED' THEN created_at + INTERVAL 15 MINUTE END AS cancelled_at,
           CASE WHEN status IN ('SHIPPED', 'COMPLETED') THEN created_at + INTERVAL 24 HOUR END AS shipped_at,
           CASE WHEN status = 'COMPLETED' THEN created_at + INTERVAL 72 HOUR END AS completed_at
    FROM order_created c
), order_totals AS (
    SELECT order_no, SUM(unit_price * quantity) AS amount
    FROM _csucampuscraft_demo_items
    GROUP BY order_no
)
SELECT d.order_no, d.user_id, d.status, t.amount, d.receiver_name, d.receiver_phone, d.receiver_address,
       d.created_at, COALESCE(d.completed_at, d.shipped_at, d.cancelled_at, d.paid_at, d.created_at),
       CASE WHEN d.paid_at IS NOT NULL THEN 'MOCK' END,
       CASE WHEN d.paid_at IS NOT NULL THEN CONCAT('MOCK-', d.order_no) END,
       d.paid_at, d.cancelled_at, d.shipped_at, d.completed_at
FROM order_timed d
JOIN order_totals t ON t.order_no = d.order_no
ORDER BY d.order_no;

-- 使用种子成交价制作订单快照，保留原有历史价差。
INSERT INTO sales_order_item
    (order_id, product_id, sku_snapshot, product_name_snapshot, cover_image_snapshot,
     unit_price, quantity, line_amount)
SELECT o.id, p.id, p.sku, p.name, p.cover_image, i.unit_price, i.quantity, i.unit_price * i.quantity
FROM _csucampuscraft_demo_items i
JOIN sales_order o ON o.order_no = i.order_no
JOIN product p ON p.sku = i.sku
ORDER BY o.id, p.id;

-- 历史已取消订单对库存的净影响为零。其他种子订单按明细扣库存。
WITH sold AS (
    SELECT i.product_id, SUM(i.quantity) AS quantity
    FROM sales_order_item i
    JOIN sales_order o ON o.id = i.order_id
    WHERE o.status <> 'CANCELLED'
    GROUP BY i.product_id
)
UPDATE product p
JOIN sold s ON p.id = s.product_id
SET p.stock = p.stock - s.quantity, p.version = p.version + 1;

-- 加车不扣库存。保留下架、售罄和加车后库存下降的教学数据。
INSERT INTO cart_item (user_id, product_id, quantity, version)
SELECT u.id, p.id, d.quantity, 0
FROM _csucampuscraft_demo_cart d
JOIN store_user u ON u.username = d.username
JOIN product p ON p.sku = d.sku
ORDER BY u.id, p.id;
-- ===== 交易演示数据结束 =====

-- 用临时唯一键断言行数和金额。若断言不成立，重复键错误会停止批处理。
-- 连接结束时回滚尚未提交的演示数据，已创建的业务表保留。
CREATE TEMPORARY TABLE _csucampuscraft_demo_assert (
    assertion VARCHAR(40) NOT NULL PRIMARY KEY
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;
INSERT INTO _csucampuscraft_demo_assert (assertion)
VALUES ('unexpected-demo-row-count'), ('demo-order-totals-mismatch');

INSERT INTO _csucampuscraft_demo_assert (assertion)
SELECT 'unexpected-demo-row-count'
WHERE (SELECT COUNT(*) FROM store_user) <> 4
   OR (SELECT COUNT(*) FROM category) <> 15
   OR (SELECT COUNT(*) FROM product) <> 60
   OR (SELECT COUNT(*) FROM product_image) <> 100
   OR (SELECT COUNT(*) FROM cart_item) <> 10
   OR (SELECT COUNT(*) FROM sales_order) <> 10
   OR (SELECT COUNT(*) FROM sales_order_item) <> 20;

INSERT INTO _csucampuscraft_demo_assert (assertion)
SELECT 'demo-order-totals-mismatch'
WHERE EXISTS (
    SELECT 1
    FROM sales_order o
    LEFT JOIN sales_order_item i ON i.order_id = o.id
    GROUP BY o.id, o.total_amount
    HAVING COUNT(i.id) <> 2 OR NOT (SUM(i.line_amount) <=> o.total_amount)
);

COMMIT;
DROP TEMPORARY TABLE _csucampuscraft_demo_orders, _csucampuscraft_demo_items,
    _csucampuscraft_demo_cart, _csucampuscraft_demo_assert;

-- 导入后核对：预期 4、15、60、100、10、10、20。
SELECT 'store_user' AS table_name, COUNT(*) AS row_count FROM store_user
UNION ALL SELECT 'category', COUNT(*) FROM category
UNION ALL SELECT 'product', COUNT(*) FROM product
UNION ALL SELECT 'product_image', COUNT(*) FROM product_image
UNION ALL SELECT 'cart_item', COUNT(*) FROM cart_item
UNION ALL SELECT 'sales_order', COUNT(*) FROM sales_order
UNION ALL SELECT 'sales_order_item', COUNT(*) FROM sales_order_item;
-- ===== 演示数据结束 =====
