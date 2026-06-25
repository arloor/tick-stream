## 工具以及环境准备

| 工具/环境 | 安装/准备方式 | 用途 |
| --- | --- | --- |
| 东财量化终端 | 欢欢电脑上有了，开机并且打开该软件即可。终端的地址是 : `192.168.5.127:7001` ,token是`1567bc4c3beab58c5e0e7700fd5b858b1d36ab80` , strategy_id是 `bdac40a3-2dcf-11f1-ae78-845c3113be70` 。未来需要使用的时候可以到这里找，然后发送给AI | AI生成的的代码需要连接到这个终端，来查询市场信息以及交易 |
| GM SDK | `python.exe -m pip install gm -U -i https://mirrors.aliyun.com/pypi/simple/` ；需要python 3.12 | AI使用这个SDK来和东财量化终端交互，调用量化终端的查询、交易能力 |

## 使用指南

快速开始的例子见[快速开始 - 掘金量化](https://www.myquant.cn/docs2/sdk/python/%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B.html#%E6%95%B0%E6%8D%AE%E4%BA%8B%E4%BB%B6%E9%A9%B1%E5%8A%A8%E7%A4%BA%E4%BE%8B)

### 常用API如下

| API | 官方用途说明 | 我的用法和用途 | 官方文档链接 |
| --- | --- | --- | --- |
| set_token | 设置访问 token，让脱离 `run` 的数据查询或交易调用具备身份鉴权。 | 找量化股扫描脚本和 quant 网关在初始化会话时先设置 token，保证后续行情、基础数据、账户和交易接口可访问。 | [set_token](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E5%85%B6%E4%BB%96%E5%87%BD%E6%95%B0.html#set-token-%E8%AE%BE%E7%BD%AE-token) |
| set_serv_addr | 指定本机 SDK 连接的掘金终端服务地址。官方 docs2 未找到该函数独立锚点，`run` 的参数说明中包含 `serv_addr`。 | 找量化股用于连接远端/Windows 掘金终端；quant 网关也按会话配置显式设置终端地址，避免默认地址不一致。 |  |
| set_account_id | 指定当前交易账户，供后续交易查询、下单和撤单使用。 | quant 网关在会话初始化时绑定账户，并在查资金、查持仓、下单、撤单时继续显式传入或校验该账户。 |  |
| get_trading_dates | 查询指定交易所、日期区间内的交易日列表。 | 找量化股用于推断最近扫描日和上一交易日，避免把自然日误当交易日。 | [get_trading_dates](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E8%80%81%E7%89%88%E6%9C%AC%E6%95%B0%E6%8D%AE%E5%87%BD%E6%95%B0.html#get-trading-dates-%E6%9F%A5%E8%AF%A2%E4%BA%A4%E6%98%93%E6%97%A5%E5%88%97%E8%A1%A8) |
| get_previous_n_trading_dates | 查询指定日期之前的 N 个交易日。 | quant 网关用于 MA/止盈止损等历史窗口计算，按交易日回溯而不是按自然日回溯。 | [get_previous_n_trading_dates](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E9%80%9A%E7%94%A8%E6%95%B0%E6%8D%AE%E5%87%BD%E6%95%B0%EF%BC%88%E5%85%8D%E8%B4%B9%EF%BC%89.html#get-previous-n-trading-dates-%E6%9F%A5%E8%AF%A2%E6%8C%87%E5%AE%9A%E6%97%A5%E6%9C%9F%E7%9A%84%E5%89%8Dn%E4%B8%AA%E4%BA%A4%E6%98%93%E6%97%A5) |
| get_symbol_infos | 查询标的基础信息，例如代码、交易所、证券类型、上市/退市日期等。 | 找量化股用它构建沪深 A 股股票池并过滤非目标标的；quant 网关用它维护代码名称缓存、补全展示信息并过滤已退市标的。 | [get_symbol_infos](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E9%80%9A%E7%94%A8%E6%95%B0%E6%8D%AE%E5%87%BD%E6%95%B0%EF%BC%88%E5%85%8D%E8%B4%B9%EF%BC%89.html#get-symbol-infos-%E6%9F%A5%E8%AF%A2%E6%A0%87%E7%9A%84%E5%9F%BA%E6%9C%AC%E4%BF%A1%E6%81%AF) |
| history | 查询指定标的、周期和时间范围内的历史行情，支持 tick、分钟线、日线等频率。 | 找量化股拉取当日 tick、指数 60 秒线和日线，用于分钟成交量重建、候选筛选和图表；quant 网关用日线复权数据计算均线和交易判断。 | [history](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E8%A1%8C%E6%83%85%E6%95%B0%E6%8D%AE%E6%9F%A5%E8%AF%A2%E5%87%BD%E6%95%B0%EF%BC%88%E5%85%8D%E8%B4%B9%EF%BC%89.html#history-%E6%9F%A5%E8%AF%A2%E5%8E%86%E5%8F%B2%E8%A1%8C%E6%83%85) |
| current / current_price | 查询当前最新行情快照或最新价。官方 docs2 当前有 `current_price` 独立锚点，quant 代码实际调用 SDK 的 `current(...)` 快照接口。 | quant 网关用于实时价格、盘口报价、集合竞价窗口价格和 MA5 止盈止损计算。 | [current_price](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E8%A1%8C%E6%83%85%E6%95%B0%E6%8D%AE%E6%9F%A5%E8%AF%A2%E5%87%BD%E6%95%B0%EF%BC%88%E5%85%8D%E8%B4%B9%EF%BC%89.html#current-price-%E6%9F%A5%E8%AF%A2%E5%BD%93%E5%89%8D%E6%9C%80%E6%96%B0%E4%BB%B7) |
| context.data | 在策略回调中读取已订阅数据的本地滑窗。 | quant demo 在 `on_tick` / `on_bar` 中读取订阅后的 tick、60 秒线或日线窗口，用于策略验证和事件驱动计算。 | [context.data](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E8%A1%8C%E6%83%85%E6%95%B0%E6%8D%AE%E6%9F%A5%E8%AF%A2%E5%87%BD%E6%95%B0%EF%BC%88%E5%85%8D%E8%B4%B9%EF%BC%89.html#context-data-%E6%9F%A5%E8%AF%A2%E8%AE%A2%E9%98%85%E6%95%B0%E6%8D%AE) |
| get_history_symbol | 查询指定标的多日交易信息，包含交易日属性、涨跌停价等字段。 | 找量化股用它补齐扫描日的涨跌停价、昨收和日度属性，过滤触及涨跌停的候选；quant 网关用它获取涨跌停价和历史标的信息。 | [get_history_symbol](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E9%80%9A%E7%94%A8%E6%95%B0%E6%8D%AE%E5%87%BD%E6%95%B0%EF%BC%88%E5%85%8D%E8%B4%B9%EF%BC%89.html#get-history-symbol-%E6%9F%A5%E8%AF%A2%E6%8C%87%E5%AE%9A%E6%A0%87%E7%9A%84%E5%A4%9A%E6%97%A5%E4%BA%A4%E6%98%93%E4%BF%A1%E6%81%AF) |
| stk_get_daily_mktvalue_pt | 查询多标的某交易日的市值指标截面数据。 | 找量化股按批次拉取 `tot_mv`，用于股票池市值过滤、候选规模控制和报告展示。 | [stk_get_daily_mktvalue_pt](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E8%82%A1%E7%A5%A8%E8%B4%A2%E5%8A%A1%E6%95%B0%E6%8D%AE%E5%8F%8A%E5%9F%BA%E7%A1%80%E6%95%B0%E6%8D%AE%E5%87%BD%E6%95%B0%EF%BC%88%E5%85%8D%E8%B4%B9%EF%BC%89.html#stk-get-daily-mktvalue-pt-%E6%9F%A5%E8%AF%A2%E5%B8%82%E5%80%BC%E6%8C%87%E6%A0%87%E5%8D%95%E6%97%A5%E6%88%AA%E9%9D%A2%E6%95%B0%E6%8D%AE-%E5%A4%9A%E6%A0%87%E7%9A%84) |
| stk_get_symbol_industry | 查询股票所属行业。 | 找量化股按证监会行业口径拉取一级行业，用于候选报告的行业标签、分组展示和后续分析。 | [stk_get_symbol_industry](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E8%82%A1%E7%A5%A8%E5%A2%9E%E5%80%BC%E6%95%B0%E6%8D%AE%E5%87%BD%E6%95%B0%EF%BC%88%E4%BB%98%E8%B4%B9%EF%BC%89.html#stk-get-symbol-industry-%E6%9F%A5%E8%AF%A2%E8%82%A1%E7%A5%A8%E7%9A%84%E6%89%80%E5%B1%9E%E8%A1%8C%E4%B8%9A) |
| stk_get_fundamentals_balance | 查询单标的指定时间段内的资产负债表数据。 | quant demo 用于验证财务字段读取，按字段拉取上汽集团资产负债表核心科目。 | [stk_get_fundamentals_balance](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E8%82%A1%E7%A5%A8%E8%B4%A2%E5%8A%A1%E6%95%B0%E6%8D%AE%E5%8F%8A%E5%9F%BA%E7%A1%80%E6%95%B0%E6%8D%AE%E5%87%BD%E6%95%B0%EF%BC%88%E5%85%8D%E8%B4%B9%EF%BC%89.html#stk-get-fundamentals-balance-%E6%9F%A5%E8%AF%A2%E8%B5%84%E4%BA%A7%E8%B4%9F%E5%80%BA%E8%A1%A8%E6%95%B0%E6%8D%AE) |
| subscribe | 订阅行情数据，SDK 后续通过事件回调和 `context.data` 提供订阅数据。 | quant demo 订阅 tick、60 秒线和日线，驱动 `on_tick` / `on_bar` 策略逻辑。 | [subscribe](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E6%95%B0%E6%8D%AE%E8%AE%A2%E9%98%85.html#subscribe-%E8%A1%8C%E6%83%85%E8%AE%A2%E9%98%85) |
| schedule | 注册策略定时任务。 | quant 网关/策略层用于在固定日期规则和时间规则下执行选股、风控、同步或交易动作。 | [schedule](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E5%9F%BA%E6%9C%AC%E5%87%BD%E6%95%B0.html#schedule-%E5%AE%9A%E6%97%B6%E4%BB%BB%E5%8A%A1%E9%85%8D%E7%BD%AE) |
| run | 启动策略运行入口，配置策略 ID、文件名、运行模式、token、回测参数和终端地址等。 | quant demo 用它启动实时/回测策略；网关侧则避开 `run` 的阻塞主循环，改为手动初始化策略上下文。 | [run](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E5%9F%BA%E6%9C%AC%E5%87%BD%E6%95%B0.html#run-%E8%BF%90%E8%A1%8C%E7%AD%96%E7%95%A5) |
| get_cash | 查询指定交易账户资金信息。 | quant 网关用于健康检查、账户可访问性验证、可用资金展示和下单前风控。 | [get_cash](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E6%9F%A5%E8%AF%A2%E5%87%BD%E6%95%B0.html#get-cash-%E6%9F%A5%E8%AF%A2%E6%8C%87%E5%AE%9A%E4%BA%A4%E6%98%93%E8%B4%A6%E6%88%B7%E7%9A%84%E8%B5%84%E9%87%91%E4%BF%A1%E6%81%AF) |
| get_position | 查询指定交易账户全部持仓信息。 | quant 网关用于持仓列表、卖出数量校验、仓位决策和风控检查。 | [get_position](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E6%9F%A5%E8%AF%A2%E5%87%BD%E6%95%B0.html#get-position-%E6%9F%A5%E8%AF%A2%E6%8C%87%E5%AE%9A%E4%BA%A4%E6%98%93%E8%B4%A6%E6%88%B7%E7%9A%84%E5%85%A8%E9%83%A8%E6%8C%81%E4%BB%93%E4%BF%A1%E6%81%AF) |
| get_orders | 查询日内全部委托。 | quant 网关在策略上下文已初始化时读取日内委托，并按当前 account_id 过滤后输出给 CLI/服务端。 | [get_orders](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E5%87%BD%E6%95%B0.html#get-orders-%E6%9F%A5%E8%AF%A2%E6%97%A5%E5%86%85%E5%85%A8%E9%83%A8%E5%A7%94%E6%89%98) |
| get_unfinished_orders | 查询日内全部未结委托。 | quant 网关用于识别挂单、展示未完成订单，并支持后续撤单逻辑。 | [get_unfinished_orders](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E5%87%BD%E6%95%B0.html#get-unfinished-orders-%E6%9F%A5%E8%AF%A2%E6%97%A5%E5%86%85%E5%85%A8%E9%83%A8%E6%9C%AA%E7%BB%93%E5%A7%94%E6%89%98) |
| get_execution_reports | 查询日内全部执行回报。 | quant 网关用于成交回报同步、成交明细查询和交易结果审计。 | [get_execution_reports](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E5%87%BD%E6%95%B0.html#get-execution-reports-%E6%9F%A5%E8%AF%A2%E6%97%A5%E5%86%85%E5%85%A8%E9%83%A8%E6%89%A7%E8%A1%8C%E5%9B%9E%E6%8A%A5) |
| order_volume | 按指定数量委托。 | quant 网关的常规买卖主接口之一，CLI 的按股数买入/卖出最终映射到该接口。 | [order_volume](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E5%87%BD%E6%95%B0.html#order-volume-%E6%8C%89%E6%8C%87%E5%AE%9A%E9%87%8F%E5%A7%94%E6%89%98) |
| order_value | 按指定金额委托。 | quant 网关在按金额建仓或调仓时使用，由 SDK 根据金额、价格和交易单位计算委托数量。 | [order_value](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E5%87%BD%E6%95%B0.html#order-value-%E6%8C%89%E6%8C%87%E5%AE%9A%E4%BB%B7%E5%80%BC%E5%A7%94%E6%89%98) |
| order_cancel | 撤销指定委托。 | quant 网关根据 `cl_ord_id` 和账户构造待撤单对象，用于手动撤单或超时/风控触发撤单。 | [order_cancel](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E5%87%BD%E6%95%B0.html#order-cancel-%E6%92%A4%E9%94%80%E5%A7%94%E6%89%98) |
| context.account().cash | 在策略上下文中查询当前账户资金。 | quant demo 用 `context.account()` 读取账户对象；生产网关更偏向直接调用 `get_cash(account_id)`，减少对策略回调上下文的依赖。 | [context.account().cash](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E6%9F%A5%E8%AF%A2%E5%87%BD%E6%95%B0.html#context-account-cash-%E6%9F%A5%E8%AF%A2%E5%BD%93%E5%89%8D%E8%B4%A6%E6%88%B7%E8%B5%84%E9%87%91) |
| context.account().positions() | 在策略上下文中查询当前账户全部持仓。 | quant demo 用于查看账户持仓；生产网关主要通过 `get_position(account_id)` 做独立查询。 | [context.account().positions()](https://www.myquant.cn/docs2/sdk/python/API%E4%BB%8B%E7%BB%8D/%E4%BA%A4%E6%98%93%E6%9F%A5%E8%AF%A2%E5%87%BD%E6%95%B0.html#context-account-positions-%E6%9F%A5%E8%AF%A2%E5%BD%93%E5%89%8D%E8%B4%A6%E6%88%B7%E5%85%A8%E9%83%A8%E6%8C%81%E4%BB%93) |

### **内部接口（gm.api.basic / gm.csdk）**

> 这些是当前项目为绕开 `run` 阻塞、手动初始化实时策略上下文而使用的底层接口。官方 docs2 主要记录对外公开 API；未找到独立官方锚点的内部函数不填写链接。
> 

| API | 官方用途说明 | 我的用法和用途 | 官方文档链接 |
| --- | --- | --- | --- |
| py_gmi_set_strategy_id | SDK 底层策略 ID 设置函数，未在官方 docs2 公开 API 中找到独立说明。 | 找量化股可选设置 strategy_id；quant 网关在手动 bootstrap 策略上下文时设置策略 ID，让账户、订单和事件链路归属到指定策略。 |  |
| gmi_set_mode | SDK 底层运行模式设置函数，未在官方 docs2 公开 API 中找到独立说明。 | quant 网关把底层模式设置为 `MODE_LIVE`，并同步 `basic.context.mode`，用于实盘/仿真事件链路。 |  |
| py_gmi_set_data_callback | SDK 底层数据/事件回调注册函数，未在官方 docs2 公开 API 中找到独立说明。 | quant 网关注册 `basic.callback_controller`，让订单、成交、账户状态等事件能进入 SDK 回调控制器。 |  |
| gmi_init | SDK 底层初始化函数，未在官方 docs2 公开 API 中找到独立说明。 | quant 网关在设置 token、账户、策略 ID、模式和回调后手动初始化 gm 运行时。 |  |
| check_gm_status | SDK 底层状态检查函数，未在官方 docs2 公开 API 中找到独立说明。 | quant 网关在 `gmi_init()` 后检查初始化状态，将失败转换成统一的 GatewayError。 |  |
| gmi_poll | SDK 底层事件轮询函数，未在官方 docs2 公开 API 中找到独立说明。 | quant 网关在线程中持续轮询事件，替代 `run(...)` 的阻塞主循环；仓库说明里也记录了它可能长期持有 GIL 的风险。 |  |
