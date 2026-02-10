"""
Measurement Tool
从 TEM/SEM 图片中手动测量纳米颗粒粒径并生成分布统计。
依赖: Pillow, matplotlib, numpy, scipy
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import math
import csv
import os

import numpy as np
from PIL import Image, ImageTk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.font_manager as fm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from scipy.stats import norm
from scipy.ndimage import label as ndimage_label


# ---------------------------------------------------------------------------
# matplotlib 中文字体配置
# ---------------------------------------------------------------------------

def _setup_matplotlib_font():
    """自动检测系统中可用的 CJK 字体并配置 matplotlib。"""
    candidates = [
        "Microsoft YaHei", "SimHei", "SimSun", "NSimSun",
        "FangSong", "KaiTi", "Source Han Sans CN",
        "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Arial Unicode MS",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return name
    # 回退: 仍然关闭 unicode_minus 以免减号显示异常
    matplotlib.rcParams["axes.unicode_minus"] = False
    return None

_CJK_FONT = _setup_matplotlib_font()


# ---------------------------------------------------------------------------
# 国际化字符串
# ---------------------------------------------------------------------------

STRINGS = {
    # ---- 工具栏 ----
    "open_image":       {"zh": "打开图片",   "en": "Open Image"},
    "set_scale":        {"zh": "设定标尺",   "en": "Set Scale"},
    "measure":          {"zh": "测量",       "en": "Measure"},
    "distribution":     {"zh": "粒径分布",   "en": "Distribution"},
    "export_csv":       {"zh": "导出 CSV",   "en": "Export CSV"},
    "fit_window":       {"zh": "适应窗口",   "en": "Fit Window"},

    # ---- 右侧面板 ----
    "scale_info":       {"zh": "标尺信息",   "en": "Scale Info"},
    "scale_not_set":    {"zh": "比例尺: 未设定", "en": "Scale: not set"},
    "scale_fmt":        {"zh": "比例尺: {v:.4f} {u}/px", "en": "Scale: {v:.4f} {u}/px"},
    "meas_list":        {"zh": "测量列表",   "en": "Measurements"},
    "col_id":           {"zh": "#",          "en": "#"},
    "col_diameter":     {"zh": "粒径 ({u})",  "en": "Diameter ({u})"},
    "delete_sel":       {"zh": "删除选中",   "en": "Delete"},
    "clear_all":        {"zh": "清空全部",   "en": "Clear All"},
    "statistics":       {"zh": "统计信息",   "en": "Statistics"},
    "count":            {"zh": "计数",       "en": "Count"},
    "mean":             {"zh": "均值",       "en": "Mean"},
    "std":              {"zh": "标准差",     "en": "Std Dev"},
    "min":              {"zh": "最小",       "en": "Min"},
    "max":              {"zh": "最大",       "en": "Max"},

    # ---- 状态栏 ----
    "ready":            {"zh": "就绪",       "en": "Ready"},
    "mode_idle":        {"zh": "浏览",       "en": "Browse"},
    "mode_scale":       {"zh": "标尺校准",   "en": "Calibrate"},
    "mode_measure":     {"zh": "测量",       "en": "Measure"},
    "status_fmt":       {"zh": "模式: {mode}  |  缩放: {zoom:.0f}%  |  坐标: ({x:.1f}, {y:.1f})",
                         "en": "Mode: {mode}  |  Zoom: {zoom:.0f}%  |  Pos: ({x:.1f}, {y:.1f})"},
    "status_short_fmt": {"zh": "模式: {mode}  |  缩放: {zoom:.0f}%",
                         "en": "Mode: {mode}  |  Zoom: {zoom:.0f}%"},

    # ---- 标尺 ----
    "scale_click1":     {"zh": "标尺校准: 请点击标尺的第一个端点",
                         "en": "Calibration: click the first end of the scale bar"},
    "scale_click2":     {"zh": "标尺校准: 请点击标尺的第二个端点",
                         "en": "Calibration: click the second end of the scale bar"},
    "scale_too_close":  {"zh": "两点距离过近，请重新点击第二个端点",
                         "en": "Points too close, click the second end again"},
    "scale_dialog_title": {"zh": "标尺校准",  "en": "Scale Calibration"},
    "scale_dialog_px":  {"zh": "标尺像素长度: {px:.1f} px", "en": "Scale bar length: {px:.1f} px"},
    "scale_dialog_val": {"zh": "实际距离:", "en": "Actual distance:"},
    "scale_dialog_unit": {"zh": "单位:", "en": "Unit:"},
    "scale_set_fmt":    {"zh": "标尺已设定: {v:.4f} {u}/px",
                         "en": "Scale set: {v:.4f} {u}/px"},

    # ---- 测量 ----
    "meas_click1":      {"zh": "测量: 请点击粒子直径的第一个端点",
                         "en": "Measure: click the first end of the particle diameter"},
    "meas_click2":      {"zh": "测量: 请点击第二个端点 (右键取消)",
                         "en": "Measure: click the second end (right-click to cancel)"},
    "meas_recorded":    {"zh": "已记录 #{n}: {d:.2f} {u}  |  继续点击下一个粒子 (Esc 退出)",
                         "en": "Recorded #{n}: {d:.2f} {u}  |  Click next particle (Esc to exit)"},
    "meas_cancelled":   {"zh": "已取消当前测量，请重新点击第一个端点",
                         "en": "Cancelled. Click the first endpoint again."},
    "meas_50_reached":  {"zh": "已达到 {n} 个测量点！",
                         "en": "{n} measurements reached!"},

    # ---- 撤销/取消 ----
    "undo_click":       {"zh": "已撤销当前点击", "en": "Current click undone"},
    "undo_meas_fmt":    {"zh": "已撤销测量 #{n}", "en": "Undid measurement #{n}"},
    "cancelled":        {"zh": "已取消",     "en": "Cancelled"},

    # ---- 对话框/提示 ----
    "warn":             {"zh": "提示",       "en": "Notice"},
    "error":            {"zh": "错误",       "en": "Error"},
    "confirm":          {"zh": "确认",       "en": "Confirm"},
    "open_image_title": {"zh": "打开图片",   "en": "Open Image"},
    "img_files":        {"zh": "图片文件",   "en": "Image files"},
    "all_files":        {"zh": "所有文件",   "en": "All files"},
    "open_fail":        {"zh": "无法打开图片:\n{e}", "en": "Cannot open image:\n{e}"},
    "no_image":         {"zh": "请先打开图片。", "en": "Please open an image first."},
    "no_scale":         {"zh": "请先设定标尺。", "en": "Please set the scale first."},
    "positive_number":  {"zh": "请输入一个正数。", "en": "Please enter a positive number."},
    "no_data":          {"zh": "没有测量数据。", "en": "No measurement data."},
    "clear_confirm":    {"zh": "确定要清空所有测量吗?", "en": "Clear all measurements?"},
    "export_title":     {"zh": "导出 CSV",   "en": "Export CSV"},
    "csv_files":        {"zh": "CSV 文件",   "en": "CSV files"},
    "exported_fmt":     {"zh": "已导出: {p}", "en": "Exported: {p}"},
    "export_fail":      {"zh": "导出失败",   "en": "Export failed"},

    # ---- 直方图 ----
    "hist_title":       {"zh": "粒径分布直方图", "en": "Particle Size Distribution"},
    "hist_xlabel":      {"zh": "粒径 ({u})", "en": "Diameter ({u})"},
    "hist_ylabel":      {"zh": "频率密度",   "en": "Frequency Density"},
    "hist_legend_hist": {"zh": "频率直方图", "en": "Histogram"},
    "hist_legend_fit":  {"zh": "高斯拟合",   "en": "Gaussian Fit"},
    "hist_title_fmt":   {"zh": "粒径分布  (n={n}, \u03bc={mean:.2f}, \u03c3={std:.2f} {u})",
                         "en": "Size Distribution  (n={n}, \u03bc={mean:.2f}, \u03c3={std:.2f} {u})"},

    # ---- CSV 表头 ----
    "csv_diameter":     {"zh": "粒径 ({u})", "en": "Diameter ({u})"},
    "csv_pixel_dist":   {"zh": "像素距离 (px)", "en": "Pixel Dist (px)"},
    "csv_stat":         {"zh": "统计",       "en": "Statistics"},
    "csv_value":        {"zh": "值",         "en": "Value"},
    "csv_count":        {"zh": "计数",       "en": "Count"},
    "csv_mean":         {"zh": "均值",       "en": "Mean"},
    "csv_std":          {"zh": "标准差",     "en": "Std Dev"},
    "csv_min":          {"zh": "最小值",     "en": "Min"},
    "csv_max":          {"zh": "最大值",     "en": "Max"},
    "csv_scale":        {"zh": "比例尺 (nm/px)", "en": "Scale (nm/px)"},
    "csv_gauss_title":  {"zh": "高斯拟合",     "en": "Gaussian Fit"},
    "csv_gauss_formula":{"zh": "公式",         "en": "Formula"},
    "csv_gauss_mu":     {"zh": "μ (均值)",     "en": "μ (Mean)"},
    "csv_gauss_sigma":  {"zh": "σ (标准差)",   "en": "σ (Std Dev)"},
    "csv_gauss_curve":  {"zh": "拟合曲线数据", "en": "Fit Curve Data"},
    "csv_gauss_x":      {"zh": "X ({u})",      "en": "X ({u})"},
    "csv_gauss_y":      {"zh": "Y (概率密度)", "en": "Y (Density)"},

    # ---- 分组 ----
    "group_select":     {"zh": "框选分组",     "en": "Select Group"},
    "group_name_prompt":{"zh": "请输入分组名称:", "en": "Enter group name:"},
    "group_hint":       {"zh": "分组: 拖拽框选区域，框内测量点归为一组 (右键取消)",
                         "en": "Group: drag to select area, measurements inside form a group (right-click to cancel)"},
    "group_created":    {"zh": "已创建分组 \"{name}\" ({n} 个测量)",
                         "en": "Group \"{name}\" created ({n} measurements)"},
    "group_empty":      {"zh": "框选区域内没有测量点", "en": "No measurements in selected area"},
    "csv_group":        {"zh": "分组",         "en": "Group"},
    "csv_group_stat":   {"zh": "分组统计: {name}", "en": "Group Statistics: {name}"},
    "mode_group":       {"zh": "框选分组",     "en": "Group Select"},
    "display_unit":     {"zh": "显示单位",     "en": "Display Unit"},

    # ---- 颜色分析 ----
    "color_analysis":       {"zh": "颜色分析",       "en": "Color Analysis"},
    "mode_pick_color":      {"zh": "取色",           "en": "Pick Color"},
    "pick_color_hint":      {"zh": "颜色分析: 请在图片上点击取色",
                             "en": "Color Analysis: click on the image to pick a color"},
    "ca_title":             {"zh": "颜色分析",       "en": "Color Analysis"},
    "ca_picked_color":      {"zh": "取色",           "en": "Picked Color"},
    "ca_rgb_fmt":           {"zh": "RGB: ({r}, {g}, {b})", "en": "RGB: ({r}, {g}, {b})"},
    "ca_hsv_fmt":           {"zh": "HSV: ({h:.0f}, {s:.0f}, {v:.0f})",
                             "en": "HSV: ({h:.0f}, {s:.0f}, {v:.0f})"},
    "ca_tolerance":         {"zh": "容差设置",       "en": "Tolerance"},
    "ca_h_tol":             {"zh": "H 容差:",        "en": "H Tol:"},
    "ca_s_tol":             {"zh": "S 容差:",        "en": "S Tol:"},
    "ca_v_tol":             {"zh": "V 容差:",        "en": "V Tol:"},
    "ca_min_area":          {"zh": "最小面积:",      "en": "Min Area:"},
    "ca_min_area_unit":     {"zh": "px",             "en": "px"},
    "ca_preview":           {"zh": "预览",           "en": "Preview"},
    "ca_stats":             {"zh": "统计",           "en": "Statistics"},
    "ca_particle_count":    {"zh": "颗粒数: {n}",   "en": "Particles: {n}"},
    "ca_total_area_px":     {"zh": "总面积: {a} px²","en": "Total Area: {a} px²"},
    "ca_total_area_nm":     {"zh": "总面积: {a} nm²","en": "Total Area: {a} nm²"},
    "ca_coverage":          {"zh": "覆盖率: {c:.2f}%","en": "Coverage: {c:.2f}%"},
    "ca_particle_list":     {"zh": "颗粒列表",       "en": "Particle List"},
    "ca_col_id":            {"zh": "#",              "en": "#"},
    "ca_col_area":          {"zh": "面积 ({u})",     "en": "Area ({u})"},
    "ca_area_dist":         {"zh": "面积分布",       "en": "Area Dist."},
    "ca_export_csv":        {"zh": "导出 CSV",       "en": "Export CSV"},
    "ca_hist_title":        {"zh": "颗粒面积分布",   "en": "Particle Area Distribution"},
    "ca_hist_xlabel":       {"zh": "面积 ({u})",     "en": "Area ({u})"},
    "ca_hist_ylabel":       {"zh": "频率密度",       "en": "Frequency Density"},
    "ca_hist_legend_hist":  {"zh": "频率直方图",     "en": "Histogram"},
    "ca_hist_legend_fit":   {"zh": "高斯拟合",       "en": "Gaussian Fit"},
    "ca_hist_title_fmt":    {"zh": "面积分布  (n={n}, μ={mean:.2f}, σ={std:.2f} {u})",
                             "en": "Area Dist.  (n={n}, μ={mean:.2f}, σ={std:.2f} {u})"},
    "ca_exported_fmt":      {"zh": "已导出: {p}",    "en": "Exported: {p}"},
    "ca_npoints_fmt":       {"zh": "({n} 个取色点的平均值)", "en": "(average of {n} points)"},

    # ---- 多点取色 ----
    "pick_color_npts_title": {"zh": "取色点数",     "en": "Sample Points"},
    "pick_color_npts_msg":   {"zh": "请输入取色点数 (1-20):",
                              "en": "Number of sample points (1-20):"},
    "pick_color_progress":   {"zh": "颜色分析: 请点击第 {i}/{n} 个取色点",
                              "en": "Color Analysis: click point {i}/{n}"},

    # ---- 手动分割 ----
    "ca_manual_split":   {"zh": "手动分割",       "en": "Manual Split"},
    "ca_undo_split":     {"zh": "撤销分割",       "en": "Undo Split"},
    "ca_clear_splits":   {"zh": "清除分割",       "en": "Clear Splits"},
    "ca_brush_width":    {"zh": "画笔:",          "en": "Brush:"},
    "ca_split_hint":     {"zh": "左键拖拽画线分割 | 右键拖拽平移 | 滚轮缩放",
                          "en": "Left-drag to split | Right-drag to pan | Scroll to zoom"},

    # ---- 添加颜色点 ----
    "ca_add_color":      {"zh": "添加颜色点",     "en": "Add Color Point"},
    "ca_undo_color":     {"zh": "撤销颜色点",     "en": "Undo Color"},
    "ca_add_color_hint": {"zh": "左键点击添加颜色点 | 右键拖拽平移 | 滚轮缩放",
                          "en": "Left-click to add color | Right-drag to pan | Scroll to zoom"},
    "ca_color_added":    {"zh": "已添加颜色点 (共 {n} 个)", "en": "Color point added ({n} total)"},
    "ca_color_undone":   {"zh": "已撤销颜色点 (剩余 {n} 个)", "en": "Color point undone ({n} remaining)"},
    "ca_no_color_undo":  {"zh": "没有可撤销的颜色点", "en": "No color point to undo"},
    "ca_auto_tol":       {"zh": "自动调整容差",   "en": "Auto Tolerance"},

    # ---- 菜单栏 ----
    "menu_file":         {"zh": "文件",           "en": "File"},
    "menu_view":         {"zh": "视图",           "en": "View"},
    "menu_tools":        {"zh": "工具",           "en": "Tools"},
    "menu_about":        {"zh": "关于",           "en": "About"},
    "menu_zoom_100":     {"zh": "实际大小 (1:1)", "en": "Actual Size (1:1)"},
    "menu_language":     {"zh": "切换语言",       "en": "Switch Language"},
    "menu_feedback":     {"zh": "提出建议",       "en": "Feedback"},
    "menu_licenses":     {"zh": "开源许可",       "en": "Licenses"},
    "menu_help":         {"zh": "使用说明",       "en": "User Guide"},
    "help_title":        {"zh": "使用说明",       "en": "User Guide"},
    "help_text":         {"zh": "【Measurement Tool 使用说明】\n\n"
                                "1. 打开图片\n"
                                "   点击「文件 → 打开图片」加载 TEM/SEM 图像\n\n"
                                "2. 设定标尺\n"
                                "   点击「工具 → 设定标尺」，在图片标尺两端各点击一次，\n"
                                "   输入标尺的实际长度（nm）\n\n"
                                "3. 测量粒径\n"
                                "   点击「工具 → 测量」，在纳米颗粒直径两端点击，\n"
                                "   程序自动记录粒径，按 Esc 退出测量\n\n"
                                "4. 查看分布\n"
                                "   点击「工具 → 粒径分布」查看直方图和高斯拟合\n\n"
                                "5. 导出数据\n"
                                "   点击「文件 → 导出 CSV」保存测量数据\n\n"
                                "6. 颜色分析\n"
                                "   点击「工具 → 颜色分析」进行颗粒识别和面积统计\n\n"
                                "【快捷操作】\n"
                                "• 右键拖拽：平移图片\n"
                                "• 滚轮：缩放图片\n"
                                "• Ctrl+Z：撤销\n"
                                "• Delete：删除选中测量",
                          "en": "【Measurement Tool User Guide】\n\n"
                                "1. Open Image\n"
                                "   File → Open Image to load TEM/SEM image\n\n"
                                "2. Set Scale\n"
                                "   Tools → Set Scale, click both ends of scale bar,\n"
                                "   enter actual length (nm)\n\n"
                                "3. Measure Particles\n"
                                "   Tools → Measure, click both ends of each particle,\n"
                                "   press Esc to exit\n\n"
                                "4. View Distribution\n"
                                "   Tools → Distribution for histogram & Gaussian fit\n\n"
                                "5. Export Data\n"
                                "   File → Export CSV to save measurements\n\n"
                                "6. Color Analysis\n"
                                "   Tools → Color Analysis for particle detection\n\n"
                                "【Shortcuts】\n"
                                "• Right-drag: Pan\n"
                                "• Scroll: Zoom\n"
                                "• Ctrl+Z: Undo\n"
                                "• Delete: Remove selected"},
    "feedback_title":    {"zh": "提出建议",       "en": "Feedback"},
    "feedback_msg":      {"zh": "如有建议或问题，请发送邮件至:\n\nwangpeijiang0802@gmail.com\n\n感谢您的反馈！",
                          "en": "For suggestions or issues, please email:\n\nwangpeijiang0802@gmail.com\n\nThank you for your feedback!"},
    "licenses_title":    {"zh": "开源许可",       "en": "Open Source Licenses"},
    "licenses_text":     {"zh": "本软件使用了以下开源库:\n\n"
                                "• Python - PSF License\n"
                                "• Tkinter - Python License\n"
                                "• Pillow (PIL) - HPND License\n"
                                "• NumPy - BSD License\n"
                                "• SciPy - BSD License\n"
                                "• Matplotlib - PSF-based License\n\n"
                                "感谢所有开源贡献者！",
                          "en": "This software uses the following open source libraries:\n\n"
                                "• Python - PSF License\n"
                                "• Tkinter - Python License\n"
                                "• Pillow (PIL) - HPND License\n"
                                "• NumPy - BSD License\n"
                                "• SciPy - BSD License\n"
                                "• Matplotlib - PSF-based License\n\n"
                                "Thanks to all open source contributors!"},
    "menu_disclaimer":   {"zh": "免责声明",       "en": "Disclaimer"},
    "disclaimer_title":  {"zh": "免责声明",       "en": "Disclaimer"},
    "disclaimer_text":   {"zh": "【免责声明】\n\n"
                                "本软件按「原样」提供，不提供任何明示或暗示的保证，\n"
                                "包括但不限于对适销性、特定用途适用性和非侵权性的保证。\n\n"
                                "在任何情况下，作者或版权持有人均不对因使用本软件\n"
                                "或与本软件相关的任何索赔、损害或其他责任负责。\n\n"
                                "使用本软件即表示您同意上述条款。\n\n"
                                "© 2025 Peijiang Wang\n"
                                "联系方式: wangpeijiang0802@gmail.com",
                          "en": "【DISCLAIMER】\n\n"
                                "This software is provided \"as is\", without warranty of any kind,\n"
                                "express or implied, including but not limited to the warranties\n"
                                "of merchantability, fitness for a particular purpose and\n"
                                "noninfringement.\n\n"
                                "In no event shall the authors or copyright holders be liable\n"
                                "for any claim, damages or other liability arising from the use\n"
                                "of this software.\n\n"
                                "By using this software, you agree to these terms.\n\n"
                                "© 2025 Peijiang Wang\n"
                                "Contact: wangpeijiang0802@gmail.com"},
}


# ---------------------------------------------------------------------------
# 标尺校准对话框
# ---------------------------------------------------------------------------

class ScaleDialog(tk.Toplevel):
    """带单位选择的标尺校准对话框"""
    def __init__(self, parent, title, px_info, val_label, unit_label, units, default_unit="nm"):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.result = None
        self.result_unit = None

        # 像素长度信息
        ttk.Label(self, text=px_info).pack(padx=20, pady=(15, 10))

        # 输入框和单位选择
        input_frame = ttk.Frame(self)
        input_frame.pack(padx=20, pady=5)

        ttk.Label(input_frame, text=val_label).pack(side=tk.LEFT)
        self.entry = ttk.Entry(input_frame, width=12)
        self.entry.pack(side=tk.LEFT, padx=(5, 10))
        self.entry.focus_set()

        ttk.Label(input_frame, text=unit_label).pack(side=tk.LEFT)
        self.unit_var = tk.StringVar(value=default_unit)
        self.unit_combo = ttk.Combobox(input_frame, textvariable=self.unit_var,
                                        values=units, width=6, state="readonly")
        self.unit_combo.pack(side=tk.LEFT, padx=5)

        # 按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="OK", command=self._on_ok, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel, width=8).pack(side=tk.LEFT, padx=5)

        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self._on_cancel())

        # 居中显示
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")

        self.wait_window(self)

    def _on_ok(self):
        try:
            val = float(self.entry.get())
            if val <= 0:
                raise ValueError
            self.result = val
            self.result_unit = self.unit_var.get()
            self.destroy()
        except ValueError:
            self.entry.focus_set()
            self.entry.select_range(0, tk.END)

    def _on_cancel(self):
        self.result = None
        self.result_unit = None
        self.destroy()


# ---------------------------------------------------------------------------
# 单位转换
# ---------------------------------------------------------------------------

UNIT_TO_NM = {
    "Å":  0.1,
    "nm": 1.0,
    "μm": 1_000.0,
    "mm": 1_000_000.0,
    "cm": 10_000_000.0,
}

SUPPORTED_UNITS = ["Å", "nm", "μm", "mm", "cm"]


def convert_length(value, from_unit, to_unit):
    """在两个单位之间转换长度值。"""
    if from_unit == to_unit:
        return value
    return value * UNIT_TO_NM[from_unit] / UNIT_TO_NM[to_unit]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class Measurement:
    """单次粒径测量记录"""
    __slots__ = ("x1", "y1", "x2", "y2", "pixel_dist", "nm_dist")

    def __init__(self, x1, y1, x2, y2, scale):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.pixel_dist = math.hypot(x2 - x1, y2 - y1)
        self.nm_dist = self.pixel_dist * scale if scale else 0.0

    @property
    def mid_x(self):
        return (self.x1 + self.x2) / 2.0

    @property
    def mid_y(self):
        return (self.y1 + self.y2) / 2.0


class MeasurementGroup:
    """矩形分组区域"""
    __slots__ = ("name", "x1", "y1", "x2", "y2")

    def __init__(self, name, x1, y1, x2, y2):
        self.name = name
        self.x1 = min(x1, x2)
        self.y1 = min(y1, y2)
        self.x2 = max(x1, x2)
        self.y2 = max(y1, y2)

    def contains_measurement(self, m: Measurement) -> bool:
        """判断测量的中点是否在此分组矩形内（含边界）。"""
        mx, my = m.mid_x, m.mid_y
        return self.x1 <= mx <= self.x2 and self.y1 <= my <= self.y2


def assign_groups(measurements, groups):
    """为每个测量分配分组标签，返回与 measurements 等长的列表。"""
    labels = []
    for m in measurements:
        assigned = ""
        for g in groups:
            if g.contains_measurement(m):
                assigned = g.name
                break
        labels.append(assigned)
    return labels


def write_csv_with_groups(writer, measurements, groups, group_labels,
                          scale=1.0, lang="zh",
                          calib_unit="nm", display_unit=None):
    """将测量数据（含分组）写入 CSV writer。"""
    if display_unit is None:
        display_unit = calib_unit

    def _t(key, **kwargs):
        entry = STRINGS.get(key)
        if entry is None:
            return key
        raw = entry.get(lang, entry.get("zh", key))
        if kwargs:
            return raw.format(**kwargs)
        return raw

    def _conv(calib_val):
        return convert_length(calib_val, calib_unit, display_unit)

    unit = display_unit if scale > 0 else "px"
    has_groups = len(groups) > 0

    # Header
    header = ["#", _t("csv_diameter", u=unit), _t("csv_pixel_dist"),
              "X1", "Y1", "X2", "Y2"]
    if has_groups:
        header.append(_t("csv_group"))
    writer.writerow(header)

    # Data rows
    for i, m in enumerate(measurements):
        d = _conv(m.nm_dist) if scale > 0 else m.pixel_dist
        row = [i + 1, f"{d:.4f}", f"{m.pixel_dist:.4f}",
               f"{m.x1:.2f}", f"{m.y1:.2f}",
               f"{m.x2:.2f}", f"{m.y2:.2f}"]
        if has_groups:
            row.append(group_labels[i])
        writer.writerow(row)

    # Overall statistics
    if scale > 0:
        vals = [_conv(m.nm_dist) for m in measurements]
    else:
        vals = [m.pixel_dist for m in measurements]
    n = len(vals)
    if n > 0:
        writer.writerow([])
        writer.writerow([_t("csv_stat"), _t("csv_value")])
        mean = np.mean(vals)
        std_val = np.std(vals, ddof=1) if n > 1 else 0.0
        writer.writerow([_t("csv_count"), n])
        writer.writerow([_t("csv_mean"), f"{mean:.4f}"])
        writer.writerow([_t("csv_std"), f"{std_val:.4f}"])
        writer.writerow([_t("csv_min"), f"{min(vals):.4f}"])
        writer.writerow([_t("csv_max"), f"{max(vals):.4f}"])
        if scale > 0:
            writer.writerow([_t("csv_scale"), f"{scale:.6f}"])

        # Gaussian fit
        if n > 1 and std_val > 0:
            writer.writerow([])
            writer.writerow([_t("csv_gauss_title")])
            writer.writerow([_t("csv_gauss_formula"),
                             "f(x) = (1/(σ√(2π))) × exp(-(x-μ)²/(2σ²))"])
            writer.writerow([_t("csv_gauss_mu"), f"{mean:.4f}"])
            writer.writerow([_t("csv_gauss_sigma"), f"{std_val:.4f}"])

            writer.writerow([])
            vals_arr = np.array(vals)
            x_fit = np.linspace(vals_arr.min() - std_val,
                                vals_arr.max() + std_val, 200)
            y_fit = norm.pdf(x_fit, mean, std_val)
            writer.writerow([_t("csv_gauss_curve")])
            writer.writerow([_t("csv_gauss_x", u=unit), _t("csv_gauss_y")])
            for xv, yv in zip(x_fit, y_fit):
                writer.writerow([f"{xv:.4f}", f"{yv:.6f}"])

    # Per-group statistics
    if has_groups:
        for g in groups:
            if scale > 0:
                g_vals = [_conv(m.nm_dist) for m, lbl
                          in zip(measurements, group_labels) if lbl == g.name]
            else:
                g_vals = [m.pixel_dist for m, lbl
                          in zip(measurements, group_labels) if lbl == g.name]
            gn = len(g_vals)
            if gn == 0:
                continue
            writer.writerow([])
            writer.writerow([_t("csv_group_stat", name=g.name)])
            writer.writerow([_t("csv_stat"), _t("csv_value")])
            g_mean = np.mean(g_vals)
            g_std = np.std(g_vals, ddof=1) if gn > 1 else 0.0
            writer.writerow([_t("csv_count"), gn])
            writer.writerow([_t("csv_mean"), f"{g_mean:.4f}"])
            writer.writerow([_t("csv_std"), f"{g_std:.4f}"])
            writer.writerow([_t("csv_min"), f"{min(g_vals):.4f}"])
            writer.writerow([_t("csv_max"), f"{max(g_vals):.4f}"])


# ---------------------------------------------------------------------------
# RGB → HSV 转换 (纯 numpy，不依赖 cv2)
# ---------------------------------------------------------------------------

def _rgb_to_hsv_array(rgb: np.ndarray) -> np.ndarray:
    """将 (H, W, 3) uint8 RGB 数组转为 HSV float 数组。

    输出范围: H 0-180, S 0-255, V 0-255 (与 OpenCV 约定一致)。
    """
    rgb_f = rgb.astype(np.float32) / 255.0
    r, g, b = rgb_f[..., 0], rgb_f[..., 1], rgb_f[..., 2]

    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    # Hue
    h = np.zeros_like(delta)
    mask_r = (cmax == r) & (delta > 0)
    mask_g = (cmax == g) & (delta > 0)
    mask_b = (cmax == b) & (delta > 0)
    h[mask_r] = 60.0 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6.0)
    h[mask_g] = 60.0 * (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2.0)
    h[mask_b] = 60.0 * (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4.0)
    h = h / 2.0  # 0-360 → 0-180

    # Saturation
    safe_cmax = np.where(cmax > 0, cmax, 1.0)
    s = np.where(cmax > 0, delta / safe_cmax, 0.0) * 255.0

    # Value
    v = cmax * 255.0

    return np.stack([h, s, v], axis=-1)


# ---------------------------------------------------------------------------
# 颜色分析窗口
# ---------------------------------------------------------------------------

class ColorAnalysisWindow(tk.Toplevel):
    """取色后弹出的颜色分析窗口，包含容差调节、预览、统计和导出。"""

    _PREVIEW_MAX = 600  # 预览画布最大边长
    _PALETTE = [
        (230, 25, 75),   (60, 180, 75),   (255, 225, 25),  (0, 130, 200),
        (245, 130, 48),  (145, 30, 180),  (70, 240, 240),  (240, 50, 230),
        (210, 245, 60),  (250, 190, 212), (0, 128, 128),   (220, 190, 255),
        (170, 110, 40),  (255, 250, 200), (128, 0, 0),     (170, 255, 195),
        (128, 128, 0),   (255, 215, 180), (0, 0, 128),     (128, 128, 128),
    ]

    def __init__(self, parent, app, color_points):
        """
        Parameters
        ----------
        color_points : list[tuple[int,int,int]]
            一个或多个 (R, G, B) 取色点。多点时取 HSV 平均值作为中心，
            并根据各点 HSV 散布自动设置初始容差。
        """
        super().__init__(parent)
        self.app = app
        self.color_points = list(color_points)
        n_pts = len(self.color_points)

        # 预计算整张图的 HSV
        img_arr = np.array(app.pil_image)  # (H, W, 3) uint8
        self.img_rgb = img_arr
        self.img_hsv = _rgb_to_hsv_array(img_arr)
        self.img_h_total, self.img_w_total = img_arr.shape[:2]

        # 计算每个取色点的 HSV
        pts_arr = np.array(self.color_points, dtype=np.uint8).reshape(1, n_pts, 3)
        pts_hsv = _rgb_to_hsv_array(pts_arr)[0]  # (n_pts, 3)
        h_vals = pts_hsv[:, 0]
        s_vals = pts_hsv[:, 1]
        v_vals = pts_hsv[:, 2]

        # H 通道的环形平均
        h_rad = h_vals * (np.pi / 90.0)  # 0-180 → 0-2π
        mean_sin = np.mean(np.sin(h_rad))
        mean_cos = np.mean(np.cos(h_rad))
        self.center_h = float(np.arctan2(mean_sin, mean_cos) * (90.0 / np.pi)) % 180.0
        self.center_s = float(np.mean(s_vals))
        self.center_v = float(np.mean(v_vals))

        # 平均 RGB (用于显示色块)
        avg_r = int(round(sum(p[0] for p in self.color_points) / n_pts))
        avg_g = int(round(sum(p[1] for p in self.color_points) / n_pts))
        avg_b = int(round(sum(p[2] for p in self.color_points) / n_pts))
        self.center_rgb = (avg_r, avg_g, avg_b)

        # 根据取色点散布计算初始容差
        if n_pts > 1:
            h_diffs = np.abs(h_vals - self.center_h)
            h_diffs = np.minimum(h_diffs, 180.0 - h_diffs)
            init_h = int(min(90, max(5, np.max(h_diffs) * 1.5 + 5)))
            init_s = int(min(128, max(10, np.max(np.abs(s_vals - self.center_s)) * 1.5 + 10)))
            init_v = int(min(128, max(10, np.max(np.abs(v_vals - self.center_v)) * 1.5 + 10)))
        else:
            init_h, init_s, init_v = 15, 50, 50
        self._init_tol = (init_h, init_s, init_v)

        # 缩略图比例
        scale = min(self._PREVIEW_MAX / self.img_w_total,
                    self._PREVIEW_MAX / self.img_h_total, 1.0)
        self.thumb_w = max(1, int(self.img_w_total * scale))
        self.thumb_h = max(1, int(self.img_h_total * scale))
        self.thumb_rgb = np.array(
            app.pil_image.resize((self.thumb_w, self.thumb_h), Image.BILINEAR)
        )

        # 连通域结果缓存
        self.particle_areas: list[int] = []
        self.mask: np.ndarray | None = None
        self._overlay_pil: Image.Image | None = None
        self._centroids_thumb: list[tuple[float, float]] = []

        # 预览缩放/平移状态
        self._pv_zoom = 1.0
        self._pv_ox = 0.0
        self._pv_oy = 0.0
        self._pv_pan_start = None

        # 手动分割状态
        self._cut_mask = np.zeros((self.img_h_total, self.img_w_total), dtype=bool)
        self._cut_strokes: list[np.ndarray] = []
        self._split_drawing = False
        self._split_points: list[tuple[float, float]] = []

        # 添加颜色点状态
        self._add_color_mode = False
        self._added_colors: list[tuple[int, int, int]] = []  # 新添加的 (R, G, B) 列表

        self.title(self._t("ca_title"))
        self.geometry("820x780")
        self.minsize(640, 600)

        self._build_ui()
        self._update_preview()

    # -- i18n helper (委托给 app) --
    def _t(self, key, **kwargs):
        return self.app._t(key, **kwargs)

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill=tk.X)

        # 色块 + RGB/HSV
        color_hex = "#%02x%02x%02x" % self.center_rgb
        self.color_swatch = tk.Canvas(top, width=32, height=32,
                                      highlightthickness=1, highlightbackground="#888")
        self.color_swatch.create_rectangle(0, 0, 32, 32, fill=color_hex, outline="")
        self.color_swatch.pack(side=tk.LEFT, padx=(0, 8))

        info_frame = ttk.Frame(top)
        info_frame.pack(side=tk.LEFT)
        r, g, b = self.center_rgb
        ttk.Label(info_frame, text=self._t("ca_rgb_fmt", r=r, g=g, b=b)).pack(anchor=tk.W)
        hsv_line = self._t("ca_hsv_fmt", h=self.center_h,
                           s=self.center_s, v=self.center_v)
        if len(self.color_points) > 1:
            hsv_line += "  " + self._t("ca_npoints_fmt", n=len(self.color_points))
        ttk.Label(info_frame, text=hsv_line).pack(anchor=tk.W)

        # 多点时显示各点小色块
        if len(self.color_points) > 1:
            pts_frame = ttk.Frame(top)
            pts_frame.pack(side=tk.LEFT, padx=(12, 0))
            for pr, pg, pb in self.color_points:
                ph = "#%02x%02x%02x" % (pr, pg, pb)
                c = tk.Canvas(pts_frame, width=14, height=14,
                              highlightthickness=1, highlightbackground="#aaa")
                c.create_rectangle(0, 0, 14, 14, fill=ph, outline="")
                c.pack(side=tk.LEFT, padx=1)

        # ---- 容差滑块 ----
        tol_frame = ttk.LabelFrame(self, text=self._t("ca_tolerance"), padding=6)
        tol_frame.pack(fill=tk.X, padx=6, pady=(4, 2))

        init_h, init_s, init_v = self._init_tol
        self.h_tol = tk.IntVar(value=init_h)
        self.s_tol = tk.IntVar(value=init_s)
        self.v_tol = tk.IntVar(value=init_v)
        self.min_area = tk.IntVar(value=10)

        for label_key, var, from_, to_ in [
            ("ca_h_tol", self.h_tol, 0, 90),
            ("ca_s_tol", self.s_tol, 0, 128),
            ("ca_v_tol", self.v_tol, 0, 128),
        ]:
            row = ttk.Frame(tol_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=self._t(label_key), width=8).pack(side=tk.LEFT)
            sc = ttk.Scale(row, from_=from_, to=to_, variable=var, orient=tk.HORIZONTAL,
                           command=lambda *_a: self._on_slider_change())
            sc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
            ttk.Label(row, textvariable=var, width=5).pack(side=tk.LEFT)

        # 最小面积
        row_area = ttk.Frame(tol_frame)
        row_area.pack(fill=tk.X, pady=1)
        ttk.Label(row_area, text=self._t("ca_min_area"), width=8).pack(side=tk.LEFT)
        sc_area = ttk.Scale(row_area, from_=0, to=500, variable=self.min_area,
                            orient=tk.HORIZONTAL,
                            command=lambda *_a: self._on_slider_change())
        sc_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        lbl_area = ttk.Frame(row_area)
        lbl_area.pack(side=tk.LEFT)
        ttk.Label(lbl_area, textvariable=self.min_area, width=4).pack(side=tk.LEFT)
        ttk.Label(lbl_area, text=self._t("ca_min_area_unit")).pack(side=tk.LEFT)

        # ---- 预览画布 ----
        pf = ttk.LabelFrame(self, text=self._t("ca_preview"), padding=4)
        pf.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        self.preview_canvas = tk.Canvas(pf, bg="#222222", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", lambda e: self._render_preview())
        # 预览缩放 & 平移
        self.preview_canvas.bind("<MouseWheel>", self._pv_on_scroll)
        self.preview_canvas.bind("<Button-4>", self._pv_on_scroll_up)
        self.preview_canvas.bind("<Button-5>", self._pv_on_scroll_down)
        self.preview_canvas.bind("<ButtonPress-3>", self._pv_on_pan_start)
        self.preview_canvas.bind("<B3-Motion>", self._pv_on_pan_drag)
        self.preview_canvas.bind("<ButtonRelease-3>", self._pv_on_pan_end)
        self.preview_canvas.bind("<Double-Button-1>", self._pv_reset_view)
        # 手动分割: 左键拖拽
        self.preview_canvas.bind("<ButtonPress-1>", self._pv_on_left_press)
        self.preview_canvas.bind("<B1-Motion>", self._pv_on_left_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._pv_on_left_release)
        self._preview_tk = None  # keep reference

        # ---- 统计 + 颗粒列表 + 按钮 ----
        bottom = ttk.Frame(self, padding=4)
        bottom.pack(fill=tk.BOTH, padx=6, pady=(2, 6))

        self.stat_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.stat_var, justify=tk.LEFT).pack(anchor=tk.W)

        list_frame = ttk.LabelFrame(bottom, text=self._t("ca_particle_list"), padding=4)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 4))

        unit = "nm\u00b2" if self.app.scale > 0 else "px\u00b2"
        cols = ("ca_col_id", "ca_col_area")
        self.ptree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                  height=6, selectmode="extended")
        self.ptree.heading("ca_col_id", text=self._t("ca_col_id"), anchor=tk.CENTER)
        self.ptree.heading("ca_col_area", text=self._t("ca_col_area", u=unit), anchor=tk.CENTER)
        self.ptree.column("ca_col_id", width=50, anchor=tk.CENTER)
        self.ptree.column("ca_col_area", width=120, anchor=tk.CENTER)

        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.ptree.yview)
        self.ptree.configure(yscrollcommand=sb.set)
        self.ptree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        btn_row = ttk.Frame(bottom)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text=self._t("ca_area_dist"),
                   command=self._show_area_histogram).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text=self._t("ca_export_csv"),
                   command=self._export_area_csv).pack(side=tk.LEFT, padx=2)

        # ---- 手动分割控件 ----
        split_row = ttk.Frame(bottom)
        split_row.pack(fill=tk.X, pady=(4, 0))
        self._split_mode = tk.BooleanVar(value=False)
        self._split_mode.trace_add("write", lambda *_a: self._on_split_mode_change())
        ttk.Checkbutton(split_row, text=self._t("ca_manual_split"),
                        variable=self._split_mode).pack(side=tk.LEFT, padx=2)
        ttk.Label(split_row, text=self._t("ca_brush_width")).pack(side=tk.LEFT, padx=(6, 0))
        self._brush_width = tk.IntVar(value=3)
        ttk.Spinbox(split_row, from_=1, to=30, textvariable=self._brush_width,
                    width=4).pack(side=tk.LEFT, padx=2)
        ttk.Button(split_row, text=self._t("ca_undo_split"),
                   command=self._undo_split).pack(side=tk.LEFT, padx=2)
        ttk.Button(split_row, text=self._t("ca_clear_splits"),
                   command=self._clear_splits).pack(side=tk.LEFT, padx=2)
        self._split_hint_var = tk.StringVar(value="")
        ttk.Label(split_row, textvariable=self._split_hint_var,
                  foreground="gray").pack(side=tk.LEFT, padx=6)

        # ---- 添加颜色点控件 ----
        color_row = ttk.Frame(bottom)
        color_row.pack(fill=tk.X, pady=(4, 0))
        self._add_color_var = tk.BooleanVar(value=False)
        self._add_color_var.trace_add("write", lambda *_a: self._on_add_color_mode_change())
        ttk.Checkbutton(color_row, text=self._t("ca_add_color"),
                        variable=self._add_color_var).pack(side=tk.LEFT, padx=2)
        self._auto_tol_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(color_row, text=self._t("ca_auto_tol"),
                        variable=self._auto_tol_var).pack(side=tk.LEFT, padx=2)
        ttk.Button(color_row, text=self._t("ca_undo_color"),
                   command=self._undo_add_color).pack(side=tk.LEFT, padx=2)
        self._add_color_hint_var = tk.StringVar(value="")
        ttk.Label(color_row, textvariable=self._add_color_hint_var,
                  foreground="gray").pack(side=tk.LEFT, padx=6)

        # 动态颜色小色块容器
        self._color_swatches_frame = ttk.Frame(top)
        self._color_swatches_frame.pack(side=tk.RIGHT, padx=(12, 0))
        self._update_color_swatches()

        # 防抖定时器 id
        self._pending_update: str | None = None

    # --------------------------------------------------------- 计算逻辑
    def _on_slider_change(self):
        """滑块变化时使用 after 防抖，避免频繁重算。"""
        if self._pending_update is not None:
            self.after_cancel(self._pending_update)
        self._pending_update = self.after(80, self._update_preview)

    def _compute_mask(self):
        """根据当前 HSV 中心和容差计算二值 mask、标记数组、面积列表和质心列表。

        Returns:
            (mask, labeled_remapped, areas_list, centroids)
            labeled_remapped 中 1=最大颗粒, 2=次大, …
            centroids 为 [(cx, cy), …] 对应每个颗粒 (图像坐标)
        """
        h_tol = self.h_tol.get()
        s_tol = self.s_tol.get()
        v_tol = self.v_tol.get()
        min_a = self.min_area.get()

        h_img = self.img_hsv[..., 0]
        s_img = self.img_hsv[..., 1]
        v_img = self.img_hsv[..., 2]

        # H 通道环形距离 (0-180 范围)
        h_diff = np.abs(h_img - self.center_h)
        h_diff = np.minimum(h_diff, 180.0 - h_diff)
        h_match = h_diff <= h_tol

        s_match = np.abs(s_img - self.center_s) <= s_tol
        v_match = np.abs(v_img - self.center_v) <= v_tol

        mask = h_match & s_match & v_match

        # 应用手动分割切割线
        if self._cut_mask.any():
            mask = mask & ~self._cut_mask

        labeled, num_features = ndimage_label(mask)
        empty_labeled = np.zeros_like(mask, dtype=np.int32)

        if num_features == 0:
            return mask, empty_labeled, [], []

        # 计算每个连通域面积
        component_ids = np.arange(1, num_features + 1)
        areas = np.bincount(labeled.ravel(), minlength=num_features + 1)[1:]

        # 过滤小面积
        if min_a > 0:
            keep = areas >= min_a
            remove_ids = component_ids[~keep]
            if len(remove_ids) > 0:
                remove_mask = np.isin(labeled, remove_ids)
                mask[remove_mask] = False
            kept_ids = component_ids[keep]
            kept_areas = areas[keep]
        else:
            kept_ids = component_ids
            kept_areas = areas

        if len(kept_areas) == 0:
            return mask, empty_labeled, [], []

        # 按面积降序排序
        order = np.argsort(kept_areas)[::-1]
        kept_areas = kept_areas[order]
        kept_ids = kept_ids[order]

        # 重映射标签: 1=最大, 2=次大, …
        remap = np.zeros(num_features + 1, dtype=np.int32)
        for new_id, old_id in enumerate(kept_ids, 1):
            remap[old_id] = new_id
        labeled_remapped = remap[labeled]

        # 用 bincount 计算每个颗粒质心
        n = len(kept_areas)
        img_h, img_w = labeled_remapped.shape
        y_coords, x_coords = np.mgrid[:img_h, :img_w]
        flat = labeled_remapped.ravel()
        counts = np.bincount(flat, minlength=n + 1)
        sum_x = np.bincount(flat, weights=x_coords.ravel(), minlength=n + 1)
        sum_y = np.bincount(flat, weights=y_coords.ravel(), minlength=n + 1)
        centroids = []
        for i in range(1, n + 1):
            if counts[i] > 0:
                centroids.append((sum_x[i] / counts[i], sum_y[i] / counts[i]))
            else:
                centroids.append((0.0, 0.0))

        return mask, labeled_remapped, kept_areas.tolist(), centroids

    def _update_preview(self):
        """重算 mask，更新预览画布、统计和颗粒列表。"""
        self._pending_update = None
        self.mask, labeled, self.particle_areas, centroids_full = self._compute_mask()
        n_particles = len(self.particle_areas)

        # -- 生成彩色遮罩预览图 (缩略图尺寸) --
        # 缩小 labeled 到缩略图尺寸
        labeled_pil = Image.fromarray(labeled.astype(np.int32), mode="I")
        labeled_thumb = np.array(
            labeled_pil.resize((self.thumb_w, self.thumb_h), Image.NEAREST),
            dtype=np.int32,
        )

        overlay = self.thumb_rgb.copy()
        for i in range(1, n_particles + 1):
            color = np.array(
                self._PALETTE[(i - 1) % len(self._PALETTE)], dtype=np.float32
            )
            region = labeled_thumb == i
            if region.any():
                overlay[region] = (
                    overlay[region] * 0.4 + color * 0.6
                ).astype(np.uint8)

        self._overlay_pil = Image.fromarray(overlay)

        # 将质心从原图坐标换算到缩略图坐标
        sx = self.thumb_w / self.img_w_total
        sy = self.thumb_h / self.img_h_total
        self._centroids_thumb = [(cx * sx, cy * sy) for cx, cy in centroids_full]

        self._render_preview()

        # -- 统计 --
        total_px = int(np.sum(self.particle_areas)) if n_particles > 0 else 0
        total_pixels = self.img_h_total * self.img_w_total
        coverage = total_px / total_pixels * 100.0 if total_pixels > 0 else 0.0

        has_scale = self.app.scale > 0
        nm2_per_px2 = self.app.scale ** 2 if has_scale else 0.0

        if has_scale:
            total_area_str = self._t("ca_total_area_nm", a=f"{total_px * nm2_per_px2:.1f}")
        else:
            total_area_str = self._t("ca_total_area_px", a=total_px)

        self.stat_var.set(
            f"{self._t('ca_particle_count', n=n_particles)}  |  "
            f"{total_area_str}  |  "
            f"{self._t('ca_coverage', c=coverage)}"
        )

        # -- 颗粒列表 --
        self.ptree.delete(*self.ptree.get_children())
        unit = "nm\u00b2" if has_scale else "px\u00b2"
        self.ptree.heading("ca_col_area", text=self._t("ca_col_area", u=unit))
        for i, a_px in enumerate(self.particle_areas, 1):
            if has_scale:
                val = f"{a_px * nm2_per_px2:.2f}"
            else:
                val = str(a_px)
            self.ptree.insert("", tk.END, iid=str(i), values=(i, val))

    # --------------------------------------------------------- 手动分割
    def _on_split_mode_change(self):
        if self._split_mode.get():
            # 关闭添加颜色点模式
            self._add_color_var.set(False)
            self.preview_canvas.config(cursor="crosshair")
            self._split_hint_var.set(self._t("ca_split_hint"))
        else:
            self.preview_canvas.config(cursor="")
            self._split_hint_var.set("")
            self._split_drawing = False

    # --------------------------------------------------------- 添加颜色点
    def _on_add_color_mode_change(self):
        if self._add_color_var.get():
            # 关闭手动分割模式
            self._split_mode.set(False)
            self.preview_canvas.config(cursor="crosshair")
            self._add_color_hint_var.set(self._t("ca_add_color_hint"))
        else:
            self.preview_canvas.config(cursor="")
            self._add_color_hint_var.set("")

    def _add_color_at_position(self, cx, cy):
        """在画布坐标 (cx, cy) 处添加颜色点。"""
        # 画布坐标 → 缩略图坐标 → 原图坐标
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        base_s = min(cw / self.thumb_w, ch / self.thumb_h)
        actual_s = base_s * self._pv_zoom
        img_cx = (cw - self.thumb_w * actual_s) / 2 + self._pv_ox
        img_cy = (ch - self.thumb_h * actual_s) / 2 + self._pv_oy

        # 缩略图坐标
        tx = (cx - img_cx) / actual_s
        ty = (cy - img_cy) / actual_s

        # 检查是否在图像范围内
        if tx < 0 or tx >= self.thumb_w or ty < 0 or ty >= self.thumb_h:
            return

        # 原图坐标
        ix = int(tx * self.img_w_total / self.thumb_w)
        iy = int(ty * self.img_h_total / self.thumb_h)
        ix = max(0, min(ix, self.img_w_total - 1))
        iy = max(0, min(iy, self.img_h_total - 1))

        # 获取该像素的 RGB 值
        r, g, b = self.img_rgb[iy, ix]
        new_color = (int(r), int(g), int(b))

        # 添加到列表
        self._added_colors.append(new_color)

        # 重新计算 HSV 中心
        self._recalculate_hsv_center()

        # 更新颜色小色块显示
        self._update_color_swatches()

        # 更新提示
        total_n = len(self.color_points) + len(self._added_colors)
        self._add_color_hint_var.set(self._t("ca_color_added", n=total_n))

        # 刷新预览
        self._update_preview()

    def _undo_add_color(self):
        """撤销最后一个添加的颜色点。"""
        if not self._added_colors:
            self._add_color_hint_var.set(self._t("ca_no_color_undo"))
            return

        self._added_colors.pop()

        # 重新计算 HSV 中心
        self._recalculate_hsv_center()

        # 更新颜色小色块显示
        self._update_color_swatches()

        # 更新提示
        total_n = len(self.color_points) + len(self._added_colors)
        self._add_color_hint_var.set(self._t("ca_color_undone", n=total_n))

        # 刷新预览
        self._update_preview()

    def _recalculate_hsv_center(self):
        """根据所有颜色点重新计算 HSV 中心和容差。"""
        # 合并原始颜色点和新添加的颜色点
        all_colors = list(self.color_points) + self._added_colors
        n_pts = len(all_colors)

        if n_pts == 0:
            return

        # 计算每个颜色点的 HSV
        pts_arr = np.array(all_colors, dtype=np.uint8).reshape(1, n_pts, 3)
        pts_hsv = _rgb_to_hsv_array(pts_arr)[0]  # (n_pts, 3)
        h_vals = pts_hsv[:, 0]
        s_vals = pts_hsv[:, 1]
        v_vals = pts_hsv[:, 2]

        # H 通道的环形平均
        h_rad = h_vals * (np.pi / 90.0)  # 0-180 → 0-2π
        mean_sin = np.mean(np.sin(h_rad))
        mean_cos = np.mean(np.cos(h_rad))
        self.center_h = float(np.arctan2(mean_sin, mean_cos) * (90.0 / np.pi)) % 180.0
        self.center_s = float(np.mean(s_vals))
        self.center_v = float(np.mean(v_vals))

        # 更新平均 RGB (用于显示色块)
        avg_r = int(round(sum(p[0] for p in all_colors) / n_pts))
        avg_g = int(round(sum(p[1] for p in all_colors) / n_pts))
        avg_b = int(round(sum(p[2] for p in all_colors) / n_pts))
        self.center_rgb = (avg_r, avg_g, avg_b)

        # 更新主色块
        color_hex = "#%02x%02x%02x" % self.center_rgb
        self.color_swatch.delete("all")
        self.color_swatch.create_rectangle(0, 0, 32, 32, fill=color_hex, outline="")

        # 如果启用了自动调整容差，则根据颜色点散布更新容差
        if self._auto_tol_var.get() and n_pts > 1:
            h_diffs = np.abs(h_vals - self.center_h)
            h_diffs = np.minimum(h_diffs, 180.0 - h_diffs)
            new_h = int(min(90, max(5, np.max(h_diffs) * 1.5 + 5)))
            new_s = int(min(128, max(10, np.max(np.abs(s_vals - self.center_s)) * 1.5 + 10)))
            new_v = int(min(128, max(10, np.max(np.abs(v_vals - self.center_v)) * 1.5 + 10)))
            self.h_tol.set(new_h)
            self.s_tol.set(new_s)
            self.v_tol.set(new_v)

    def _update_color_swatches(self):
        """更新显示所有颜色点的小色块。"""
        # 清除旧的色块
        for widget in self._color_swatches_frame.winfo_children():
            widget.destroy()

        # 显示所有颜色点（原始 + 新添加）
        all_colors = list(self.color_points) + self._added_colors
        if len(all_colors) <= 1:
            return

        for i, (r, g, b) in enumerate(all_colors):
            ph = "#%02x%02x%02x" % (r, g, b)
            # 新添加的颜色点用不同的边框颜色
            border_color = "#0a0" if i >= len(self.color_points) else "#aaa"
            c = tk.Canvas(self._color_swatches_frame, width=14, height=14,
                          highlightthickness=1, highlightbackground=border_color)
            c.create_rectangle(0, 0, 14, 14, fill=ph, outline="")
            c.pack(side=tk.LEFT, padx=1)

    def _pv_on_left_press(self, event):
        # 添加颜色点模式优先处理
        if self._add_color_var.get():
            self._add_color_at_position(event.x, event.y)
            return
        if not self._split_mode.get():
            return
        self._split_drawing = True
        self._split_points = [(event.x, event.y)]

    def _pv_on_left_drag(self, event):
        if not self._split_drawing:
            return
        self._split_points.append((event.x, event.y))
        if len(self._split_points) >= 2:
            x0, y0 = self._split_points[-2]
            x1, y1 = self._split_points[-1]
            # 画笔宽度换算到画布像素
            cw = self.preview_canvas.winfo_width()
            ch = self.preview_canvas.winfo_height()
            base_s = min(cw / self.thumb_w, ch / self.thumb_h)
            actual_s = base_s * self._pv_zoom
            img_to_cv = actual_s * self.thumb_w / self.img_w_total
            cv_w = max(2, self._brush_width.get() * img_to_cv)
            self.preview_canvas.create_line(
                x0, y0, x1, y1, fill="red", width=cv_w,
                capstyle=tk.ROUND, tags="split_draw",
            )

    def _pv_on_left_release(self, event):
        if not self._split_drawing:
            return
        self._split_drawing = False
        self.preview_canvas.delete("split_draw")
        if len(self._split_points) >= 2:
            self._apply_split_stroke(self._split_points)
        self._split_points = []

    def _apply_split_stroke(self, canvas_pts):
        """将画布上的笔画转为图像坐标，写入切割蒙版，刷新预览。"""
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        base_s = min(cw / self.thumb_w, ch / self.thumb_h)
        actual_s = base_s * self._pv_zoom
        img_cx = (cw - self.thumb_w * actual_s) / 2 + self._pv_ox
        img_cy = (ch - self.thumb_h * actual_s) / 2 + self._pv_oy
        t2i_x = self.img_w_total / self.thumb_w
        t2i_y = self.img_h_total / self.thumb_h

        img_pts = []
        for cx, cy in canvas_pts:
            tx = (cx - img_cx) / actual_s
            ty = (cy - img_cy) / actual_s
            img_pts.append((tx * t2i_x, ty * t2i_y))

        radius = max(1.0, self._brush_width.get() / 2.0)
        stroke = np.zeros((self.img_h_total, self.img_w_total), dtype=bool)
        for k in range(len(img_pts) - 1):
            self._draw_line_on_mask(stroke, *img_pts[k], *img_pts[k + 1], radius)

        self._cut_strokes.append(stroke)
        self._cut_mask |= stroke
        self._update_preview()

    @staticmethod
    def _draw_line_on_mask(mask, x0, y0, x1, y1, radius):
        """在布尔蒙版上画一条宽为 2*radius 的线段 (向量化)。"""
        h, w = mask.shape
        bx0 = max(0, int(min(x0, x1) - radius) - 1)
        by0 = max(0, int(min(y0, y1) - radius) - 1)
        bx1 = min(w, int(max(x0, x1) + radius) + 2)
        by1 = min(h, int(max(y0, y1) + radius) + 2)
        if bx0 >= bx1 or by0 >= by1:
            return
        yy, xx = np.mgrid[by0:by1, bx0:bx1]
        dx, dy = x1 - x0, y1 - y0
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 1e-6:
            dist_sq = (xx - x0) ** 2 + (yy - y0) ** 2
        else:
            t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / seg_len_sq, 0.0, 1.0)
            px = x0 + t * dx
            py = y0 + t * dy
            dist_sq = (xx - px) ** 2 + (yy - py) ** 2
        mask[by0:by1, bx0:bx1] |= (dist_sq <= radius * radius)

    def _undo_split(self):
        if not self._cut_strokes:
            return
        self._cut_strokes.pop()
        self._cut_mask = np.zeros((self.img_h_total, self.img_w_total), dtype=bool)
        for s in self._cut_strokes:
            self._cut_mask |= s
        self._update_preview()

    def _clear_splits(self):
        if not self._cut_strokes:
            return
        self._cut_strokes.clear()
        self._cut_mask[:] = False
        self._update_preview()

    # --------------------------------------------------------- 预览缩放/平移
    def _pv_on_scroll(self, event):
        factor = 1.2 if event.delta > 0 else 1 / 1.2
        self._pv_zoom_at(event.x, event.y, factor)

    def _pv_on_scroll_up(self, event):
        self._pv_zoom_at(event.x, event.y, 1.2)

    def _pv_on_scroll_down(self, event):
        self._pv_zoom_at(event.x, event.y, 1 / 1.2)

    def _pv_zoom_at(self, cx, cy, factor):
        """以鼠标位置 (cx, cy) 为中心缩放预览。"""
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        old = self._pv_zoom
        self._pv_zoom = max(0.5, min(self._pv_zoom * factor, 20.0))
        r = self._pv_zoom / old
        # 正确的 zoom-at-point 公式：保持鼠标下的图像点不动
        self._pv_ox = (1 - r) * (cx - cw / 2) + r * self._pv_ox
        self._pv_oy = (1 - r) * (cy - ch / 2) + r * self._pv_oy
        self._render_preview()

    def _pv_on_pan_start(self, event):
        self._pv_pan_start = (event.x, event.y, self._pv_ox, self._pv_oy)

    def _pv_on_pan_drag(self, event):
        if self._pv_pan_start is None:
            return
        sx, sy, oox, ooy = self._pv_pan_start
        self._pv_ox = oox + (event.x - sx)
        self._pv_oy = ooy + (event.y - sy)
        self._render_preview()

    def _pv_on_pan_end(self, event):
        self._pv_pan_start = None

    def _pv_reset_view(self, event=None):
        if self._split_mode.get():
            return
        self._pv_zoom = 1.0
        self._pv_ox = 0.0
        self._pv_oy = 0.0
        self._render_preview()

    # --------------------------------------------------------- 预览渲染
    def _render_preview(self):
        """将缓存的遮罩预览图按缩放/平移状态渲染到画布，叠加颗粒编号。"""
        if self._overlay_pil is None:
            return
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 2 or ch < 2:
            return

        # 基准缩放 (适应窗口) × 用户缩放
        base_scale = min(cw / self.thumb_w, ch / self.thumb_h)
        actual_scale = base_scale * self._pv_zoom

        # 图像左上角在画布上的位置 (居中 + 用户偏移)
        img_cx = (cw - self.thumb_w * actual_scale) / 2 + self._pv_ox
        img_cy = (ch - self.thumb_h * actual_scale) / 2 + self._pv_oy

        # 可见区域在缩略图中的范围 (裁剪优化)
        t_x0 = max(0, int(-img_cx / actual_scale))
        t_y0 = max(0, int(-img_cy / actual_scale))
        t_x1 = min(self.thumb_w, int((cw - img_cx) / actual_scale) + 1)
        t_y1 = min(self.thumb_h, int((ch - img_cy) / actual_scale) + 1)

        self.preview_canvas.delete("all")

        if t_x1 <= t_x0 or t_y1 <= t_y0:
            return

        crop = self._overlay_pil.crop((t_x0, t_y0, t_x1, t_y1))
        crop_w = max(1, int((t_x1 - t_x0) * actual_scale))
        crop_h = max(1, int((t_y1 - t_y0) * actual_scale))

        resample = Image.NEAREST if self._pv_zoom > 3 else Image.BILINEAR
        resized = crop.resize((crop_w, crop_h), resample)
        self._preview_tk = ImageTk.PhotoImage(resized)

        px = img_cx + t_x0 * actual_scale
        py = img_cy + t_y0 * actual_scale
        self.preview_canvas.create_image(px, py, anchor=tk.NW, image=self._preview_tk)

        # 绘制颗粒编号标签 (仅可见范围)
        font_size = max(7, min(12, int(8 * self._pv_zoom)))
        for i, (tx, ty) in enumerate(self._centroids_thumb, 1):
            dx = img_cx + tx * actual_scale
            dy = img_cy + ty * actual_scale
            if -20 < dx < cw + 20 and -20 < dy < ch + 20:
                self.preview_canvas.create_text(
                    dx + 1, dy + 1, text=str(i), fill="black",
                    font=("Arial", font_size, "bold"),
                )
                self.preview_canvas.create_text(
                    dx, dy, text=str(i), fill="white",
                    font=("Arial", font_size, "bold"),
                )

    # --------------------------------------------------------- 面积直方图
    def _show_area_histogram(self):
        if not self.particle_areas:
            messagebox.showwarning(self._t("warn"), self._t("no_data"))
            return

        has_scale = self.app.scale > 0
        nm2_per_px2 = self.app.scale ** 2 if has_scale else 0.0

        if has_scale:
            vals = np.array(self.particle_areas, dtype=float) * nm2_per_px2
            unit = "nm\u00b2"
        else:
            vals = np.array(self.particle_areas, dtype=float)
            unit = "px\u00b2"

        n = len(vals)
        mean = np.mean(vals)
        std = np.std(vals, ddof=1) if n > 1 else 0.0

        win = tk.Toplevel(self)
        win.title(self._t("ca_hist_title"))
        win.geometry("700x550")

        fig = Figure(figsize=(7, 5), dpi=100)
        ax = fig.add_subplot(111)

        num_bins = max(5, int(math.sqrt(n)))
        ax.hist(vals, bins=num_bins, density=True, alpha=0.7,
                color="#4C72B0", edgecolor="white",
                label=self._t("ca_hist_legend_hist"))

        if std > 0:
            x_fit = np.linspace(vals.min() - std, vals.max() + std, 200)
            y_fit = norm.pdf(x_fit, mean, std)
            ax.plot(x_fit, y_fit, "r-", linewidth=2,
                    label=self._t("ca_hist_legend_fit"))

        ax.set_xlabel(self._t("ca_hist_xlabel", u=unit), fontsize=12)
        ax.set_ylabel(self._t("ca_hist_ylabel"), fontsize=12)
        ax.set_title(self._t("ca_hist_title_fmt", n=n, mean=mean, std=std, u=unit),
                     fontsize=13)
        ax.legend(fontsize=10)
        fig.tight_layout()

        canvas_agg = FigureCanvasTkAgg(fig, master=win)
        canvas_agg.draw()
        canvas_agg.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        nav = NavigationToolbar2Tk(canvas_agg, win)
        nav.update()
        nav.pack(side=tk.BOTTOM, fill=tk.X)

    # --------------------------------------------------------- CSV 导出
    def _export_area_csv(self):
        if not self.particle_areas:
            messagebox.showwarning(self._t("warn"), self._t("no_data"))
            return

        path = filedialog.asksaveasfilename(
            title=self._t("export_title"),
            defaultextension=".csv",
            filetypes=[(self._t("csv_files"), "*.csv")],
        )
        if not path:
            return

        has_scale = self.app.scale > 0
        nm2_per_px2 = self.app.scale ** 2 if has_scale else 0.0
        unit = "nm\u00b2" if has_scale else "px\u00b2"

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["#", self._t("ca_col_area", u=unit), self._t("ca_col_area", u="px\u00b2")])
                for i, a_px in enumerate(self.particle_areas, 1):
                    a_val = a_px * nm2_per_px2 if has_scale else a_px
                    writer.writerow([i, f"{a_val:.4f}", a_px])

                writer.writerow([])
                writer.writerow([self._t("csv_stat"), self._t("csv_value")])

                vals = [a * nm2_per_px2 for a in self.particle_areas] if has_scale else list(self.particle_areas)
                n = len(vals)
                mean = np.mean(vals)
                std_val = np.std(vals, ddof=1) if n > 1 else 0.0
                total_pixels = self.img_h_total * self.img_w_total
                total_px = sum(self.particle_areas)
                coverage = total_px / total_pixels * 100.0 if total_pixels > 0 else 0.0

                writer.writerow([self._t("ca_particle_count", n=""), n])
                writer.writerow([self._t("csv_mean"), f"{mean:.4f}"])
                writer.writerow([self._t("csv_std"), f"{std_val:.4f}"])
                writer.writerow([self._t("csv_min"), f"{min(vals):.4f}"])
                writer.writerow([self._t("csv_max"), f"{max(vals):.4f}"])
                writer.writerow([self._t("ca_coverage", c=0.0).split(":")[0], f"{coverage:.2f}%"])
                if has_scale:
                    writer.writerow([self._t("csv_scale"), f"{self.app.scale:.6f}"])

                # ---- 高斯拟合 ----
                if n > 1 and std_val > 0:
                    writer.writerow([])
                    writer.writerow([self._t("csv_gauss_title")])
                    writer.writerow([self._t("csv_gauss_formula"),
                                     "f(x) = (1/(σ√(2π))) × exp(-(x-μ)²/(2σ²))"])
                    writer.writerow([self._t("csv_gauss_mu"), f"{mean:.4f}"])
                    writer.writerow([self._t("csv_gauss_sigma"), f"{std_val:.4f}"])

                    writer.writerow([])
                    vals_arr = np.array(vals)
                    x_fit = np.linspace(vals_arr.min() - std_val,
                                        vals_arr.max() + std_val, 200)
                    y_fit = norm.pdf(x_fit, mean, std_val)
                    writer.writerow([self._t("csv_gauss_curve")])
                    writer.writerow([self._t("csv_gauss_x", u=unit),
                                     self._t("csv_gauss_y")])
                    for xv, yv in zip(x_fit, y_fit):
                        writer.writerow([f"{xv:.4f}", f"{yv:.6f}"])

            self.app.status_var.set(self._t("ca_exported_fmt", p=path))
        except Exception as exc:
            messagebox.showerror(self._t("export_fail"), str(exc))


# ---------------------------------------------------------------------------
# 主应用
# ---------------------------------------------------------------------------

class NanoMeasurer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Measurement Tool")
        self.geometry("1200x800")
        self.minsize(900, 600)

        # ---- 语言 ----
        self.lang = "zh"

        # ---- 状态变量 ----
        self.pil_image = None
        self.tk_image = None
        self.img_w = 0
        self.img_h = 0

        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        self.scale = 0.0
        self.unit = "nm"  # 校准单位
        self.display_unit = "nm"  # 显示单位
        self.units = SUPPORTED_UNITS
        self.mode = "idle"
        self.click_pt = None

        self.measurements: list[Measurement] = []
        self.undo_stack: list[Measurement] = []
        self.groups: list[MeasurementGroup] = []

        self._pan_start = None
        self._right_press_pos = None
        self._rubber_line = None
        self._rubber_text = None

        self._group_drag_start = None  # (ix, iy) for group rectangle drag

        self._pick_color_points: list[tuple] = []   # [(img_x, img_y, r, g, b), ...]
        self._pick_color_total: int = 1

        self._build_ui()
        self._bind_shortcuts()

    # -- 国际化 helper --
    def _t(self, key, **kwargs):
        """查找当前语言的字符串，支持 .format() 参数。"""
        entry = STRINGS.get(key)
        if entry is None:
            return key
        raw = entry.get(self.lang, entry.get("zh", key))
        if kwargs:
            return raw.format(**kwargs)
        return raw

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # -- 菜单栏 --
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        # 文件菜单
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self._t("menu_file"), menu=self.file_menu)
        self.file_menu.add_command(label=self._t("open_image"), command=self.open_image)
        self.file_menu.add_command(label=self._t("export_csv"), command=self.export_csv)

        # 视图菜单
        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self._t("menu_view"), menu=self.view_menu)
        self.view_menu.add_command(label=self._t("fit_window"), command=self.fit_to_window)
        self.view_menu.add_command(label=self._t("menu_zoom_100"), command=self.zoom_100)
        self.view_menu.add_separator()
        self.view_menu.add_command(label=self._t("menu_language"), command=self._toggle_lang)

        # 工具菜单
        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self._t("menu_tools"), menu=self.tools_menu)
        self.tools_menu.add_command(label=self._t("set_scale"), command=self.start_set_scale)
        self.tools_menu.add_command(label=self._t("measure"), command=self.start_measure)
        self.tools_menu.add_command(label=self._t("distribution"), command=self.show_histogram)
        self.tools_menu.add_command(label=self._t("group_select"), command=self.start_group_select)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label=self._t("color_analysis"), command=self.start_pick_color)

        # 关于菜单
        self.about_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self._t("menu_about"), menu=self.about_menu)
        self.about_menu.add_command(label=self._t("menu_help"), command=self._show_help)
        self.about_menu.add_separator()
        self.about_menu.add_command(label=self._t("menu_feedback"), command=self._show_feedback)
        self.about_menu.add_command(label=self._t("menu_licenses"), command=self._show_licenses)
        self.about_menu.add_command(label=self._t("menu_disclaimer"), command=self._show_disclaimer)

        # -- 工具栏 --
        self.toolbar = ttk.Frame(self, padding=2)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_cfg = dict(padding=(8, 2))
        self.btn_open = ttk.Button(self.toolbar, text=self._t("open_image"),
                                   command=self.open_image, **btn_cfg)
        self.btn_open.pack(side=tk.LEFT, padx=2)
        self.btn_scale = ttk.Button(self.toolbar, text=self._t("set_scale"),
                                    command=self.start_set_scale, **btn_cfg)
        self.btn_scale.pack(side=tk.LEFT, padx=2)
        self.btn_measure = ttk.Button(self.toolbar, text=self._t("measure"),
                                      command=self.start_measure, **btn_cfg)
        self.btn_measure.pack(side=tk.LEFT, padx=2)
        self.btn_dist = ttk.Button(self.toolbar, text=self._t("distribution"),
                                   command=self.show_histogram, **btn_cfg)
        self.btn_dist.pack(side=tk.LEFT, padx=2)
        self.btn_csv = ttk.Button(self.toolbar, text=self._t("export_csv"),
                                  command=self.export_csv, **btn_cfg)
        self.btn_csv.pack(side=tk.LEFT, padx=2)
        self.btn_color = ttk.Button(self.toolbar, text=self._t("color_analysis"),
                                    command=self.start_pick_color, **btn_cfg)
        self.btn_color.pack(side=tk.LEFT, padx=2)
        self.btn_group = ttk.Button(self.toolbar, text=self._t("group_select"),
                                    command=self.start_group_select, **btn_cfg)
        self.btn_group.pack(side=tk.LEFT, padx=2)

        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self.btn_fit = ttk.Button(self.toolbar, text=self._t("fit_window"),
                                  command=self.fit_to_window, **btn_cfg)
        self.btn_fit.pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="1:1", command=self.zoom_100, **btn_cfg).pack(side=tk.LEFT, padx=2)

        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self.btn_lang = ttk.Button(self.toolbar, text="EN", command=self._toggle_lang, **btn_cfg)
        self.btn_lang.pack(side=tk.LEFT, padx=2)

        # -- 主区域 --
        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        canvas_frame = ttk.Frame(body)
        self.canvas = tk.Canvas(canvas_frame, bg="#222222", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        body.add(canvas_frame, weight=3)

        self.right_panel = ttk.Frame(body, width=280)
        self._build_right_panel(self.right_panel)
        body.add(self.right_panel, weight=0)

        # -- 状态栏 --
        self.status_var = tk.StringVar(value=self._t("ready"))
        status_bar = ttk.Label(self, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W, padding=(4, 2))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # -- 画布事件 --
        self.canvas.bind("<ButtonPress-1>", self._on_left_click)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)
        self.canvas.bind("<ButtonPress-3>", self._on_right_press)
        self.canvas.bind("<B3-Motion>", self._on_right_drag)
        self.canvas.bind("<ButtonRelease-3>", self._on_right_release)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Button-4>", self._on_scroll_linux_up)
        self.canvas.bind("<Button-5>", self._on_scroll_linux_down)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Configure>", lambda e: self._render())

    def _build_right_panel(self, parent):
        self.lf_scale = ttk.LabelFrame(parent, text=self._t("scale_info"), padding=6)
        self.lf_scale.pack(fill=tk.X, padx=4, pady=(4, 2))
        self.scale_label = ttk.Label(self.lf_scale, text=self._t("scale_not_set"))
        self.scale_label.pack(anchor=tk.W)

        unit_frame = ttk.Frame(self.lf_scale)
        unit_frame.pack(fill=tk.X, pady=(4, 0))
        self.display_unit_label = ttk.Label(unit_frame,
                                             text=self._t("display_unit") + ":")
        self.display_unit_label.pack(side=tk.LEFT)
        self.display_unit_var = tk.StringVar(value=self.display_unit)
        self.display_unit_combo = ttk.Combobox(
            unit_frame, textvariable=self.display_unit_var,
            values=SUPPORTED_UNITS, width=6, state="readonly")
        self.display_unit_combo.pack(side=tk.LEFT, padx=5)
        self.display_unit_combo.bind("<<ComboboxSelected>>",
                                      self._on_display_unit_change)

        self.lf_list = ttk.LabelFrame(parent, text=self._t("meas_list"), padding=4)
        self.lf_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)

        cols = ("col_id", "col_diameter")
        self.tree = ttk.Treeview(self.lf_list, columns=cols, show="headings",
                                 height=15, selectmode="extended")
        self.tree.heading("col_id", text=self._t("col_id"), anchor=tk.CENTER)
        self.tree.heading("col_diameter", text=self._t("col_diameter"), anchor=tk.CENTER)
        self.tree.column("col_id", width=40, anchor=tk.CENTER)
        self.tree.column("col_diameter", width=100, anchor=tk.CENTER)

        sb = ttk.Scrollbar(self.lf_list, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Delete>", lambda e: self.delete_selected())

        self.btn_row = ttk.Frame(self.lf_list)
        self.btn_row.pack(fill=tk.X, pady=(4, 0))
        self.btn_del = ttk.Button(self.btn_row, text=self._t("delete_sel"),
                                  command=self.delete_selected)
        self.btn_del.pack(side=tk.LEFT, padx=2)
        self.btn_clear = ttk.Button(self.btn_row, text=self._t("clear_all"),
                                    command=self.clear_all)
        self.btn_clear.pack(side=tk.LEFT, padx=2)

        self.lf_stat = ttk.LabelFrame(parent, text=self._t("statistics"), padding=6)
        self.lf_stat.pack(fill=tk.X, padx=4, pady=(2, 4))
        self.stat_label = ttk.Label(self.lf_stat, text=f'{self._t("count")}: 0',
                                    justify=tk.LEFT)
        self.stat_label.pack(anchor=tk.W)

    # --------------------------------------------------------- 语言切换
    def _show_help(self):
        """显示使用说明对话框。"""
        messagebox.showinfo(self._t("help_title"), self._t("help_text"))

    def _show_feedback(self):
        """显示提出建议对话框。"""
        messagebox.showinfo(self._t("feedback_title"), self._t("feedback_msg"))

    def _show_licenses(self):
        """显示开源许可对话框。"""
        messagebox.showinfo(self._t("licenses_title"), self._t("licenses_text"))

    def _show_disclaimer(self):
        """显示免责声明对话框。"""
        messagebox.showinfo(self._t("disclaimer_title"), self._t("disclaimer_text"))

    def _toggle_lang(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self._refresh_ui_text()

    def _refresh_ui_text(self):
        """切换语言后刷新所有 UI 文本。"""
        self.btn_lang.config(text="EN" if self.lang == "zh" else "中文")

        self.btn_open.config(text=self._t("open_image"))
        self.btn_scale.config(text=self._t("set_scale"))
        self.btn_measure.config(text=self._t("measure"))
        self.btn_dist.config(text=self._t("distribution"))
        self.btn_csv.config(text=self._t("export_csv"))
        self.btn_color.config(text=self._t("color_analysis"))
        self.btn_group.config(text=self._t("group_select"))
        self.btn_fit.config(text=self._t("fit_window"))

        # 刷新菜单文本（子菜单项）
        self.file_menu.entryconfig(0, label=self._t("open_image"))
        self.file_menu.entryconfig(1, label=self._t("export_csv"))

        self.view_menu.entryconfig(0, label=self._t("fit_window"))
        self.view_menu.entryconfig(1, label=self._t("menu_zoom_100"))
        self.view_menu.entryconfig(3, label=self._t("menu_language"))

        self.tools_menu.entryconfig(0, label=self._t("set_scale"))
        self.tools_menu.entryconfig(1, label=self._t("measure"))
        self.tools_menu.entryconfig(2, label=self._t("distribution"))
        self.tools_menu.entryconfig(3, label=self._t("group_select"))
        self.tools_menu.entryconfig(5, label=self._t("color_analysis"))

        self.about_menu.entryconfig(0, label=self._t("menu_help"))
        self.about_menu.entryconfig(2, label=self._t("menu_feedback"))
        self.about_menu.entryconfig(3, label=self._t("menu_licenses"))
        self.about_menu.entryconfig(4, label=self._t("menu_disclaimer"))

        self.lf_scale.config(text=self._t("scale_info"))
        if self.scale > 0:
            self.scale_label.config(text=self._t("scale_fmt", v=self.scale, u=self.unit))
        else:
            self.scale_label.config(text=self._t("scale_not_set"))

        self.lf_list.config(text=self._t("meas_list"))
        self.tree.heading("col_id", text=self._t("col_id"))
        self.tree.heading("col_diameter", text=self._t("col_diameter", u=self.display_unit))
        self.display_unit_label.config(text=self._t("display_unit") + ":")
        self.btn_del.config(text=self._t("delete_sel"))
        self.btn_clear.config(text=self._t("clear_all"))

        self.lf_stat.config(text=self._t("statistics"))
        self._refresh_list()  # 刷新统计文本

        mode_text = self._mode_text()
        self.status_var.set(self._t("status_short_fmt", mode=mode_text, zoom=self.zoom * 100))

    def _mode_text(self):
        return {"idle": self._t("mode_idle"),
                "set_scale": self._t("mode_scale"),
                "measure": self._t("mode_measure"),
                "pick_color": self._t("mode_pick_color"),
                "group_select": self._t("mode_group")}.get(self.mode, "")

    # --------------------------------------------------------- 快捷键
    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self.open_image())
        self.bind("<Control-O>", lambda e: self.open_image())
        self.bind("<Control-s>", lambda e: self.export_csv())
        self.bind("<Control-S>", lambda e: self.export_csv())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-Z>", lambda e: self.undo())
        self.bind("<Escape>", lambda e: self.cancel_mode())
        self.bind("<Delete>", lambda e: self.delete_selected())

    # --------------------------------------------------------- 打开图片
    def open_image(self):
        path = filedialog.askopenfilename(
            title=self._t("open_image_title"),
            filetypes=[
                (self._t("img_files"), "*.jpg *.jpeg *.bmp *.png *.tif *.tiff"),
                (self._t("all_files"), "*.*"),
            ],
        )
        if not path:
            return

        try:
            img = Image.open(path)
        except Exception as exc:
            messagebox.showerror(self._t("error"), self._t("open_fail", e=exc))
            return

        # 16-bit TIFF → 8-bit
        if img.mode in ("I;16", "I;16B", "I;16L", "I"):
            arr = np.array(img, dtype=np.float64)
            lo, hi = arr.min(), arr.max()
            if hi > lo:
                arr = (arr - lo) / (hi - lo) * 255.0
            img = Image.fromarray(arr.astype(np.uint8))

        if img.mode != "RGB":
            img = img.convert("RGB")

        self.pil_image = img
        self.img_w, self.img_h = img.size
        self.title(f"Measurement Tool - {os.path.basename(path)}")

        self.measurements.clear()
        self.undo_stack.clear()
        self.groups.clear()
        self.scale = 0.0
        self.unit = "nm"
        self.display_unit = "nm"
        self.display_unit_var.set("nm")
        self.click_pt = None
        self.mode = "idle"
        self.scale_label.config(text=self._t("scale_not_set"))
        self._refresh_list()
        self.fit_to_window()

    # --------------------------------------------------------- 缩放/平移
    def fit_to_window(self):
        if self.pil_image is None:
            return
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        zx = cw / self.img_w
        zy = ch / self.img_h
        self.zoom = min(zx, zy) * 0.95
        self.offset_x = (cw - self.img_w * self.zoom) / 2
        self.offset_y = (ch - self.img_h * self.zoom) / 2
        self._render()

    def zoom_100(self):
        if self.pil_image is None:
            return
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        self.zoom = 1.0
        self.offset_x = (cw - self.img_w) / 2
        self.offset_y = (ch - self.img_h) / 2
        self._render()

    def _on_scroll(self, event):
        if self.pil_image is None:
            return
        factor = 1.15 if event.delta > 0 else 1 / 1.15
        self._zoom_at(event.x, event.y, factor)

    def _on_scroll_linux_up(self, event):
        if self.pil_image is None:
            return
        self._zoom_at(event.x, event.y, 1.15)

    def _on_scroll_linux_down(self, event):
        if self.pil_image is None:
            return
        self._zoom_at(event.x, event.y, 1 / 1.15)

    def _zoom_at(self, cx, cy, factor):
        old_zoom = self.zoom
        self.zoom = max(0.02, min(self.zoom * factor, 50.0))
        ratio = self.zoom / old_zoom
        self.offset_x = cx - ratio * (cx - self.offset_x)
        self.offset_y = cy - ratio * (cy - self.offset_y)
        self._render()

    def _on_right_press(self, event):
        self._right_press_pos = (event.x, event.y)
        self._pan_start = (event.x, event.y, self.offset_x, self.offset_y)

    def _on_right_drag(self, event):
        if self._pan_start is None:
            return
        sx, sy, ox, oy = self._pan_start
        self.offset_x = ox + (event.x - sx)
        self.offset_y = oy + (event.y - sy)
        self._render()

    def _on_right_release(self, event):
        self._pan_start = None
        if (self._right_press_pos is not None
                and abs(event.x - self._right_press_pos[0]) < 5
                and abs(event.y - self._right_press_pos[1]) < 5):
            if self.mode == "measure" and self.click_pt is not None:
                self.click_pt = None
                self.canvas.delete("rubber")
                self.status_var.set(self._t("meas_cancelled"))
        self._right_press_pos = None

    # --------------------------------------------------------- 坐标转换
    def _canvas_to_img(self, cx, cy):
        ix = (cx - self.offset_x) / self.zoom
        iy = (cy - self.offset_y) / self.zoom
        return ix, iy

    def _img_to_canvas(self, ix, iy):
        cx = ix * self.zoom + self.offset_x
        cy = iy * self.zoom + self.offset_y
        return cx, cy

    # --------------------------------------------------------- 渲染
    def _render(self):
        self.canvas.delete("all")
        if self.pil_image is None:
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        ix0, iy0 = self._canvas_to_img(0, 0)
        ix1, iy1 = self._canvas_to_img(cw, ch)

        ix0c = max(0, int(math.floor(ix0)))
        iy0c = max(0, int(math.floor(iy0)))
        ix1c = min(self.img_w, int(math.ceil(ix1)))
        iy1c = min(self.img_h, int(math.ceil(iy1)))

        if ix1c <= ix0c or iy1c <= iy0c:
            self._update_status_idle()
            return

        crop = self.pil_image.crop((ix0c, iy0c, ix1c, iy1c))
        new_w = max(1, int((ix1c - ix0c) * self.zoom))
        new_h = max(1, int((iy1c - iy0c) * self.zoom))

        max_dim = 4000
        if new_w > max_dim or new_h > max_dim:
            ratio = min(max_dim / new_w, max_dim / new_h)
            new_w = max(1, int(new_w * ratio))
            new_h = max(1, int(new_h * ratio))

        resample = Image.NEAREST if self.zoom > 4 else Image.BILINEAR
        crop_resized = crop.resize((new_w, new_h), resample)
        self.tk_image = ImageTk.PhotoImage(crop_resized)

        px, py = self._img_to_canvas(ix0c, iy0c)
        self.canvas.create_image(px, py, anchor=tk.NW, image=self.tk_image)

        self._draw_overlays()
        self._update_status_idle()

    def _draw_overlays(self):
        for i, m in enumerate(self.measurements):
            cx1, cy1 = self._img_to_canvas(m.x1, m.y1)
            cx2, cy2 = self._img_to_canvas(m.x2, m.y2)
            self.canvas.create_line(cx1, cy1, cx2, cy2, fill="#FF3333", width=2, tags="overlay")
            r = 3
            for cx, cy in [(cx1, cy1), (cx2, cy2)]:
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                        fill="#FF3333", outline="", tags="overlay")
            mx, my = (cx1 + cx2) / 2, (cy1 + cy2) / 2
            if self.scale > 0:
                dv = self._display_value(m.nm_dist)
                label = f"{dv:.2f} {self.display_unit}"
            else:
                label = f"{m.pixel_dist:.1f} px"
            self.canvas.create_text(mx, my - 10, text=label,
                                    fill="#FFFF00", font=("Arial", 9, "bold"), tags="overlay")

        # 分组矩形
        group_colors = ["#00FF00", "#00CCFF", "#FF9900", "#FF00FF",
                        "#FFFF00", "#00FFCC", "#FF6666", "#9966FF"]
        for gi, g in enumerate(self.groups):
            color = group_colors[gi % len(group_colors)]
            gx1, gy1 = self._img_to_canvas(g.x1, g.y1)
            gx2, gy2 = self._img_to_canvas(g.x2, g.y2)
            self.canvas.create_rectangle(gx1, gy1, gx2, gy2,
                                         outline=color, width=2,
                                         dash=(6, 3), tags="overlay")
            self.canvas.create_text(gx1 + 4, gy1 + 4, text=g.name,
                                    anchor=tk.NW, fill=color,
                                    font=("Arial", 10, "bold"), tags="overlay")

        # 取色标记
        if self.mode == "pick_color" and self._pick_color_points:
            for idx, (px, py, pr, pg, pb) in enumerate(self._pick_color_points, 1):
                cx, cy = self._img_to_canvas(px, py)
                dot_r = 5
                hex_c = "#%02x%02x%02x" % (pr, pg, pb)
                self.canvas.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                                        fill=hex_c, outline="white", width=2, tags="overlay")
                self.canvas.create_text(cx, cy - 12, text=str(idx),
                                        fill="#00FF00", font=("Arial", 9, "bold"),
                                        tags="overlay")

    # --------------------------------------------------------- 鼠标事件
    def _on_left_click(self, event):
        if self.pil_image is None:
            return
        ix, iy = self._canvas_to_img(event.x, event.y)
        ix = max(0, min(ix, self.img_w - 1))
        iy = max(0, min(iy, self.img_h - 1))

        if self.mode == "set_scale":
            self._handle_scale_click(ix, iy)
        elif self.mode == "measure":
            self._handle_measure_click(ix, iy)
        elif self.mode == "pick_color":
            self._handle_pick_color(ix, iy)
        elif self.mode == "group_select":
            self._group_drag_start = (ix, iy)

    def _on_left_drag(self, event):
        if self.mode == "group_select" and self._group_drag_start is not None:
            self.canvas.delete("group_rect")
            cx1, cy1 = self._img_to_canvas(*self._group_drag_start)
            cx2, cy2 = event.x, event.y
            self.canvas.create_rectangle(cx1, cy1, cx2, cy2,
                                         outline="#00FF00", width=2,
                                         dash=(6, 4), tags="group_rect")

    def _on_left_release(self, event):
        if self.mode == "group_select" and self._group_drag_start is not None:
            ix, iy = self._canvas_to_img(event.x, event.y)
            ix = max(0, min(ix, self.img_w - 1))
            iy = max(0, min(iy, self.img_h - 1))
            sx, sy = self._group_drag_start
            self._group_drag_start = None
            self.canvas.delete("group_rect")

            if abs(ix - sx) < 3 and abs(iy - sy) < 3:
                return  # too small

            # Count measurements in this rectangle
            temp_group = MeasurementGroup("", sx, sy, ix, iy)
            count = sum(1 for m in self.measurements
                        if temp_group.contains_measurement(m))
            if count == 0:
                messagebox.showinfo(self._t("warn"), self._t("group_empty"))
                return

            # Ask for group name
            default_name = f"G{len(self.groups) + 1}"
            name = simpledialog.askstring(
                self._t("group_select"),
                self._t("group_name_prompt"),
                initialvalue=default_name, parent=self)
            if not name:
                return

            g = MeasurementGroup(name, sx, sy, ix, iy)
            self.groups.append(g)
            self._render()
            self.status_var.set(self._t("group_created", name=name, n=count))

    def _on_motion(self, event):
        if self.pil_image is None:
            return
        ix, iy = self._canvas_to_img(event.x, event.y)

        mode_text = self._mode_text()
        self.status_var.set(self._t("status_fmt", mode=mode_text,
                                    zoom=self.zoom * 100, x=ix, y=iy))

        if self.click_pt is not None and self.mode in ("set_scale", "measure"):
            self.canvas.delete("rubber")
            cx1, cy1 = self._img_to_canvas(*self.click_pt)
            cx2, cy2 = event.x, event.y

            color = "#00FF00" if self.mode == "set_scale" else "#FF3333"
            self.canvas.create_line(cx1, cy1, cx2, cy2, fill=color, width=2,
                                    dash=(6, 4), tags="rubber")

            p1x, p1y = self.click_pt
            dist_px = math.hypot(ix - p1x, iy - p1y)
            if self.mode == "measure" and self.scale > 0:
                dv = self._display_value(dist_px * self.scale)
                dist_text = f"{dv:.2f} {self.display_unit}"
            else:
                dist_text = f"{dist_px:.1f} px"
            mid_x, mid_y = (cx1 + cx2) / 2, (cy1 + cy2) / 2
            self.canvas.create_text(mid_x, mid_y - 12, text=dist_text,
                                    fill="#00FF00", font=("Arial", 10, "bold"), tags="rubber")

    def _update_status_idle(self):
        mode_text = self._mode_text()
        self.status_var.set(self._t("status_short_fmt", mode=mode_text, zoom=self.zoom * 100))

    # --------------------------------------------------------- 标尺校准
    def start_set_scale(self):
        if self.pil_image is None:
            messagebox.showwarning(self._t("warn"), self._t("no_image"))
            return
        self.mode = "set_scale"
        self.click_pt = None
        self.status_var.set(self._t("scale_click1"))
        self.canvas.config(cursor="crosshair")

    def _handle_scale_click(self, ix, iy):
        if self.click_pt is None:
            self.click_pt = (ix, iy)
            self.status_var.set(self._t("scale_click2"))
        else:
            x1, y1 = self.click_pt
            dist_px = math.hypot(ix - x1, iy - y1)
            if dist_px < 1:
                self.status_var.set(self._t("scale_too_close"))
                return

            dlg = ScaleDialog(
                self,
                self._t("scale_dialog_title"),
                self._t("scale_dialog_px", px=dist_px),
                self._t("scale_dialog_val"),
                self._t("scale_dialog_unit"),
                self.units,
                self.unit
            )
            if dlg.result is None:
                self.cancel_mode()
                return

            self.unit = dlg.result_unit
            self.display_unit = dlg.result_unit
            self.display_unit_var.set(dlg.result_unit)
            self.scale = dlg.result / dist_px
            self.scale_label.config(text=self._t("scale_fmt", v=self.scale, u=self.unit))
            self._update_column_header()

            for m in self.measurements:
                m.nm_dist = m.pixel_dist * self.scale
            self._refresh_list()

            self.click_pt = None
            self.mode = "idle"
            self.canvas.config(cursor="")
            self.canvas.delete("rubber")
            self._render()
            self.status_var.set(self._t("scale_set_fmt", v=self.scale, u=self.unit))

    def _update_column_header(self):
        """更新列表标题以显示当前单位"""
        self.tree.heading("col_diameter",
                          text=self._t("col_diameter", u=self.display_unit))

    def _display_value(self, calib_value):
        """将校准单位的值转换为当前显示单位。"""
        return convert_length(calib_value, self.unit, self.display_unit)

    def _on_display_unit_change(self, event=None):
        """用户切换显示单位时的回调。"""
        self.display_unit = self.display_unit_var.get()
        self._update_column_header()
        self._refresh_list()
        self._render()

    # --------------------------------------------------------- 粒径测量
    def start_measure(self):
        if self.pil_image is None:
            messagebox.showwarning(self._t("warn"), self._t("no_image"))
            return
        if self.scale <= 0:
            messagebox.showwarning(self._t("warn"), self._t("no_scale"))
            return
        self.mode = "measure"
        self.click_pt = None
        self.status_var.set(self._t("meas_click1"))
        self.canvas.config(cursor="crosshair")

    def start_group_select(self):
        if self.pil_image is None:
            messagebox.showwarning(self._t("warn"), self._t("no_image"))
            return
        if not self.measurements:
            messagebox.showwarning(self._t("warn"), self._t("no_data"))
            return
        self.mode = "group_select"
        self._group_drag_start = None
        self.status_var.set(self._t("group_hint"))
        self.canvas.config(cursor="crosshair")

    def _handle_measure_click(self, ix, iy):
        if self.click_pt is None:
            self.click_pt = (ix, iy)
            self.status_var.set(self._t("meas_click2"))
        else:
            x1, y1 = self.click_pt
            dist_px = math.hypot(ix - x1, iy - y1)
            if dist_px < 1:
                self.status_var.set(self._t("scale_too_close"))
                return

            m = Measurement(x1, y1, ix, iy, self.scale)
            self.measurements.append(m)
            self.undo_stack.clear()
            self._refresh_list()
            self._render()

            self.click_pt = None
            self.canvas.delete("rubber")
            n_meas = len(self.measurements)
            self.status_var.set(self._t("meas_recorded",
                                        n=n_meas, d=self._display_value(m.nm_dist),
                                        u=self.display_unit))
            if n_meas % 50 == 0:
                messagebox.showinfo(self._t("hist_title"),
                                    self._t("meas_50_reached", n=n_meas))

    # --------------------------------------------------------- 颜色分析 (取色)
    def start_pick_color(self):
        if self.pil_image is None:
            messagebox.showwarning(self._t("warn"), self._t("no_image"))
            return
        n = simpledialog.askinteger(
            self._t("pick_color_npts_title"),
            self._t("pick_color_npts_msg"),
            initialvalue=1, minvalue=1, maxvalue=20, parent=self,
        )
        if n is None:
            return
        self._pick_color_total = n
        self._pick_color_points = []
        self.mode = "pick_color"
        self.click_pt = None
        if n == 1:
            self.status_var.set(self._t("pick_color_hint"))
        else:
            self.status_var.set(self._t("pick_color_progress", i=1, n=n))
        self.canvas.config(cursor="crosshair")

    def _handle_pick_color(self, ix, iy):
        px_x = int(round(ix))
        px_y = int(round(iy))
        px_x = max(0, min(px_x, self.img_w - 1))
        px_y = max(0, min(px_y, self.img_h - 1))
        r, g, b = self.pil_image.getpixel((px_x, px_y))[:3]
        self._pick_color_points.append((px_x, px_y, r, g, b))
        self._render()  # 重绘以显示取色标记

        if len(self._pick_color_points) < self._pick_color_total:
            i = len(self._pick_color_points) + 1
            self.status_var.set(self._t("pick_color_progress",
                                        i=i, n=self._pick_color_total))
            return

        # 所有点已采集 → 提取 RGB 列表 → 打开分析窗口
        rgb_list = [(p[2], p[3], p[4]) for p in self._pick_color_points]
        self._pick_color_points = []
        self.mode = "idle"
        self.canvas.config(cursor="")
        self._render()
        ColorAnalysisWindow(self, self, rgb_list)

    # --------------------------------------------------------- 测量管理
    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for i, m in enumerate(self.measurements, 1):
            if self.scale > 0:
                dv = self._display_value(m.nm_dist)
                val = f"{dv:.2f}"
            else:
                val = f"{m.pixel_dist:.1f} px"
            self.tree.insert("", tk.END, iid=str(i), values=(i, val))

        n = len(self.measurements)
        if n == 0:
            self.stat_label.config(text=f'{self._t("count")}: 0')
            return

        if self.scale > 0:
            vals = [self._display_value(m.nm_dist) for m in self.measurements]
            unit = self.display_unit
        else:
            vals = [m.pixel_dist for m in self.measurements]
            unit = "px"
        mean = np.mean(vals)
        std = np.std(vals, ddof=1) if n > 1 else 0.0
        self.stat_label.config(
            text=(
                f"{self._t('count')}: {n}\n"
                f"{self._t('mean')}: {mean:.2f} {unit}\n"
                f"{self._t('std')}: {std:.2f} {unit}\n"
                f"{self._t('min')}: {min(vals):.2f} {unit}\n"
                f"{self._t('max')}: {max(vals):.2f} {unit}"
            )
        )

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        indices = sorted([int(s) - 1 for s in sel], reverse=True)
        for idx in indices:
            if 0 <= idx < len(self.measurements):
                self.measurements.pop(idx)
        self._refresh_list()
        self._render()

    def clear_all(self):
        if not self.measurements:
            return
        if messagebox.askyesno(self._t("confirm"), self._t("clear_confirm")):
            self.measurements.clear()
            self.undo_stack.clear()
            self._refresh_list()
            self._render()

    def undo(self):
        if self.mode == "pick_color" and self._pick_color_points:
            self._pick_color_points.pop()
            self._render()
            i = len(self._pick_color_points) + 1
            self.status_var.set(self._t("pick_color_progress",
                                        i=i, n=self._pick_color_total))
            return
        if self.click_pt is not None:
            self.click_pt = None
            self.canvas.delete("rubber")
            self.status_var.set(self._t("undo_click"))
            return
        if not self.measurements:
            return
        m = self.measurements.pop()
        self.undo_stack.append(m)
        self._refresh_list()
        self._render()
        self.status_var.set(self._t("undo_meas_fmt", n=len(self.measurements) + 1))

    def cancel_mode(self):
        self.mode = "idle"
        self.click_pt = None
        self._pick_color_points = []
        self._group_drag_start = None
        self.canvas.config(cursor="")
        self.canvas.delete("rubber")
        self.canvas.delete("group_rect")
        self._render()
        self.status_var.set(self._t("cancelled"))

    # --------------------------------------------------------- 直方图
    def show_histogram(self):
        if not self.measurements:
            messagebox.showwarning(self._t("warn"), self._t("no_data"))
            return

        if self.scale > 0:
            vals = np.array([self._display_value(m.nm_dist)
                             for m in self.measurements])
            unit = self.display_unit
        else:
            vals = np.array([m.pixel_dist for m in self.measurements])
            unit = "px"

        n = len(vals)
        mean = np.mean(vals)
        std = np.std(vals, ddof=1) if n > 1 else 0.0

        win = tk.Toplevel(self)
        win.title(self._t("hist_title"))
        win.geometry("700x550")

        fig = Figure(figsize=(7, 5), dpi=100)
        ax = fig.add_subplot(111)

        num_bins = max(5, int(math.sqrt(n)))
        counts, bins, patches = ax.hist(vals, bins=num_bins, density=True,
                                         alpha=0.7, color="#4C72B0", edgecolor="white",
                                         label=self._t("hist_legend_hist"))

        if std > 0:
            x_fit = np.linspace(vals.min() - std, vals.max() + std, 200)
            y_fit = norm.pdf(x_fit, mean, std)
            ax.plot(x_fit, y_fit, "r-", linewidth=2,
                    label=self._t("hist_legend_fit"))

        ax.set_xlabel(self._t("hist_xlabel", u=unit), fontsize=12)
        ax.set_ylabel(self._t("hist_ylabel"), fontsize=12)
        ax.set_title(self._t("hist_title_fmt", n=n, mean=mean, std=std, u=unit),
                     fontsize=13)
        ax.legend(fontsize=10)
        fig.tight_layout()

        canvas_agg = FigureCanvasTkAgg(fig, master=win)
        canvas_agg.draw()
        canvas_agg.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        nav = NavigationToolbar2Tk(canvas_agg, win)
        nav.update()
        nav.pack(side=tk.BOTTOM, fill=tk.X)

    # --------------------------------------------------------- CSV 导出
    def export_csv(self):
        if not self.measurements:
            messagebox.showwarning(self._t("warn"), self._t("no_data"))
            return

        path = filedialog.asksaveasfilename(
            title=self._t("export_title"),
            defaultextension=".csv",
            filetypes=[(self._t("csv_files"), "*.csv")],
        )
        if not path:
            return

        group_labels = assign_groups(self.measurements, self.groups)

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                write_csv_with_groups(writer, self.measurements, self.groups,
                                      group_labels, scale=self.scale,
                                      lang=self.lang,
                                      calib_unit=self.unit,
                                      display_unit=self.display_unit)

            self.status_var.set(self._t("exported_fmt", p=path))
        except Exception as exc:
            messagebox.showerror(self._t("export_fail"), str(exc))


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = NanoMeasurer()
    app.mainloop()
