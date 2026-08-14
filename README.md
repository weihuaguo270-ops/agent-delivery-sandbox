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

冻结数据集见 [`dataset/manifest.json`](dataset/manifest.json)，批量入口为
[`run_delivery_experiment.py`](run_delivery_experiment.py)。运行产物默认不提交仓库。

## 审批控制面

```powershell
$env:AGENT_DELIVERY_API_TOKEN = "<random-token>"
python -m sandbox_service.control_plane --port 8780
```

- `GET /health`、`GET /ready`：健康与就绪探针
- `GET /v1/evidence`：Bearer 保护的实验摘要
- `POST /v1/approvals`：记录绑定计划指纹的批准或拒绝事件

服务为每个请求返回 `X-Request-Id`，访问日志采用 JSON 行格式；Authorization 不进入日志或审计文件。该服务是单租户沙箱控制面，不是 OAuth 或企业多租户网关。

## 故障回流

```powershell
$env:PYTHONPATH = "../react-agent/src"
python run_fault_injection.py --artifact-dir ../test-temp/agent-delivery-fault-v1
```

该用例故意只修改运行策略、不修改业务契约。测试必须失败，运行器必须阻止外部写入，`trace-debugger` 应标记 `acceptance_failed`，`llm-eval-engine` 应给出 `hold`。
Controlled GitHub sandbox for Agent delivery workflow evidence
