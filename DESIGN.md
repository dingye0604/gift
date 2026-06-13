# Gift 网站设计文档 v2

## 设计问题诊断

当前首页"死板"的根因不是河流元素不够多，而是它仍然是传统左右时间轴：中心线固定、节点等距、卡片对称、桥宽用 nth-child 硬编码。

## 信息结构

```
首页 /
  ├─ 先秦 /xian-qin/
  │   ├─ 朝代导言
  │   └─ 诗歌目录
  │       ├─ 关雎
  │       └─ ...
  └─ 单首诗 /tang/jing-ye-si.html
```

- 首页：总览与入口
- 朝代页：导言 + 诗歌子目录
- 单首诗：阅读

## 首页视觉方向

**诗歌之河，不是时间轴。** 河流不是竖直居中的管道，而是一条不规则蜿蜒水脉。朝代节点像"渡口、洲渚、河湾"一样依附在河岸附近，不再左右机械交替。

首页分三层：
```html
<section class="home-river">
  <header class="river-opening">...</header>
  <div class="river-scroll">
    <svg class="river-map">...</svg>
    <nav class="dynasty-ports">
      <a class="dynasty-port" style="--x: 42%; --y: 12%">...</a>
      ...
    </nav>
  </div>
</section>
```

朝代入口用 CSS 变量定位，自然错落：
```css
.dynasty-port {
  --x: 42%; --y: 12%;
  position: absolute;
  left: var(--x); top: var(--y);
}
```

## 河流视觉细节

- 河道宽度有变化：上游窄、唐宋附近宽、近代入海处散开
- 水色保持青绿但降低纯度
- 水纹用 `stroke-dasharray + animation`，18s 缓慢漂移
- `prefers-reduced-motion` 下关闭动画
- 2-3 层半透明 SVG path 叠加，形成水纹、浅滩、流速变化
- 河面用 2-3 层半透明 SVG path 叠加

## 朝代入口样式

白色卡片改成"岸边题签"：
- 朝代名大一点，带水滴/墨点装饰
- 摘要小字副标题，数量低调文本
- hover 时水纹变亮、题签微微偏移（不浮起卡片）

## 朝代目录页

每个有诗的朝代都生成 `dynasty_dir/index.html`（不仅限于有 `_intro.tex` 的朝代）：
- 面包屑导航返回首页
- 导言（如有）
- 诗歌目录（列表，不网格卡片）

## 单首诗歌页

底部"返回目录"指向当前朝代目录 `/{dynasty_dir}/`

## 修改清单

1. `build.py`: 朝代目录页始终生成（不管有无 _intro），传入 poems、summary、intro_text
2. `intro.html`: 从"导言页"改成"朝代目录页"，导言只是其中一个模块
3. `poem.html`: 底部返回链接改回朝代目录
4. `index.html`: 首页入口改自然河岸
5. `style.css`: 重写河流首页段落，删除左右时间轴/桥宽硬编码/白卡片感

## 移动端响应式设计（Mobile Adaptive）

为了在移动端（`max-width: 1024px`）优雅地呈现这条“诗歌之河”，我们放弃了死板的网格对齐，设计了**动态河心浮动时间轴**：

1. **河流靠左，卡片居右**：
   - 移动端将 SVG 蜿蜒河流定位在左侧（`left: 2%; width: 32%`），右侧留给文字。
   - 所有偶数节点（`nth-child(even)`）的左右交替样式被重置，强制统一为“左圆点、右文字”的单列视觉流向。

2. **渡口圆点数学河心对齐（Mathematical Centerline Alignment）**：
   - 圆点（`.river-dot`）不再使用桌面端估算值，而是通过计算贝塞尔曲线左右河岸在各高度上的平均值 `(Left_X + Right_X) / 2`，换算为精确屏幕百分比 `--x-mobile`，完美居于河道水平几何中心：
     - 先秦: `17.6%` | 两汉: `17.5%` | 魏晋: `18.1%` | 南北朝: `20.6%` | 唐: `20.5%`
     - 五代十国: `18.1%` | 两宋: `17.6%` | 元: `20.1%` | 明清: `22.0%` | 近代: `24.0%`

3. **文字卡片随河道波浪起伏（Wavy/Floating Alignment）**：
   - 题签卡片（`.river-card`）打破直线对齐，其 `left` 坐标和宽度 `width` 均绑定河心 X 坐标（`var(--x-mobile)`）：
     - `left: calc(var(--x-mobile) + 28px) !important;`
     - `width: calc(100% - (var(--x-mobile) + 28px) - 16px) !important;`（右侧预留 16px 视口页边距防溢出）
   - 卡片在水平方向上随河流曲线浮动移位，与河流的动态律动完全统一。

4. **桥接线交互**：
   - 起点绑定在圆点右侧（`left: calc(var(--x-mobile) + 4px)`），长度设为固定的 `18px`，悬停时拉伸到 `26px`。
   - 悬停拉伸期间卡片文字保持静止，避免产生物理抖动，交互体验平滑自然。

## 原则

- 无 JS，纯 SVG + CSS
- 移动端自适应，点击区域更大，排版随河流曲线波动
- 保持当前站点配色体系（靛青、朱砂红、暖象牙白）
