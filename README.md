# DeepSeen TikTok卖家 Skills

简体中文 | [English](README.en.md)

作者：祥子｜跨境无疆&DeepSeen AI创始人

产品品牌：DeepSeen

当前主要面向TikTok跨境卖家：发现机会、验证商品、制作带货内容，并用实际投放结果复盘。每个环节可独立使用，不强制跑完整套流程。

## 三个专题入口，四个独立Skill

| 产品入口 | 对应Skill | 从哪里开始 |
|---|---|---|
| [DeepSeen 选品参谋](https://github.com/kanehuang168/deepseen-product-advisor) | 选品参谋：商机探测＋商品验证合一 | 没有商品找方向；已有商品直接验证 |
| [DeepSeen 带货创作](https://github.com/kanehuang168/deepseen-commerce-creative) | 剧本导演、成品质检，各自独立 | 确认商品事实与原稿后规划，取得成片再质检 |
| [DeepSeen 投放诊断](https://github.com/kanehuang168/deepseen-ad-diagnosis) | 投流报表诊断与复盘 | 读取自有报表，不混广告归因成交与店铺总成交 |

正式名称保持简洁；“面向TikTok跨境卖家”放在描述、示例和搜索关键词里。选品参谋的两个模式按需选择，不捆绑运行或重复买数据。

实际链路：选品参谋 → 剧本导演 → 实际制作 → 成品质检 → 实际投放 → 投放诊断。没有成片或投放数据时明确停在待输入，不能把方案当出片、报表示例当真实销售。详见[同一商品的交接示例](examples/workflow.md)。

## 独立方法系列

| 产品入口 | 适合解决的问题 |
|---|---|
| [DeepSeen 项目管理](https://github.com/kanehuang168/deepseen-project-manager) | 多步骤工作推进、交接、中断恢复和证据验收 |
| [DeepSeen 深知灼见](https://github.com/kanehuang168/deepseen-shenzhizhuojian) | 复杂决策、反复故障、竞争解释与可逆计划 |
| [DeepSeen 吸星大法](https://github.com/kanehuang168/deepseen-xixing) | 资料理解、小范围试用和证据回归 |

方法系列不限定行业，也不要求电商任务必须经过三个额外步骤。每个入口独立安装，不包含DeepSeen私有控制面、客户案例或隐含费用授权。

## 原有安装兼容

本仓库保留原有三个入口，现有安装链接不失效；后续维护以对应专题仓库为主。初次安装建议选择上面的专题入口，不同时安装相同名称的旧版与新版；迁移时在客户端核对Skill路径和版本，再替换旧版，勿直接删除其他技能。

| 技能 | 输入 | 能直接交付什么 |
|---|---|---|
| [投流报表诊断简版](skills/deepseen-ad-report-lite/SKILL.md) | 自有CSV/XLSX | 本地计算、口径缺口、素材核查建议 |
| [带货剧本与导演简版](skills/deepseen-commerce-director-lite/SKILL.md) | 商品事实、目标、原稿 | 脚本或原稿整理、分镜与验收要求 |
| [成品质检](skills/deepseen-asset-quality-audit/SKILL.md) | 成片、确认要求及实际观察 | 文件技术事实、证据矛盾、需修订或待核验项 |

后两个属于同一制作流程，也可分别使用。质检读取确认要求和最终文件，不以导演自我评价作为通过证据。

## 本地演示

Python 3.10或更新版本，投流计算只使用标准库，不需要DeepSeen账号、密钥或网络。

```sh
python -X utf8 skills/deepseen-ad-report-lite/scripts/diagnose_ads.py skills/deepseen-ad-report-lite/assets/sample-ads.csv --target-roas 2.5 --demo
python -X utf8 -m unittest discover -s tests -v
```

示例数据是虚构的，不是真实客户业绩。脚本不调整投放，也不证明因果或净利润。

导演简版由宿主智能体处理文字，消耗和可用能力以宿主为准；本仓库不会自动调用收费制作。成品质检的技术探测需要PATH中的ffprobe和ffmpeg。它不会自动听懂声音或判断画面语义；完整观看、听审和可靠的观察来源仍须单独取得。

## 在智能体中使用

原有兼容安装命令仍可选择三个旧入口：

```sh
npx skills add kanehuang168/deepseen-commerce-skills
```

查看可安装列表但不安装：

```sh
npx skills add kanehuang168/deepseen-commerce-skills --list
```

每个技能使用标准SKILL.md目录结构。可让支持Agent Skills的客户端加载指定技能文件；具体安装方式和兼容性以客户端为准。本仓库仅对脚本和包结构做了本地验证，不宣称所有客户端、视频模型或真实生成效果都通过。

## 到DeepSeen继续

需要进一步分析、制作或保存业务结果时，可自愿访问 [DeepSeen](https://deepseen.ai/?utm_source=github&utm_medium=skill&utm_campaign=commerce_skills)。连接后先读取当前开放能力与实时报价，再由本人授权。此链接仅用于网页来源区分；本地脚本不收集或回传数据。

公开版能够独立完成上表的小任务。DeepSeen云端服务与本地结果分别说明，不把免费安装当作免费媒体生成，不收集聊天中的密钥。

## 资料和许可

本仓库采用[MIT许可证](LICENSE)，允许修改、分发及商业使用，须保留版权和许可声明。DeepSeen云端服务及未收录的私有内核不在此许可范围内。没有打包客户素材、内部运行日志、生产配置或私有Git历史。

不使用真实客户结果作为示例；外部来源须保留署名和适用许可。完整能力边界见各技能说明。

平台和工具名称仅说明适用场景、格式或实际依赖，不表示合作、授权或背书；适用许可和必要版权声明仍须遵守。
