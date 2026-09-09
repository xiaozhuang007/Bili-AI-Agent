# cookie_imports/ 使用说明

把**从浏览器导出的 Cookie 文件**放在这里，然后告诉 Agent 文件名即可。

## 为什么需要这个目录？

Agent 运行在 Docker 容器里（独立"迷你电脑"），**访问不到你 Windows 硬盘上的任意路径**。
这个目录通过 docker-compose 挂载进容器（`./cookie_imports:/app/cookie_imports`），
是"你放文件 → Agent 读文件"的唯一通道。

## 怎么用？

1. 用浏览器扩展导出 Cookie 文件（Netscape / 浏览器字符串 / JSON 格式都行）
2. 把文件放到本目录，例如 `cookies.txt`
3. 在对话框里告诉 Agent：`帮我检测一下 cookies.txt`
   - Agent 会报告：格式 / 关键字段 / 过期时间 / 实测登录态
4. 想让下载立刻用它：让 Agent 转换
   - Agent 会：转成 Netscape → 本目录存一份 `<原名>_netscape.txt` 副本
     → 同时设为当前生效 Cookie（项目根目录 `cookie.txt`）

## 注意事项

- 你的原始文件**永远不会被修改/覆盖**
- 文件名不要带路径和特殊字符（Agent 只按纯文件名查找）
- Cookie 有效期通常只有 1~2 天，过期后重新导出即可
- 本目录含敏感凭据，已加入 .gitignore，不会上传 GitHub
