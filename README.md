# AI 辅助报告评分工具
## 检查权限
**上传评分表和报告，让 AI 找出处、给建议，再由人确认每一项分数。**

ELEC5623 · Group 14 · Track A · 课程项目原型

[看懂界面](docs/看懂这个仓库.md) · [全部文档](docs/README.md) · [English / 技术说明](README_EN.md) · [小组分工](docs/TEAM_DELIVERY.md)

## 它解决什么问题？

批一份十几页的报告，要反复对照评分表、翻找相关段落。这个工具把**评分要求、报告原文、AI 建议和人工决定**放在一起，方便批阅者核对。

例如，评分表要求“说明如何验证方案”，工具会找出报告里讲测试的段落，显示页码，再给出有出处的评分建议。找不到足够依据时，会提示证据不足。

它能帮忙找和整理依据；**最终分数由人决定，目前也没有独立研究证明它比人工更准或更快。**

## 用起来是什么样？

![批阅界面：左边核对报告证据，右边接受、改分或拒绝 AI 建议](docs/img/review_ui_live.png)

*已有演示截图：使用本地模型读取小组自己的 proposal。截图早于当前 `assessment_v4` 提示词，仅用于说明界面；图中分数和耗时不是当前版本的保证。*

1. **选材料**：上传评分表和报告，或选择仓库自带示例。
2. **看建议和出处**：每条评分标准旁边都有相关原文、位置和 AI 解释。
3. **自己决定**：接受建议、修改分数，或拒绝建议。检查不合格的 AI 分数不能直接接受。
4. **导出记录**：每项都处理后，下载 JSON 或 CSV；AI 原分和人工决定分别保留。

<details>
<summary>展开看：报告原文和出处怎样显示</summary>

![证据展示：每段带编号、页码和所在章节，方便与 AI 解释逐项核对](docs/img/review_ui_evidence.png)

`E-008` 这样的编号对应报告中的一段原文。有出处不代表 AI 理解一定正确，批阅者仍需核对。

</details>

## 先跑起来

需要 **Python 3.11 或以上版本**。在终端执行：

```bash
git clone https://github.com/hanzhengyu202305-arch/elec5623-group14-rubric-agent.git
cd elec5623-group14-rubric-agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m streamlit run app/streamlit_app.py
```

Windows 激活虚拟环境时，将 `source .venv/bin/activate` 换成 `.venv\Scripts\Activate.ps1`（PowerShell）。

打开终端显示的本地网址，在左侧 **Example** 选择 `s1_standard (S1 baseline)`，点击 **Run review**。

**默认是 fixture 演示模式**：不需要 API key，也不会调用真实 AI，适合先走通操作。要看真实模型效果，可使用本地 Ollama，或配置托管模型；具体见 [模型配置](README_EN.md#models)。托管模型会把所选内容发往配置的服务。

## 目前做到哪一步？

| 状态 | 人话说明 | 去哪里核对 |
|---|---|---|
| 已实现 | 读取评分表和报告、找原文、生成建议、检查回答、人工改分和导出 | [代码与需求对应表](docs/REQUIREMENTS_TRACEABILITY.md) |
| 已有模型实验 | 本地 Qwen 7B 已在开发数据上运行；包含完整结果和未达标项 | [实验结果解读](docs/EVALUATION_dev_frozen_notes.md) |
| 尚未完成 | 独立人工打分、真实使用者计时、最终测试集评价 | [项目状态](STATUS.md) |

**能跑通，不等于评分已经可靠。** 当前开发数据主要是合成报告；“引用编号存在”只能证明格式与编号检查通过，不能证明引用真的支持结论。模型也未达到所有既定目标。

## 按你想做的事找入口

| 你想做什么 | 从这里开始 |
|---|---|
| 不懂代码，先看懂这个项目 | [中文界面说明](docs/看懂这个仓库.md) |
| 看实验做了什么、结果如何 | [结果解读](docs/EVALUATION_dev_frozen_notes.md) |
| 准备报告和展示 | [报告草稿](docs/FINAL_REPORT_DRAFT.md) · [演示讲稿](docs/DEMO_SCRIPT.md) |
| 找自己的小组任务 | [分工与交付](docs/TEAM_DELIVERY.md) |
| 修改代码或运行测试 | [技术说明](README_EN.md) · [贡献指南](CONTRIBUTING.md) |
| 查某份文档 | [文档导航](docs/README.md) |

## 文件夹不用全看

| 目录 | 放什么 |
|---|---|
| [`app/`](app/) | 你实际操作的网页界面 |
| [`src/rubric_agent/`](src/rubric_agent/) | 读取材料、找证据、调用模型和检查结果的程序 |
| [`prompts/`](prompts/) | 给 AI 的指令，当前评分用 `assessment_v4` |
| [`dataset/`](dataset/) | 合成测试材料，以及去掉封面的本组 proposal 示例 |
| [`tests/`](tests/) | 检查程序是否正常工作的自动测试 |
| [`docs/`](docs/) | 设计、实验、报告和协作说明 |

项目固定的实验配置见 [Freeze record](docs/FREEZE.md)；AI 辅助开发记录见 [AI_USE.md](AI_USE.md)。
