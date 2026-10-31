# 视频检查输入

调用方从用户确认要求解析authority，从实际观看或可靠记录提供observation，不能由计划推测观察。

- authority.scriptHash：确认要求的SHA256；observation.scriptHash须对应同一要求。
- authority.audioMode：明确静默为SILENT，必要口播为SPEECH，必要环境音为ENVIRONMENT；不明时保持未指定。
- authority.checks：稳定id、applies；只有明确时序要求才有eventWindowSeconds，单位秒。
- observation.mediaSha256：实际最终文件的SHA256。
- observation.videoCoverage/audioCoverage：完整覆盖为FULL，抽样为SAMPLED，未观察为NONE。声明须有可靠来源。
- observation.speechPresent、audioMatchesRequirement：仅实际听审后填布尔值，不能凭音轨存在填通过。
- observation.checks：与确认检查同id，状态PASS、FAIL或NEEDS_EVIDENCE；evidence含kind=OBSERVED、startSec、endSec及简体中文descriptionZh。事件可另记录observedEventSec。

缺少有效指纹或实际观察时脚本返回未核验。它不能验证调用方是否真的观看了视频，不能替代独立审核或客户确认。不要把内部执行提示词、凭据或完整聊天塞入审核文件。

使用者自己选择输入与新输出路径。脚本不会联网、上传文件或创建生成任务。ffprobe/ffmpeg缺失、输入无法读取或解码失败都应如实报告，不能当作零问题。
