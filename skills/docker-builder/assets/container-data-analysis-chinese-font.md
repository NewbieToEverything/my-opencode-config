# 数据分析类 docker 容器中文字体处理
## 情况一：基础镜像自带中文字体
- 确认：`fc-list :lang=zh | head -5`
- 检查 matplotlib 是否已识别：
  ```python
  [f.name for f in matplotlib.font_manager.fontManager.ttflist if 'WenQuan' in f.name or 'CJK' in f.name]
  ```
- 配置：
  ```python
  plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC']
  plt.rcParams['axes.unicode_minus'] = False
  ```

### 情况二：基础镜像不带中文字体——动态图片（HTML 图表，推荐）
- 使用 Plotly 替代 matplotlib（生成 SVG/HTML，浏览器渲染中文）
- 无需安装字体，无需额外配置
- Python 示例：
  ```python
  import plotly.graph_objects as go
  fig = go.Figure()
  fig.add_trace(go.Bar(x=['选择题','简答题'], y=[85.2, 72.1]))
  fig.update_layout(title=dict(text='得分率', font=dict(size=14)))
  ```

### 情况三：基础镜像不带中文字体——静态图片（matplotlib/seaborn，需 PNG/PDF 输出）
- 在 Dockerfile 中安装字体（注意先 `USER root` 后切回默认用户）：
  ```dockerfile
  USER root
  RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
             /etc/apt/sources.list && \
      sed -i 's|http://security.ubuntu.com/ubuntu|http://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
             /etc/apt/sources.list && \
      apt-get update && apt-get install -y --no-install-recommends fonts-wqy-microhei && \
      rm -rf /var/lib/apt/lists/*
  USER <默认用户名>
  ```
- 在 Python 脚本中清理缓存并配置：
  ```python
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.font_manager as fm
  import os

  cache_dir = matplotlib.get_cachedir()
  for f in os.listdir(cache_dir):
      if f.startswith('fontlist'):
          os.remove(os.path.join(cache_dir, f))
  fm._rebuild()

  plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
  plt.rcParams['axes.unicode_minus'] = False
  ```
