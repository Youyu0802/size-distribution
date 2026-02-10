# Measurement Tool

A desktop application for measuring nanoparticle sizes from TEM/SEM images.

从 TEM/SEM 图片中测量纳米颗粒粒径的桌面应用程序。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

## Features / 功能

- **Scale Calibration** - Set scale using scale bar with multiple units (nm, μm, mm, Å)
- **Particle Measurement** - Click to measure particle diameters
- **Size Distribution** - Generate histograms with Gaussian fitting
- **Color Analysis** - Automatic particle detection by color
- **Measurement Grouping** - Draw rectangles to group measurements with per-group statistics
- **Unit Conversion** - Switch display units (Å, nm, μm, mm, cm) at any time
- **Data Export** - Export measurements to CSV with Gaussian fit curve & formula
- **Bilingual UI** - Chinese/English interface

---

- **标尺校准** - 使用标尺条设定比例尺，支持多种单位（nm, μm, mm, Å）
- **粒径测量** - 点击测量颗粒直径
- **粒径分布** - 生成直方图并进行高斯拟合
- **颜色分析** - 基于颜色自动识别颗粒
- **测量分组** - 绘制矩形框将测量分组，支持分组统计
- **单位切换** - 随时切换显示单位（Å、nm、μm、mm、cm）
- **数据导出** - 导出测量数据为 CSV，含高斯拟合曲线及公式
- **双语界面** - 中文/英文切换

## Screenshots / 截图

*(Coming soon)*

## Installation / 安装

### Option 1: Download executable (Windows)

Download the latest release from [Releases](../../releases) page.

从 [Releases](../../releases) 页面下载最新版本。

### Option 2: Run from source

```bash
# Clone the repository
git clone https://github.com/Youyu0802/size-distribution.git
cd size-distribution

# Install dependencies
pip install pillow matplotlib numpy scipy

# Run
python nano_measurer.py
```

## Usage / 使用方法

1. **Open Image** - File → Open Image (加载 TEM/SEM 图像)
2. **Set Scale** - Tools → Set Scale, click both ends of scale bar (点击标尺两端设定比例尺)
3. **Measure** - Tools → Measure, click particle diameter endpoints (点击颗粒直径两端测量)
4. **View Distribution** - Tools → Distribution (查看粒径分布)
5. **Export Data** - File → Export CSV (导出数据)

### CSV Export Content / CSV 导出内容

The exported CSV includes:

| Section | Content |
|---------|---------|
| Raw Data | Index, diameter/area, pixel distance, coordinates |
| Statistics | Count, mean, std, min, max, scale |
| Gaussian Fit | Formula: `f(x) = (1/(σ√(2π))) × exp(-(x-μ)²/(2σ²))`, μ, σ values |
| Fit Curve | 200 data points (X, Y) for re-plotting in Excel/Origin |

导出的 CSV 文件包含：

| 区域 | 内容 |
|------|------|
| 原始数据 | 序号、粒径/面积、像素距离、坐标 |
| 统计量 | 计数、均值、标准差、最小值、最大值、比例尺 |
| 高斯拟合 | 公式: `f(x) = (1/(σ√(2π))) × exp(-(x-μ)²/(2σ²))`、μ、σ 值 |
| 拟合曲线 | 200 个数据点 (X, Y)，可在 Excel/Origin 中重绘 |

### Shortcuts / 快捷键

| Action | Shortcut |
|--------|----------|
| Pan | Right-drag |
| Zoom | Scroll wheel |
| Undo | Ctrl+Z |
| Delete | Delete key |

## Dependencies / 依赖

- Python 3.8+
- Pillow (PIL)
- NumPy
- SciPy
- Matplotlib
- Tkinter (included with Python)

## License / 许可证

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## Author / 作者

**Peijiang Wang**

- Email: wangpeijiang0802@gmail.com
- GitHub: [@Youyu0802](https://github.com/Youyu0802)

## Acknowledgments / 致谢

This software uses the following open source libraries:

- [Python](https://www.python.org/) - PSF License
- [Pillow](https://pillow.readthedocs.io/) - HPND License
- [NumPy](https://numpy.org/) - BSD License
- [SciPy](https://scipy.org/) - BSD License
- [Matplotlib](https://matplotlib.org/) - PSF-based License
