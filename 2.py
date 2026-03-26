import sys
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QSpinBox, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QProgressBar, QComboBox
)
from PyQt5.QtGui import QPixmap, QFont, QColor
from PyQt5.QtCore import Qt, QTimer


class ConstructionDetectionUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("建筑构件数字化检测系统")
        self.setGeometry(100, 100, 1200, 800)  # 窗口大小
        self.setStyleSheet("background-color: #0F172A; color: #E2E8F0;")  # 深色主题

        # 主容器
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # 左侧导航栏
        self.side_nav = QWidget()
        self.side_nav.setFixedWidth(80)
        side_layout = QVBoxLayout(self.side_nav)
        side_layout.setAlignment(Qt.AlignTop)

        # 导航按钮（自动界面、参数设置、结果）
        nav_btns = ["自动界面", "参数设置", "结果"]
        for btn_text in nav_btns:
            btn = QPushButton(btn_text)
            btn.setFixedSize(70, 50)
            btn.setStyleSheet("background-color: #1E293B; border: none; border-radius: 5px;")
            side_layout.addWidget(btn)
        main_layout.addWidget(self.side_nav)

        # 中间标签页（核心内容区）
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(
            "QTabBar::tab {background-color: #1E293B; color: #E2E8F0; padding: 8px;} QTabBar::tab:selected {background-color: #334155;}")

        # 标签页1：自动界面
        self.auto_tab = QWidget()
        self.init_auto_tab()
        self.tab_widget.addTab(self.auto_tab, "自动界面")

        # 标签页2：参数设置
        self.param_tab = QWidget()
        self.init_param_tab()
        self.tab_widget.addTab(self.param_tab, "参数设置")

        # 标签页3：结果
        self.result_tab = QWidget()
        self.init_result_tab()
        self.tab_widget.addTab(self.result_tab, "结果")

        main_layout.addWidget(self.tab_widget)

        # 右侧信息栏
        self.right_info = QWidget()
        self.right_info.setFixedWidth(250)
        right_layout = QVBoxLayout(self.right_info)

        # 操作员信息
        operator_box = QGroupBox("操作员信息")
        operator_layout = QVBoxLayout(operator_box)
        operator_layout.addWidget(QLabel("姓名：张三"))
        operator_layout.addWidget(QLabel("工号：001"))
        right_layout.addWidget(operator_box)

        # 进度条
        progress_box = QGroupBox("检测进度")
        progress_layout = QVBoxLayout(progress_box)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(60)
        progress_layout.addWidget(self.progress_bar)
        right_layout.addWidget(progress_box)

        main_layout.addWidget(self.right_info)

    # 初始化“自动界面”标签页
    def init_auto_tab(self):
        layout = QGridLayout(self.auto_tab)

        # 模型显示区
        model_label = QLabel()
        model_label.setPixmap(QPixmap("construction_model.png").scaled(200, 150))  # 替换为你的模型图片
        layout.addWidget(model_label, 0, 0)

        # 视图按钮
        view_btns = ["设计图", "单目标标注视图", "双目标标注视图", "3D模型视图"]
        btn_pos = [(0, 1), (1, 0), (1, 1), (2, 0)]
        for i, btn_text in enumerate(view_btns):
            btn = QPushButton(btn_text)
            btn.setStyleSheet("background-color: #334155; border: none; padding: 5px;")
            layout.addWidget(btn, btn_pos[i][0], btn_pos[i][1])

        # 操作栏
        op_box = QGroupBox("操作栏")
        op_layout = QGridLayout(op_box)
        op_btns = ["开始", "角度", "计算", "旋转", "角度计算"]
        op_layout.addWidget(QPushButton(op_btns[0]), 0, 0)
        op_layout.addWidget(QLabel("60°"), 0, 2)
        op_layout.addWidget(QPushButton(op_btns[1]), 0, 1)
        op_layout.addWidget(QPushButton(op_btns[2]), 1, 0)
        op_layout.addWidget(QPushButton(op_btns[3]), 1, 1)
        op_layout.addWidget(QPushButton(op_btns[4]), 2, 0)
        layout.addWidget(op_box, 2, 1)

    # 初始化“参数设置”标签页
    def init_param_tab(self):
        layout = QGridLayout(self.param_tab)
        params = [
            ("边缘检测(mm)", 0), ("对比度", 32), ("逆光对比", 1),
            ("亮度", 128), ("清晰度", 3), ("锐度", 100),
            ("色调", 0), ("饱和", 120), ("焦点", 10),
            ("饱和度", 64), ("白平衡", 4600), ("曝光", -6)
        ]

        # 生成参数输入框（SpinBox）
        for i, (param_name, default_val) in enumerate(params):
            label = QLabel(param_name)
            spin = QSpinBox()
            spin.setValue(default_val)
            spin.setStyleSheet("background-color: #1E293B; border: none;")
            layout.addWidget(label, i // 3, (i % 3) * 2)
            layout.addWidget(spin, i // 3, (i % 3) * 2 + 1)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton("操作确定"))
        btn_layout.addWidget(QPushButton("重载默认"))
        btn_layout.addWidget(QPushButton("应用此次"))
        layout.addLayout(btn_layout, 4, 0, 1, 6)

    # 初始化“结果”标签页
    def init_result_tab(self):
        layout = QVBoxLayout(self.result_tab)

        # 多视图显示
        view_layout = QHBoxLayout()
        for _ in range(3):
            view_label = QLabel()
            view_label.setPixmap(QPixmap("view_sample.png").scaled(200, 150))  # 替换为视图图片
            view_layout.addWidget(view_label)
        layout.addLayout(view_layout)

        # 结果表格
        self.result_table = QTableWidget(5, 8)
        self.result_table.setHorizontalHeaderLabels(["检测项", "结果", "误差", "阈值", "状态", "备注", "评分", "时间"])
        self.result_table.setStyleSheet("background-color: #1E293B;")
        # 示例数据
        self.result_table.setItem(0, 0, QTableWidgetItem("构件尺寸"))
        self.result_table.setItem(0, 1, QTableWidgetItem("1000mm"))
        layout.addWidget(self.result_table)

        # 导出按钮
        export_layout = QHBoxLayout()
        export_layout.addWidget(QPushButton("结果导出选项"))
        export_layout.addWidget(QPushButton("Excel清单"))
        export_layout.addWidget(QPushButton("上传云端"))
        layout.addLayout(export_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ConstructionDetectionUI()
    window.show()
    sys.exit(app.exec_())