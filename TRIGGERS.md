# JsonTriggerService 5 分钟手册

## 1. 一条触发器长啥样  
| 字段   | 说明                     | 示例值        |
|--------|--------------------------|---------------|
| on     | 事件名（中文）           | "悄悄话"      |
| when   | 字段过滤器               | {"sender":"Alice"} |
| do.cmd | 要执行的 **Fluent 命令** | "pay"         |
| do.args| 构造器参数               | {"amount":100} |
| do.chain| 链式调用列表            | [["transfer_to","Alice"]] |

## 2. 过滤器支持  
- 精确值：`{"sender": "Alice"}`  
- 列表：`{"sender": ["Alice", "Bob"]}`  
- 正则：`{"text": "re:.*hello.*"}`  

## 3. 可用命令（v1）  
| cmd | 作用 | 必传 args | 链式方法 |
|-----|------|-----------|----------|
| chat | 公屏说话 | content | .sendto(player) / .interval(sec) |
| pay | 转账 | amount | .transfer_to(player) |
| land | 领地操作 | 无 | .handle_invite().accept() / .deposit(val) |
| jump | 原地跳 | 无 | .times(n).interval(sec) |

## 5. 调试  
exe 同目录的 `logs/runtime_*.log` 里搜  
`JsonTriggerService` 能看到命中记录。