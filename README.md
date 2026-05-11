# Anime No-Reference Clip Skill

面向 Codex 的动漫自动剪辑 skill，用源视频本身完成短视频解说剪辑流程：转录、镜头检测、关键帧、子代理视觉打标、故事原子、强钩子脚本、镜头映射、整段 TTS、字幕边界表、后 TTS 节奏修复、竖版合成、内跳扫描和交付 QA。

当前迁移版本来自本地 `anime-noref-clip` skill 的 `v1.4.9`，保留了 `v1.4.2` 之后的连续源片段、后钩子节奏稳定、25-35 镜头/60 秒短视频等规则。

## 仓库结构

```text
.
├── README.md
├── requirements.txt
└── anime-noref-clip/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── references/
    ├── scripts/
    └── templates/project/
```

`anime-noref-clip/` 是真正的 skill 文件夹。根目录 README 只用于 GitHub 分享，不属于 skill 必需上下文。

## 安装

手动安装到 Codex skills 目录：

```bash
git clone https://github.com/Alligxator/anime-noref-clip-skill.git
mkdir -p ~/.codex/skills
cp -R anime-noref-clip-skill/anime-noref-clip ~/.codex/skills/
```

安装项目工具依赖：

```bash
python3 -m pip install -r anime-noref-clip-skill/requirements.txt
```

还需要本机可用：

- `ffmpeg` 和 `ffprobe`
- Codex 子代理能力，用于视觉打标和字幕 boundary 分组
- AssemblyAI API key，运行转录前设置到环境变量 `ASSEMBLYAI_API_KEY`

## 快速使用

在新的剪辑项目目录里先初始化项目本地工具：

```bash
python3 ~/.codex/skills/anime-noref-clip/scripts/init_project_scripts.py --project-root .
```

然后在 Codex 中触发 skill，例如：

```text
用 $anime-noref-clip 剪这一集，做 60 秒左右竖版短视频，允许子代理打标，先做中文版。
```

skill 会先输出执行表和当前 gate 状态。不要跳过脚本-镜头 review、整段 TTS、post-TTS pacing repair、字幕 boundary 表、内部跳切扫描和最终 QA。

## 关键约束

- 只基于源视频、字幕、转录和视觉打标中能支持的信息写脚本。
- 视觉打标必须由 Codex 子代理生成 JSONL，并通过合并校验。
- TTS 必须是整段生成，不使用 `unit_*` 音频拼接作为主流程。
- 字幕先用真实 TTS `WordBoundary` 建 boundary table，再由子代理按 boundary id 分组。
- 竖版输出使用模糊背景加完整居中的 16:9 前景，字幕坐标必须落在前景框内。
- 默认水印占位是 `@YourHandle`，实际发布前请改成自己的账号或显式传入 `--watermark-text`。

## 注意

这个仓库不包含任何源视频、成片、项目产物或 API key。使用者需要自己准备合法来源素材，并自行确认平台规则、版权授权和模型/API 成本。
