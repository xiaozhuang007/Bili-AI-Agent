# shared/ 使用说明

**通用共享目录**：任何想给 Agent 读的文件都可以放在这里。

## 和 cookie_imports/ 的区别

| 目录 | 用途 |
|------|------|
| `cookie_imports/` | 专用：Cookie 文件检测/转换（Agent 按文件名在这里找 cookie） |
| `shared/` | 通用：任意文件（配置、文档、数据……想给 Agent 看就丢这里） |

## 怎么用？

1. 把文件放到本目录，例如 `notes.txt`
2. 告诉 Agent：`帮我读一下 shared 目录里的 notes.txt`
   （Agent 的 read_file 工具支持 directory 参数：cookie_imports / shared / downloads）

## 安全边界

Agent 只能读白名单目录（本目录 / cookie_imports / downloads），
**读不到** backend 代码、.env（含 API Key）等你没挂载的位置。
想开放更多目录？改 docker-compose.yml 加一行挂载 + config.py 的 READABLE_DIRS 登记即可。
