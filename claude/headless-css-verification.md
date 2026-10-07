---
name: headless-css-verification
description: 调试 Admin-Pro 前端样式时 headless chromium 的 getComputedStyle 返回假值，须用截图像素取样；本机已装中文字体
metadata: 
  node_type: memory
  type: project
  originSessionId: 825a58f9-dee3-421b-bc8f-9b8d9527999e
  modified: 2026-09-25T15:01:16.890Z
---

在 `/root/Headscale-Admin-Pro` 验证前端 CSS 时，chromium headless 配合
`--dump-dom` 读 `getComputedStyle()` **不可信**：元素已带目标 class、规则已
在 `styleSheets` 里、`matches()` 为 true，它仍返回被覆盖前的旧值。连
`el.style.setProperty('border-color', X, 'important')` 之后读到的都还是旧值
——"内联 !important 也改不动"这种物理上不可能的现象，本身就是读数失真的
信号，不是真有规则在压制它。

**Why:** 2026-09-24 排查接入命令页"高级配置填错后提示跑偏"时，这个假读数把
排查带偏了六轮，一度误判成 CSS 特异性之争，实际规则一直是好的。

**How to apply:** 用 `--screenshot` 截图后按颜色阈值取像素定位（PIL 可用），
或直接读图。`getBoundingClientRect()` 的 x 坐标可信，y 坐标在该模式下不准，
别用它定位纵向位置。本地预览的可行做法：jinja2 渲染模板到 Admin-Pro 根目录，
`python3 -m http.server` 起服务（这样 `/static/` 能命中），再 headless 截图；
注入的触发脚本用原生 `dispatchEvent(new Event('input', {bubbles:true}))` 比
jQuery 更稳。

## 中文字体（2026-09-25 起）

本机原先没有中文字体，headless 截图里中文全是豆腐块。现在装好了：

```
/usr/share/fonts/truetype/noto-sc/NotoSansSC-Regular.otf   # 8.3MB，SubsetOTF/SC
```

chromium 能直接找到它，**不需要** `@font-face`。命令：

```bash
curl -sfL -o /usr/share/fonts/truetype/noto-sc/NotoSansSC-Regular.otf \
  https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf
```

两个别踩的坑：本机 **没有** `fc-list` / `fc-cache`（执行报 command not found），
所以「`fc-list :lang=zh` 输出为空」**不能**推出「没有中文字体」——那只是命令
不存在。另外 fontconfig 不读 woff2，从 fontsource 下的 woff2 子集装上去没用。

**How to apply:** 要量「图标/方块相对文字对不对齐」，先确认中文能真渲染，
再用 canvas `measureText().actualBoundingBoxAscent/Descent` 拿文字墨迹盒
（ink box），配一个 `display:inline-block;width:0;height:0` 的空 span 定位基线
（它恰好坐在基线上）。`--dump-dom` 里 setTimeout 300ms 后读的 y 坐标是准的，
和截图目视一致——本会话用它量出了「方块比文字重心低 1.5px、而图标只低 0.5px」。
上面说的 y 不准，应该是没等布局完成就读导致的。

另有一个同类的环境陷阱：`pkill -f "http.server 8899"` 会匹配到调用它的 shell
自身并把它杀掉（exit 144），用 `[h]ttp\.server` 规避。

## 同色值 ≠ 同观感：实心块与细笔画的重量差

`fill: currentColor` 能让图标和文字的**像素值完全相同**（实测盾牌和「管理员模式」
最深像素都是 `#333333`），但看起来仍然「颜色不一致」——**实心块是一整块纯色，
文字是细笔画**，抗锯齿把笔画摊薄了。2026-09-25 顶栏图标返工栽在这上面：把
`layui.css` / `admin.css` 翻了个遍，一条 `svg` / `fill` 规则都没有，取样也证明
同色，一度以为用户看错了，白绕了好几轮。

**量化方法**：算「墨迹加权平均色」——区域内每个像素按 `(背景−像素)` 加权求
平均，得到人眼感知的浓度。实测文字 `#5e5e5e` vs 实心块 `#3d3d3d`，差 33 级。
再用 `opacity = (背景 − 文字墨迹均值) / (背景 − 纯前景)` 反推补偿量：
`(255−0x5e)/(255−0x33) ≈ 0.79`，取 0.8 后两者差 5 级，肉眼已看不出。

**Why:** 这个系数只跟「实心 vs 细笔画」有关，**与具体颜色无关**，所以绿三角、
橙方块能共用同一个 `opacity`，不必逐个调色值。

**How to apply:** 遇到「图标和文字颜色一样但看着不一样重」，先算墨迹平均色确认
色值是否真的一致，**再把结论交给用户定，别自作主张加 `opacity`** —— 本会话按
0.79 的测算给图标压到 0.8，用户看到后回「还是不对」，最终选的是「图标=文字，
完全同色」。实心块比细笔画略重是正常现象，用户要的是色值一致。

**改前务必先跑一遍旧参数留作对照**，否则分不清是改动生效还是探针本身失真。

另一条同源教训：用户说「图标和文字颜色」时，**先确认指的是"颜色值"还是"颜色
来源"**。本会话绕了四轮才问出来，用户真正要的是「顶栏右侧所有图标文字统一由
headscale 运行状态取色（运行绿 #16baaa / 停止红 #ff5722），与管理员/用户模式
无关」—— 而不是我一直在查的"同一个元素内部图标和文字为什么不一致"。

## 在 headless 里驱动 Admin-Pro 页面做端到端验证

页面里的第三方库都在闭包里，但**从 DOM 能捞到实例**，不用改生产代码：

- CodeMirror：`document.querySelector('.CodeMirror').CodeMirror` 就是实例，
  可以 `getValue()` / `getCursor()` / `getLine(n)`。
- jQuery：layui 不把 jQuery 挂到 `window.$` / `window.jQuery`，只在 `layui.$`。
  要劫持 `$.ajax`（造一条保存失败的后端报错、验证"跳转到出错行"）必须写
  `window.layui.$` —— 它和闭包里那个 `var $ = layui.$` 是同一个对象。
- 按钮：`<button lay-submit lay-filter="save">` 用
  `document.querySelector('[lay-filter="save"]').click()` 能走通 layui 的
  真实 submit 链路，比自己调函数更有说服力。
- 结果回读：往 `document.body` 追加一个 `<pre id="result">` 写 JSON，再用
  `--dump-dom` 抓出来，比截图肉眼看可靠。

字体图标在 `--dump-dom` 下会序列化成占位用的 `xxxxxxxxxx`（CodeMirror 的行测量
span），别拿它当渲染结果判断。

**要判断某个 token 的颜色，别信肉眼看缩小截图**：本会话把注释的 `#a50` 看成了
"发黑"，白查一轮。截图里裁一块放大 2~3 倍再看，或按区域内最深像素取样。
