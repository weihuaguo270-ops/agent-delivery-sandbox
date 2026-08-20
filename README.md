# Agent Delivery Sandbox

用于验证工程 Agent 受控交付闭环的公开沙箱仓库。仓库中的 Issue、策略值和测试均为合成数据，不对应真实生产系统。

每条任务要求同时修改一个策略值和对应契约。基线始终通过全部测试；Agent 必须在隔离克隆中完成修改和验收，经过人工审批后才能创建 Draft PR。

业务证据包括：

- 24 条 GitHub Issue，按 `dev/golden/held-out` 冻结划分
- Shadow 与 guarded 运行报告
- Draft PR 的合并、拒绝关闭和回滚案例
- 任务成功率、人工接管率、PR 接受率和 P95 延迟

## 2026-08-14 实验结论

- 数据集 24 条：dev/golden/held-out = 6/10/8；Shadow 24/24，外部写入 0，P95 606.258 ms。
- guarded 4/4 创建 Draft PR，P95 8457.034 ms；人工接受 3 条、拒绝 1 条。
- PR #25、#28 合并，PR #26 拒绝并关闭；PR #27 合并后由 PR #29 回滚。当前没有待处理 PR。
- 选定发布集 task_01 + task_18 的 `llm-eval-engine` 门禁为 `pass`；全量实验保留拒绝案例，门禁为 `hold`。
- 故障注入在外部写入前被测试拦截，并由 `trace-debugger` 分类为 `acceptance_failed`。

证据等级为 `external_real_sandbox`：GitHub Issue、分支、Draft PR、合并、关闭和回滚操作真实发生，
任务内容与审批决定属于合成实验。尚无生产用户或流量、人工执行耗时基线、真实模型成本、OAuth
和多租户权限证据。其余 20 条 Issue 仅完成 Shadow，不应计为受控写入交付。

**2026-08-20 文档更新：** 控制面、证据契约和故障回流边界已集中说明；selected release
可以为 `pass`，但保留拒绝/回滚的全量 guarded 实验仍应为 `hold`，两者不能合并为一个总分。

冻结证据见 [`evidence/experiment_20260814.json`](evidence/experiment_20260814.json)、
[`evidence/selected_release_20260814.json`](evidence/selected_release_20260814.json) 和
[`evidence/failure_feedback_20260814.json`](evidence/failure_feedback_20260814.json)。

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
