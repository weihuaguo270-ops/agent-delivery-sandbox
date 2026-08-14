# Agent Delivery Sandbox

用于验证工程 Agent 受控交付闭环的公开沙箱仓库。仓库中的 Issue、策略值和测试均为合成数据，不对应真实生产系统。

每条任务要求同时修改一个策略值和对应契约。基线始终通过全部测试；Agent 必须在隔离克隆中完成修改和验收，经过人工审批后才能创建 Draft PR。

业务证据包括：

- 24 条 GitHub Issue，按 `dev/golden/held-out` 冻结划分
- Shadow 与 guarded 运行报告
- Draft PR 的合并、拒绝关闭和回滚案例
- 任务成功率、人工接管率、PR 接受率和 P95 延迟

```bash
python -m pytest -q
```
Controlled GitHub sandbox for Agent delivery workflow evidence
