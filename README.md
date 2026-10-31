# DeepSeen 电商实用 Skills

作者：祥子｜无疆AI出海圈 · DeepSeen

把广告报表变成可核查的观察，把商品原稿变成可执行分镜，把成片检查变成有证据的判断。

## 首发范围

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

可通过Skills CLI选择安装这三个入口：

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
