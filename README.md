# md2handnote

`md2handnote` 用于把 UTF-8 Markdown 转换成不可搜索的手写风格 A4 横线纸 PDF。它适合把中英文说明、LaTeX 公式和简单笔记内容渲染成更像手写作业/手写笔记的图片型 PDF。

当前版本的核心目标是生成一份视觉上接近手写扫描件的 PDF。

## 效果预览

![md2handnote 生成效果](docs/preview.png)

示例输出见 [examples/sample.pdf](examples/sample.pdf)，示例输入见 [examples/sample.md](examples/sample.md)。

## 功能

- 支持中文、英文和中英混排文本。
- 支持 `$...$` 行内公式和 `$$...$$` 块级公式。
- 使用 A4 横线纸背景，输出不可搜索的图片型 PDF。
- 支持随机种子，方便复现同一版手写扰动。
- 支持配置字体、字号、页边距、行距、墨色和抖动幅度。
- 对重复文字做轻微字号、宽度、旋转和字形形变，减少完全复制粘贴的观感。

## 安装

建议使用 Python 3.10 或更高版本。

```bash
python -m pip install -e .
```

数学公式通过 `tectonic` 渲染，所以需要额外安装这个外部程序：

```bash
tectonic --version
```

如果命令不存在，请先安装 Tectonic。没有 `tectonic` 时，普通文本仍可解析，但包含公式的文档无法正常渲染。

## 快速使用

```bash
md2handnote examples/sample.md -o examples/sample.pdf --config examples/config.yaml --seed 42
```

参数说明：

- `input`：输入 Markdown 文件，必须是 UTF-8 编码。
- `-o, --output`：输出 PDF 路径。
- `--config`：YAML 配置文件路径。
- `--seed`：随机种子。传入相同种子可以复现相同排版和扰动。
- `--dpi`：覆盖配置里的页面 DPI。
- `--verbose`：打印更详细的处理日志。

## 字体怎么选

字体对最终效果影响很大。一个实用原则是：中文字体不要太规整，英文不要太印刷，公式保持正常 LaTeX 字体。

当前示例配置使用：

```yaml
fonts:
  chinese_font: ../fonts/ZhiMangXing-Regular.ttf
  english_font: ../fonts/Caveat-wght.ttf
  math_font_hint: null
```

项目里已经放入几种可选字体：

| 字体文件 | 适合场景 | 取舍 |
| --- | --- | --- |
| `ZhiMangXing-Regular.ttf` | 默认中文字体，偏行书，比较不方正 | 笔势明显，但部分字会有书法式断笔 |
| `LongCang-Regular.ttf` | 更日常、更容易读 | 结构略方，手写感比文楷好但没那么流动 |
| `chinese_handwriting.ttf` | LXGW WenKai，硬笔风格 | 清晰稳定，但更像字体，容易显得规整 |
| `MaShanZheng-Regular.ttf` | 强书法味中文 | 毛笔感明显，不太像普通课堂笔记 |
| `LiuJianMaoCao-Regular.ttf` | 很强的草书感 | 个性强，但长文可读性差 |
| `Caveat-wght.ttf` | 默认英文字体 | 连笔感更强，适合夹在中文笔记里 |
| `english_handwriting.ttf` | Patrick Hand | 更规整，像普通手写印刷体 |

建议：

- 想要“不要太像打印”：优先试 `ZhiMangXing-Regular.ttf`。
- 想要“别太草、看得清”：试 `LongCang-Regular.ttf`。
- 想要“最稳定、最少奇怪字形”：试 `chinese_handwriting.ttf`。
- 不建议在同一行随机混用多个中文字体。不同字体的笔画习惯差异太大，反而会显得像拼贴。
- 英文和中文最好选择粗细接近的字体；否则中英文混排时会显得不是同一支笔写的。

字体许可证和版权声明见 [fonts/LICENSES.md](fonts/LICENSES.md)。

## 配置说明

示例配置在 [examples/config.yaml](examples/config.yaml)。

常用配置项：

```yaml
page:
  dpi: 300
  margin_left_mm: 22
  margin_top_mm: 18
  line_spacing_mm: 9
  show_lined_paper: true

text:
  chinese_font_size_px: 62
  english_font_size_px: 56
  ink_alpha_min: 210
  ink_alpha_max: 230

jitter:
  char_x_px: 1.9
  char_y_px: 0.35
  char_rotation_deg: 1.4
  line_y_px: 0.2
```

调参建议：

- 字太小：增大 `text.chinese_font_size_px` 和 `text.english_font_size_px`，或减小 `page.line_spacing_mm` 前先确认字不会压线。
- 行内高低不自然：减小 `jitter.char_y_px` 和 `jitter.line_y_px`。
- 字太规整：略增大 `jitter.char_rotation_deg` 和 `jitter.char_x_px`，但过大会变成抖动感。
- 墨色不统一：调整 `text.ink_alpha_min` 和 `text.ink_alpha_max`，让范围更窄。
- 公式太突兀：当前公式使用正常 LaTeX 字体，适合解释为 OneNote/平板的墨迹转公式结果；如果要手写公式风格，需要后续单独做公式字体或公式笔迹渲染。

## Markdown 支持范围

当前支持：

- 普通文本
- `$...$` 行内公式
- `$$...$$` 块级公式

当前不会特殊渲染：

- 标题
- 列表
- 表格
- 图片
- 代码块
- 引用块

这些结构会作为普通文本处理，并在运行时给出警告。这个限制是有意保留的：当前版本优先保证普通段落和公式的手写效果。

## 输出特点和限制

- 输出 PDF 是图片型 PDF，不支持复制文字或搜索。
- 公式由 LaTeX 渲染，再贴入页面；它不会和中文字体完全一样。
- 中文手写效果高度依赖字体本身。程序可以做轻微扰动，但不能把一个规整字体完全变成真人手写。
- 如果输入里有很多未覆盖字符，字体缺字会导致渲染失败或显示异常。建议优先使用覆盖完整的中文字体。
- 当前没有真正生成个人字体。

## 开发

运行测试：

```bash
python -m unittest discover -s tests
```

重新生成示例 PDF：

```bash
md2handnote examples/sample.md -o examples/sample.pdf --config examples/config.yaml --seed 42
```

## 许可证

项目代码使用 MIT 许可证，见 [LICENSE](LICENSE)。

`fonts/` 目录中的字体文件使用各自的 SIL Open Font License 1.1，见 [fonts/LICENSES.md](fonts/LICENSES.md) 和 [fonts/OFL-1.1.txt](fonts/OFL-1.1.txt)。
