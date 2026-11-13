# STEP03 截图视觉复核

受测提交：ad43f8f213d858b2d7b15b0676ed2e438051ebb2。覆盖 attempt3 62张与 supplement-home-states 4张；补充使用同JAR及运行输入指纹。

结论：66/66原始截图已逐张打开查看，未发现阻断验收的排版、文本溢出、遮挡或状态缺失。两种桌面视口1366×768和1920×1080均覆盖；截图采用完整页面，高度可能超过视口高度。

逐图精确路径、SHA256、视口、HTTP记录状态与观察见 [final-step03.json](final-step03.json)。evidence_path 为相对证据归档根路径。基础62张独立记录仍保留于 final-attempt3.json；补充4张记录为 supplement-home-states.json。

本复核是 AI 辅助截图审阅，不替代组员交叉复核；SQL、HTTP、URL保留以实测记录为依据。手机、读屏器和手工键盘遍历不在本次范围。

| 截图 | 结论 | 观察 |
| --- | --- | --- |
| attempt3/browser/demo/combined-1366.png | PASS | 毕业主题、文具、毕业关键词、价格升序和size=2同时回显；9.90/12.90两件及总5件/3页可见。 |
| attempt3/browser/demo/combined-1920.png | PASS | 毕业主题、文具、毕业关键词、价格升序和size=2同时回显；9.90/12.90两件及总5件/3页可见。 |
| attempt3/browser/demo/draft-1366.png | PASS | 下架商品404页，PRODUCT_NOT_FOUND和返回首页入口可读。 |
| attempt3/browser/demo/draft-1920.png | PASS | 下架商品404页，PRODUCT_NOT_FOUND和返回首页入口可读。 |
| attempt3/browser/demo/gift-box-1366.png | PASS | 礼盒SKU、49.00、库存12、禁用数量/加购与暂未开放提示、四张相册图注完整。 |
| attempt3/browser/demo/gift-box-1920.png | PASS | 礼盒SKU、49.00、库存12、禁用数量/加购与暂未开放提示、四张相册图注完整。 |
| attempt3/browser/demo/graduation-all-1366.png | PASS | 毕业主题/全部类型/毕业关键词/size=1回显，第2页、总10件/10页可见。 |
| attempt3/browser/demo/graduation-all-1920.png | PASS | 毕业主题/全部类型/毕业关键词/size=1回显，第2页、总10件/10页可见。 |
| attempt3/browser/demo/graduation-souvenir-1366.png | PASS | 毕业主题/纪念周边/毕业关键词/size=1回显，第2页礼盒49.00/库存12可见。 |
| attempt3/browser/demo/graduation-souvenir-1920.png | PASS | 毕业主题/纪念周边/毕业关键词/size=1回显，第2页礼盒49.00/库存12可见。 |
| attempt3/browser/demo/graduation-stationery-1366.png | PASS | 毕业主题/文具/毕业关键词/size=1回显，第2页、总5件/5页可见。 |
| attempt3/browser/demo/graduation-stationery-1920.png | PASS | 毕业主题/文具/毕业关键词/size=1回显，第2页、总5件/5页可见。 |
| attempt3/browser/demo/home-1366.png | PASS | 首页五个一级主题、新品3件、精选4件、毕业横幅和搜索提示清楚；未见遮挡。 |
| attempt3/browser/demo/home-1920.png | PASS | 首页五个一级主题、新品3件、精选4件、毕业横幅和搜索提示清楚；未见遮挡。 |
| attempt3/browser/demo/invalid-page-1366.png | PASS | 非法页码400页，INVALID_INTEGER与错误摘要可读，无技术堆栈。 |
| attempt3/browser/demo/invalid-page-1920.png | PASS | 非法页码400页，INVALID_INTEGER与错误摘要可读，无技术堆栈。 |
| attempt3/browser/demo/invalid-size-1366.png | PASS | 非法条数400页，INVALID_INTEGER与错误摘要可读，无技术堆栈。 |
| attempt3/browser/demo/invalid-size-1920.png | PASS | 非法条数400页，INVALID_INTEGER与错误摘要可读，无技术堆栈。 |
| attempt3/browser/demo/invalid-sort-1366.png | PASS | 非法排序400页，INVALID_ENUM与错误摘要可读，无技术堆栈。 |
| attempt3/browser/demo/invalid-sort-1920.png | PASS | 非法排序400页，INVALID_ENUM与错误摘要可读，无技术堆栈。 |
| attempt3/browser/demo/invalid-type-1366.png | PASS | 非法类型400页，INVALID_ENUM与错误摘要可读，无技术堆栈。 |
| attempt3/browser/demo/invalid-type-1920.png | PASS | 非法类型400页，INVALID_ENUM与错误摘要可读，无技术堆栈。 |
| attempt3/browser/demo/missing-cover-1366.png | PASS | 缺失封面回退现有占位图，无破图；29.00及库存7可读。 |
| attempt3/browser/demo/missing-cover-1920.png | PASS | 缺失封面回退现有占位图，无破图；29.00及库存7可读。 |
| attempt3/browser/demo/no-album-1366.png | PASS | 无相册提示清楚，仍显示封面；价格、库存和禁用控件可读。 |
| attempt3/browser/demo/no-album-1920.png | PASS | 无相册提示清楚，仍显示封面；价格、库存和禁用控件可读。 |
| attempt3/browser/demo/out-of-range-1366.png | PASS | 极大页码完整显示；超页空态和返回第1页入口清楚，无横向溢出。 |
| attempt3/browser/demo/out-of-range-1920.png | PASS | 极大页码完整显示；超页空态和返回第1页入口清楚，无横向溢出。 |
| attempt3/browser/demo/pagination-1366.png | PASS | 第2页6件、总54件/9页；含售罄商品，上一页/下一页入口清楚。 |
| attempt3/browser/demo/pagination-1920.png | PASS | 第2页6件、总54件/9页；含售罄商品，上一页/下一页入口清楚。 |
| attempt3/browser/demo/products-1366.png | PASS | 共54件、首屏6条、共9页；三列卡片和分页完整可读。 |
| attempt3/browser/demo/products-1920.png | PASS | 共54件、首屏6条、共9页；三列卡片和分页完整可读。 |
| attempt3/browser/demo/secondary-category-1366.png | PASS | 二级分类ID404页，与未知主题呈相同错误口径。 |
| attempt3/browser/demo/secondary-category-1920.png | PASS | 二级分类ID404页，与未知主题呈相同错误口径。 |
| attempt3/browser/demo/sold-out-1366.png | PASS | 售罄与库存0清楚；保留详情说明和封面，无相册提示可见。 |
| attempt3/browser/demo/sold-out-1920.png | PASS | 售罄与库存0清楚；保留详情说明和封面，无相册提示可见。 |
| attempt3/browser/demo/sort-default-1366.png | PASS | 默认排序回显；六件首屏SKU、价格、库存和分页清楚。 |
| attempt3/browser/demo/sort-default-1920.png | PASS | 默认排序回显；六件首屏SKU、价格、库存和分页清楚。 |
| attempt3/browser/demo/sort-newest-1366.png | PASS | 最新排序回显，毕业新品在前，礼盒49.00/库存12清楚。 |
| attempt3/browser/demo/sort-newest-1920.png | PASS | 最新排序回显，毕业新品在前，礼盒49.00/库存12清楚。 |
| attempt3/browser/demo/sort-price_asc-1366.png | PASS | 升序回显，首屏6.90/7.90/8.00/8.80/8.90/9.90符合升序，售罄仍显示。 |
| attempt3/browser/demo/sort-price_asc-1920.png | PASS | 升序回显，首屏6.90/7.90/8.00/8.80/8.90/9.90符合升序，售罄仍显示。 |
| attempt3/browser/demo/sort-price_desc-1366.png | PASS | 降序回显，首屏49.00/32.00/29.90/29.00/28.00/28.00符合降序，缺图有占位。 |
| attempt3/browser/demo/sort-price_desc-1920.png | PASS | 降序回显，首屏49.00/32.00/29.90/29.00/28.00/28.00符合降序，缺图有占位。 |
| attempt3/browser/demo/unknown-category-1366.png | PASS | 未知主题404页，THEME_NOT_FOUND和返回首页入口可读。 |
| attempt3/browser/demo/unknown-category-1920.png | PASS | 未知主题404页，THEME_NOT_FOUND和返回首页入口可读。 |
| attempt3/browser/empty/empty-detail-1366.png | PASS | 空库详情404，PRODUCT_NOT_FOUND及恢复入口清楚。 |
| attempt3/browser/empty/empty-detail-1920.png | PASS | 空库详情404，PRODUCT_NOT_FOUND及恢复入口清楚。 |
| attempt3/browser/empty/empty-home-1366.png | PASS | 空库首页搜索与导航保留；主题及两个商品区分别空态，毕业横幅省略。 |
| attempt3/browser/empty/empty-home-1920.png | PASS | 空库首页搜索与导航保留；主题及两个商品区分别空态，毕业横幅省略。 |
| attempt3/browser/empty/empty-products-1366.png | PASS | 空库共0件，全部筛选控件、空态与清除入口可读。 |
| attempt3/browser/empty/empty-products-1920.png | PASS | 空库共0件，全部筛选控件、空态与清除入口可读。 |
| attempt3/browser/fixtures/escaped-description-1366.png | PASS | script标签在名称、面包屑和说明中按普通文本显示；长名称自然换行，无遮挡。 |
| attempt3/browser/fixtures/escaped-description-1920.png | PASS | script标签在名称、面包屑和说明中按普通文本显示；长名称自然换行，无遮挡。 |
| attempt3/browser/fixtures/literal-backslash-1366.png | PASS | 反斜杠回显，匹配1件测试商品；卡片长文本正常换行。 |
| attempt3/browser/fixtures/literal-backslash-1920.png | PASS | 反斜杠回显，匹配1件测试商品；卡片长文本正常换行。 |
| attempt3/browser/fixtures/literal-percent-1366.png | PASS | 百分号回显，匹配1件测试商品；名称包含script普通文本。 |
| attempt3/browser/fixtures/literal-percent-1920.png | PASS | 百分号回显，匹配1件测试商品；名称包含script普通文本。 |
| attempt3/browser/fixtures/literal-underscore-1366.png | PASS | 下划线回显，匹配1件测试商品；卡片长文本正常换行。 |
| attempt3/browser/fixtures/literal-underscore-1920.png | PASS | 下划线回显，匹配1件测试商品；卡片长文本正常换行。 |
| attempt3/browser/missing-graduation/no-graduation-banner-1366.png | PASS | GRADUATION编码缺失时横幅省略，搜索、其余主题、新品与精选仍正常。 |
| attempt3/browser/missing-graduation/no-graduation-banner-1920.png | PASS | GRADUATION编码缺失时横幅省略，搜索、其余主题、新品与精选仍正常。 |
| supplement-home-states/browser/all-draft-home/all-products-draft-1366.png | PASS | 五个主题与毕业横幅仍在，全部商品DRAFT后新品和精选各自空态；搜索和浏览入口可读。 |
| supplement-home-states/browser/all-draft-home/all-products-draft-1920.png | PASS | 五个主题与毕业横幅仍在，全部商品DRAFT后新品和精选各自空态；搜索和浏览入口可读。 |
| supplement-home-states/browser/sold-out-home/featured-sold-out-1366.png | PASS | 精选首件库存改0后卡片仍展示18.00并明确标售罄；其余主题、横幅、新品和精选排布正常。 |
| supplement-home-states/browser/sold-out-home/featured-sold-out-1920.png | PASS | 精选首件库存改0后卡片仍展示18.00并明确标售罄；其余主题、横幅、新品和精选排布正常。 |
