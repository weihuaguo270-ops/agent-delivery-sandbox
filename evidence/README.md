# 真实交付实验（2026-08-14）

本目录保存可公开核验的摘要。完整运行轨迹保留在本地实验产物目录，摘要通过 SHA-256 与原始结果绑定。

## 结果

| 阶段 | 结果 |
|------|------|
| 数据集 | 24 个真实 GitHub Issue：dev 6 / golden 10 / held-out 8 |
| Shadow | 24/24 通过；无外部写入；P95 606.258 ms |
| Guarded | 4/4 创建真实 Draft PR；P95 8457.034 ms |
| 人工评审 | 2 接受、1 拒绝、1 待处理；已完成样本接受率 66.67% |
| 回滚 | PR #27 合并后由 PR #29 回滚，CI 通过 |
| trace-debugger | 24 条轨迹扫描，无启发式失败；沙箱项目健康机制未接入 |
| llm-eval-engine | 基础业务终态门禁通过；综合门禁 `hold` |

综合门禁保持 `hold` 是预期结果：PR #26 被人工拒绝，PR #28 仍待评审，并且没有测量人工执行基线。不能用脚本结果代替真实人工基线。

## 可核验链接

- 接受并合并：[PR #25](https://github.com/weihuaguo270-ops/agent-delivery-sandbox/pull/25)
- 人工拒绝并清理分支：[PR #26](https://github.com/weihuaguo270-ops/agent-delivery-sandbox/pull/26)
- 合并后回滚：[PR #27](https://github.com/weihuaguo270-ops/agent-delivery-sandbox/pull/27) -> [PR #29](https://github.com/weihuaguo270-ops/agent-delivery-sandbox/pull/29)
- 保持待处理：[PR #28](https://github.com/weihuaguo270-ops/agent-delivery-sandbox/pull/28)

## 边界

证据等级为 `external_real_sandbox`：GitHub Issue、分支、PR、CI、关闭和回滚都是真实外部操作，但任务和数据是合成的，没有生产用户、真实业务流量或付费模型调用。
