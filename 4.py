import os
import subprocess
import platform
import sys
from pathlib import Path
import threading
import json
import time

# 使用PyQt5/PySide6替代tkinter实现与main.py一致的界面风格
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QLineEdit, QGroupBox, QFrame, QMessageBox,
        QComboBox, QFormLayout, QRadioButton, QFileDialog, QProgressBar,
        QTextEdit, QListWidget, QButtonGroup
    )
    from PySide6.QtGui import QFont
    from PySide6.QtCore import Qt, Signal, QThread
    PYSIDE_VERSION = 6
except ImportError:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QLineEdit, QGroupBox, QFrame, QMessageBox,
        QComboBox, QFormLayout, QRadioButton, QFileDialog, QProgressBar,
        QTextEdit, QListWidget, QButtonGroup
    )
    from PyQt5.QtGui import QFont
    from PyQt5.QtCore import Qt, pyqtSignal as Signal, QThread
    PYSIDE_VERSION = 5


class ProcessThread(QThread):
    """处理线程"""
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)
    
    def __init__(self, parent, process_func):
        super().__init__()
        self.parent = parent
        self.process_func = process_func
        
    def run(self):
        try:
            self.process_func()
        except Exception as e:
            self.log_signal.emit(f"❌ 处理异常: {str(e)}")
            self.finished_signal.emit(False, str(e))


class PointCloudProcessingSystem(QMainWindow):
    """点云处理系统（集成CloudCompare+MeshLab）"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("点云处理系统 v2.0")
        self.setGeometry(100, 100, 1400, 900)

        # 全局变量
        self.cc_path = ""
        self.meshlab_path = ""
        self.input_paths = []
        self.output_path = ""
        self.process_type = "denoise"
        self.is_running = False
        self.config_file = "pointcloud_config.json"
        self.process_thread = None
        
        # 参数变量
        self.denoise_k = "6"
        self.denoise_std = "1.0"
        self.subsample_voxel = "0.01"
        self.register_iter = "20"
        self.register_overlap = "0.5"
        self.meshlab_script = "simplification"

        # 加载配置
        self._load_config()
        
        # 初始化界面
        self._init_ui()

    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.cc_path = config.get('cc_path', '')
                    self.meshlab_path = config.get('meshlab_path', '')
        except Exception as e:
            print(f"加载配置失败: {e}")

    def _save_config(self):
        """保存配置文件"""
        try:
            config = {
                'cc_path': self.cc_path,
                'meshlab_path': self.meshlab_path
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _init_ui(self):
        """初始化GUI界面"""
        # 主窗口样式
        self.setStyleSheet("QWidget { background-color: #0f172a; color: #e2e8f0; }")
        
        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #0f172a; color: #e2e8f0;")
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 通用样式
        group_style = """
            QGroupBox {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                border: 1px solid #334155;
                padding-top: 10px;
                margin-top: 10px;
                background-color: #1e293b;
            }
            QLabel { color: #e2e8f0; font-size: 13px; }
            QLineEdit {
                background-color: #334155;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #475569;
                border-radius: 4px;
                font-size: 13px;
            }
            QComboBox {
                background-color: #334155;
                color: #ffffff;
                padding: 6px;
                border: 1px solid #475569;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-size: 13px;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QRadioButton {
                color: #e2e8f0;
                font-size: 13px;
            }
            QListWidget {
                background-color: #334155;
                color: #ffffff;
                border: 1px solid #475569;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #334155;
                color: #ffffff;
                border: 1px solid #475569;
                border-radius: 4px;
                font-family: Consolas, monospace;
            }
            QProgressBar {
                border: 1px solid #475569;
                border-radius: 4px;
                background-color: #334155;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
            }
        """

        # ========== 1. 软件路径配置区 ==========
        frame_cc = QGroupBox("软件路径配置")
        frame_cc.setStyleSheet(group_style)
        frame_cc_layout = QFormLayout(frame_cc)
        frame_cc_layout.setSpacing(10)

        # CloudCompare路径
        cc_layout = QHBoxLayout()
        self.cc_path_edit = QLineEdit(self.cc_path)
        self.cc_path_edit.setMinimumWidth(500)
        cc_browse_btn = QPushButton("浏览")
        cc_browse_btn.clicked.connect(self._browse_cc_path)
        cc_auto_btn = QPushButton("自动检测")
        cc_auto_btn.clicked.connect(self._auto_detect_cc)
        cc_layout.addWidget(self.cc_path_edit)
        cc_layout.addWidget(cc_browse_btn)
        cc_layout.addWidget(cc_auto_btn)
        frame_cc_layout.addRow(QLabel("CloudCompare路径："), cc_layout)

        # MeshLab路径
        meshlab_layout = QHBoxLayout()
        self.meshlab_path_edit = QLineEdit(self.meshlab_path)
        self.meshlab_path_edit.setMinimumWidth(500)
        meshlab_browse_btn = QPushButton("浏览")
        meshlab_browse_btn.clicked.connect(self._browse_meshlab_path)
        meshlab_auto_btn = QPushButton("自动检测")
        meshlab_auto_btn.clicked.connect(self._auto_detect_meshlab)
        meshlab_layout.addWidget(self.meshlab_path_edit)
        meshlab_layout.addWidget(meshlab_browse_btn)
        meshlab_layout.addWidget(meshlab_auto_btn)
        frame_cc_layout.addRow(QLabel("MeshLab路径（可选）："), meshlab_layout)

        main_layout.addWidget(frame_cc)

        # ========== 2. 输入输出配置区 ==========
        frame_io = QGroupBox("输入输出配置")
        frame_io.setStyleSheet(group_style)
        io_layout = QVBoxLayout(frame_io)
        io_layout.setSpacing(10)

        # 输入点云按钮行
        input_btn_layout = QHBoxLayout()
        input_btn_layout.addWidget(QLabel("输入点云："))
        add_files_btn = QPushButton("添加文件")
        add_files_btn.clicked.connect(self._add_input_files)
        add_folder_btn = QPushButton("添加文件夹")
        add_folder_btn.clicked.connect(self._add_input_folder)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_input_files)
        input_btn_layout.addWidget(add_files_btn)
        input_btn_layout.addWidget(add_folder_btn)
        input_btn_layout.addWidget(clear_btn)
        input_btn_layout.addStretch()
        io_layout.addLayout(input_btn_layout)

        # 输入文件列表
        self.input_listbox = QListWidget()
        self.input_listbox.setMaximumHeight(100)
        io_layout.addWidget(self.input_listbox)

        # 输出路径
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出路径："))
        self.output_path_edit = QLineEdit(self.output_path)
        self.output_path_edit.setMinimumWidth(600)
        output_browse_btn = QPushButton("浏览")
        output_browse_btn.clicked.connect(self._browse_output_path)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(output_browse_btn)
        io_layout.addLayout(output_layout)

        main_layout.addWidget(frame_io)

        # ========== 3. 处理功能选择区 ==========
        frame_func = QGroupBox("处理功能选择")
        frame_func.setStyleSheet(group_style)
        func_layout = QVBoxLayout(frame_func)

        # 功能单选按钮
        radio_layout = QHBoxLayout()
        self.radio_group = QButtonGroup()
        
        self.radio_denoise = QRadioButton("去噪（统计滤波）")
        self.radio_denoise.setChecked(True)
        self.radio_subsample = QRadioButton("下采样（体素网格）")
        self.radio_register = QRadioButton("点云配准（ICP）")
        self.radio_merge = QRadioButton("点云拼接（合并）")
        self.radio_meshlab = QRadioButton("MeshLab网格处理")
        
        self.radio_group.addButton(self.radio_denoise, 0)
        self.radio_group.addButton(self.radio_subsample, 1)
        self.radio_group.addButton(self.radio_register, 2)
        self.radio_group.addButton(self.radio_merge, 3)
        self.radio_group.addButton(self.radio_meshlab, 4)
        
        radio_layout.addWidget(self.radio_denoise)
        radio_layout.addWidget(self.radio_subsample)
        radio_layout.addWidget(self.radio_register)
        radio_layout.addWidget(self.radio_merge)
        radio_layout.addWidget(self.radio_meshlab)
        radio_layout.addStretch()
        func_layout.addLayout(radio_layout)

        # 参数配置区域
        param_group = QGroupBox("参数配置")
        param_group.setStyleSheet("QGroupBox { color: #cbd5e1; font-size: 14px; border: 1px solid #475569; padding-top: 10px; margin-top: 10px; }")
        self.param_layout = QHBoxLayout(param_group)
        
        # 去噪参数
        self.denoise_widget = QWidget()
        denoise_layout = QHBoxLayout(self.denoise_widget)
        denoise_layout.addWidget(QLabel("邻域点数："))
        self.denoise_k_edit = QLineEdit(self.denoise_k)
        self.denoise_k_edit.setMaximumWidth(80)
        denoise_layout.addWidget(self.denoise_k_edit)
        denoise_layout.addWidget(QLabel("标准差倍数："))
        self.denoise_std_edit = QLineEdit(self.denoise_std)
        self.denoise_std_edit.setMaximumWidth(80)
        denoise_layout.addWidget(self.denoise_std_edit)
        denoise_layout.addStretch()
        
        # 下采样参数
        self.subsample_widget = QWidget()
        subsample_layout = QHBoxLayout(self.subsample_widget)
        subsample_layout.addWidget(QLabel("体素大小(m)："))
        self.subsample_voxel_edit = QLineEdit(self.subsample_voxel)
        self.subsample_voxel_edit.setMaximumWidth(80)
        subsample_layout.addWidget(self.subsample_voxel_edit)
        subsample_layout.addStretch()
        
        # 配准参数
        self.register_widget = QWidget()
        register_layout = QHBoxLayout(self.register_widget)
        register_layout.addWidget(QLabel("ICP迭代次数："))
        self.register_iter_edit = QLineEdit(self.register_iter)
        self.register_iter_edit.setMaximumWidth(80)
        register_layout.addWidget(self.register_iter_edit)
        register_layout.addWidget(QLabel("重叠度："))
        self.register_overlap_edit = QLineEdit(self.register_overlap)
        self.register_overlap_edit.setMaximumWidth(80)
        register_layout.addWidget(self.register_overlap_edit)
        register_layout.addStretch()
        
        # MeshLab参数
        self.meshlab_widget = QWidget()
        meshlab_layout = QHBoxLayout(self.meshlab_widget)
        meshlab_layout.addWidget(QLabel("处理类型："))
        self.meshlab_script_combo = QComboBox()
        self.meshlab_script_combo.addItems(["simplification", "smoothing", "reconstruction"])
        self.meshlab_script_combo.setCurrentText(self.meshlab_script)
        meshlab_layout.addWidget(self.meshlab_script_combo)
        meshlab_layout.addStretch()
        
        self.param_layout.addWidget(self.denoise_widget)
        self.param_layout.addWidget(self.subsample_widget)
        self.param_layout.addWidget(self.register_widget)
        self.param_layout.addWidget(self.meshlab_widget)
        
        # 初始显示去噪参数
        self.subsample_widget.hide()
        self.register_widget.hide()
        self.meshlab_widget.hide()
        
        func_layout.addWidget(param_group)
        main_layout.addWidget(frame_func)

        # 绑定单选按钮事件
        self.radio_group.buttonClicked.connect(self._on_process_type_change)

        # ========== 4. 执行与日志区 ==========
        frame_exec = QGroupBox("执行日志")
        frame_exec.setStyleSheet(group_style)
        exec_layout = QVBoxLayout(frame_exec)

        # 执行按钮行
        btn_layout = QHBoxLayout()
        self.exec_btn = QPushButton("开始处理")
        self.exec_btn.clicked.connect(self._start_process)
        stop_btn = QPushButton("停止处理")
        stop_btn.clicked.connect(self._stop_process)
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self._clear_log)
        export_log_btn = QPushButton("导出日志")
        export_log_btn.clicked.connect(self._export_log)
        
        btn_layout.addWidget(self.exec_btn)
        btn_layout.addWidget(stop_btn)
        btn_layout.addWidget(clear_log_btn)
        btn_layout.addWidget(export_log_btn)
        
        self.progress = QProgressBar()
        self.progress.setMaximum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        btn_layout.addWidget(self.progress)
        
        exec_layout.addLayout(btn_layout)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(300)
        exec_layout.addWidget(self.log_text)

        main_layout.addWidget(frame_exec)

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #e2e8f0; padding: 5px; background-color: #1e293b;")
        main_layout.addWidget(self.status_label)

    def _on_process_type_change(self, button):
        """处理类型改变时更新参数显示"""
        button_id = self.radio_group.id(button)
        
        # 隐藏所有参数框
        self.denoise_widget.hide()
        self.subsample_widget.hide()
        self.register_widget.hide()
        self.meshlab_widget.hide()
        
        # 显示对应参数框
        if button_id == 0:  # 去噪
            self.process_type = "denoise"
            self.denoise_widget.show()
        elif button_id == 1:  # 下采样
            self.process_type = "subsample"
            self.subsample_widget.show()
        elif button_id == 2:  # 配准
            self.process_type = "register"
            self.register_widget.show()
        elif button_id == 3:  # 合并
            self.process_type = "merge"
        elif button_id == 4:  # MeshLab
            self.process_type = "meshlab"
            self.meshlab_widget.show()

    # ========== 界面交互方法 ==========
    def _auto_detect_cc(self):
        """自动检测CloudCompare路径"""
        common_paths = [
            "C:/Program Files/CloudCompare/CloudCompare.exe",
            "C:/Program Files (x86)/CloudCompare/CloudCompare.exe",
            "D:/Program Files/CloudCompare/CloudCompare.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                self.cc_path = path
                self.cc_path_edit.setText(path)
                self._log(f"✅ 自动检测到CloudCompare: {path}")
                self._save_config()
                return
        self._log("❌ 未自动检测到CloudCompare，请手动选择")

    def _auto_detect_meshlab(self):
        """自动检测MeshLab路径"""
        common_paths = [
            "C:/Program Files/MeshLab/MeshLab.exe",
            "C:/Program Files (x86)/MeshLab/MeshLab.exe",
            "D:/Program Files/MeshLab/MeshLab.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                self.meshlab_path = path
                self.meshlab_path_edit.setText(path)
                self._log(f"✅ 自动检测到MeshLab: {path}")
                self._save_config()
                return
        self._log("❌ 未自动检测到MeshLab，请手动选择")

    def _browse_cc_path(self):
        """浏览选择CloudCompare路径"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择CloudCompare.exe",
            "C:/Program Files/CloudCompare",
            "可执行文件 (*.exe);;所有文件 (*.*)"
        )
        if path:
            self.cc_path = path
            self.cc_path_edit.setText(path)
            self._save_config()

    def _browse_meshlab_path(self):
        """浏览选择MeshLab路径"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择MeshLab.exe",
            "C:/Program Files/MeshLab",
            "可执行文件 (*.exe);;所有文件 (*.*)"
        )
        if path:
            self.meshlab_path = path
            self.meshlab_path_edit.setText(path)
            self._save_config()

    def _add_input_files(self):
        """添加输入点云文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择点云文件", "",
            "点云文件 (*.ply *.las *.laz *.pcd *.xyz *.pts *.e57);;所有文件 (*.*)"
        )
        if files:
            for f in files:
                if f not in self.input_paths:
                    self.input_paths.append(f)
                    self.input_listbox.addItem(os.path.basename(f))
            self._log(f"✅ 添加了 {len(files)} 个点云文件")

    def _add_input_folder(self):
        """添加文件夹中的所有点云文件"""
        folder = QFileDialog.getExistingDirectory(self, "选择点云文件所在文件夹")
        if folder:
            pointcloud_extensions = ['.ply', '.las', '.laz', '.pcd', '.xyz', '.pts', '.e57']
            added = 0
            for ext in pointcloud_extensions:
                for file in Path(folder).glob(f"*{ext}"):
                    if str(file) not in self.input_paths:
                        self.input_paths.append(str(file))
                        self.input_listbox.addItem(file.name)
                        added += 1
            self._log(f"✅ 从文件夹添加了 {added} 个点云文件")

    def _clear_input_files(self):
        """清空输入文件列表"""
        self.input_paths.clear()
        self.input_listbox.clear()
        self._log("✅ 已清空输入文件列表")

    def _browse_output_path(self):
        """选择输出文件路径"""
        default_ext = ".ply"
        if self.process_type == "meshlab":
            filter_str = "PLY文件 (*.ply);;所有文件 (*.*)"
        else:
            filter_str = "PLY文件 (*.ply);;LAS文件 (*.las);;PCD文件 (*.pcd);;所有文件 (*.*)"
        
        path, _ = QFileDialog.getSaveFileName(
            self, "保存处理后的点云", "", filter_str
        )
        if path:
            self.output_path = path
            self.output_path_edit.setText(path)

    def _log(self, msg):
        """日志输出"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        self.log_text.append(formatted_msg)
        QApplication.processEvents()

    def _clear_log(self):
        """清空日志"""
        self.log_text.clear()

    def _export_log(self):
        """导出日志到文件"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self._log(f"✅ 日志已导出到: {path}")
            except Exception as e:
                self._log(f"❌ 导出日志失败: {e}")

    def _stop_process(self):
        """停止处理过程"""
        if self.is_running:
            self.is_running = False
            self._log("⚠️ 用户请求停止处理...")

    # ========== 核心处理方法 ==========
    def _validate_paths(self):
        """验证路径合法性"""
        self.cc_path = self.cc_path_edit.text()
        self.meshlab_path = self.meshlab_path_edit.text()
        self.output_path = self.output_path_edit.text()
        
        if not self.cc_path or not os.path.exists(self.cc_path):
            QMessageBox.critical(self, "错误", "请选择有效的CloudCompare路径！")
            return False
            
        if not self.input_paths:
            QMessageBox.critical(self, "错误", "请添加至少一个输入点云文件！")
            return False
            
        if not self.output_path:
            QMessageBox.critical(self, "错误", "请选择输出文件路径！")
            return False
            
        if self.process_type == "register" and len(self.input_paths) < 2:
            QMessageBox.critical(self, "错误", "点云配准需要至少2个输入点云文件！")
            return False
            
        if self.process_type == "meshlab" and (not self.meshlab_path or not os.path.exists(self.meshlab_path)):
            QMessageBox.critical(self, "错误", "MeshLab处理需要有效的MeshLab路径！")
            return False
            
        return True

    def _get_cc_commands(self):
        """生成CloudCompare处理命令"""
        commands = ["-SILENT", "-NO_TIMESTAMP", "-AUTO_SAVE", "OFF", "-C_EXPORT_FMT", "PLY"]

        if self.process_type == "denoise":
            k = self.denoise_k_edit.text()
            std = self.denoise_std_edit.text()
            commands.extend(["-SOR", k, std])
        elif self.process_type == "subsample":
            voxel = self.subsample_voxel_edit.text()
            commands.extend(["-SS", "VOXEL_SIZE", voxel])
        elif self.process_type == "register":
            iter_num = self.register_iter_edit.text()
            overlap = self.register_overlap_edit.text()
            commands.extend(["-ICP", "-MIN_ERROR_DIFF", "0.0001", "-ITER", iter_num, "-OVERLAP", overlap])
        elif self.process_type == "merge":
            commands.extend(["-MERGE_CLOUDS"])

        return commands

    def _run_cc_process(self):
        """执行CloudCompare处理"""
        try:
            self.is_running = True
            self.exec_btn.setEnabled(False)
            self.progress.setMaximum(0)
            self.status_label.setText("处理中...")
            
            self._log("=" * 50)
            self._log("开始点云处理")
            self._log(f"处理类型: {self.process_type}")
            self._log(f"输入文件: {len(self.input_paths)} 个")
            for i, path in enumerate(self.input_paths):
                self._log(f"  文件 {i+1}: {os.path.basename(path)}")
            self._log(f"输出文件: {self.output_path}")

            cmd = [self.cc_path]
            for path in self.input_paths:
                cmd.extend(["-O", path])
            cmd.extend(self._get_cc_commands())
            
            output_dir = os.path.dirname(self.output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            cmd.extend(["-SAVE_CLOUDS", "FILE", self.output_path])
            self._log(f"执行命令: {' '.join(cmd)}")

            start_time = time.time()
            creation_flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True, creationflags=creation_flags)

            while True:
                if not self.is_running:
                    process.terminate()
                    break
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self._log(output.strip())

            returncode = process.wait()
            elapsed_time = time.time() - start_time

            if returncode in [0, 1] and self.is_running:
                if os.path.exists(self.output_path):
                    file_size = os.path.getsize(self.output_path) / (1024 * 1024)
                    self._log(f"✅ 处理完成！")
                    self._log(f"📊 输出文件: {self.output_path}")
                    self._log(f"📏 文件大小: {file_size:.2f} MB")
                    self._log(f"⏱️ 处理时间: {elapsed_time:.2f} 秒")
                else:
                    self._log("⚠️ 返回码正常，但未生成输出文件")
            else:
                if not self.is_running:
                    self._log("❌ 处理被用户中断")
                else:
                    self._log(f"❌ 处理失败（返回码: {returncode}）")
                    stderr_output = process.stderr.read()
                    if stderr_output:
                        self._log(f"错误信息: {stderr_output[:1000]}")

        except Exception as e:
            self._log(f"❌ 处理异常: {str(e)}")
        finally:
            self.is_running = False
            self.exec_btn.setEnabled(True)
            self.progress.setMaximum(100)
            self.progress.setValue(100)
            self.status_label.setText("就绪")
            self._log("处理结束")
            self._log("=" * 50)

    def _start_process(self):
        """启动处理"""
        if self.is_running:
            QMessageBox.warning(self, "提示", "处理中，请等待完成！")
            return
            
        if not self._validate_paths():
            return

        def process_thread():
            if self.process_type == "meshlab":
                # MeshLab处理暂不实现
                self._log("MeshLab处理功能开发中...")
            else:
                self._run_cc_process()

        threading.Thread(target=process_thread, daemon=True).start()


if __name__ == "__main__":
    # 适配高分屏
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    # 设置全局字体
    font = QFont("微软雅黑", 10)
    app.setFont(font)

    window = PointCloudProcessingSystem()
    window.show()

    sys.exit(app.exec())
