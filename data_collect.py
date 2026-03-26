# -*- coding: utf-8 -*-
"""
数据采集程序
功能：
1. GUI界面设置采集参数（张数、帧率、分辨率、保存路径）
2. 抽帧采集功能（每10帧采集一次）
3. 相机参数调整（曝光时间等）
4. 预览模式：实时显示画面
5. 采集模式：关闭画面显示，进行数据采集
"""

import sys
import os
import gxipy as gx
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PIL import Image
import datetime
import numpy
from ctypes import *
from gxipy.gxidef import *
from gxipy.ImageProc import Utility
from gxipy.ImageFormatConvert import *


# 分辨率预设值
RESOLUTION_PRESETS = {
    "1K (1280x720)": (1280, 720),
    "2K (1920x1080)": (1920, 1080),
    "3K (2560x1440)": (2560, 1440),
    "4K (3840x2160)": (3840, 2160)
}


class PreviewThread(QThread):
    """预览线程，用于实时显示画面"""
    image_signal = pyqtSignal(object)  # 发送图像数据信号
    
    def __init__(self, cam, image_format_convert):
        super().__init__()
        self.cam = cam
        self.image_format_convert = image_format_convert
        self.running = False
        
    def run(self):
        """线程运行函数"""
        self.running = True
        while self.running:
            try:
                raw_image = self.cam.data_stream[0].get_image(500)
                if raw_image is None:
                    continue
                    
                # 转换图像格式
                if raw_image.get_pixel_format() != GxPixelFormatEntry.RGB8:
                    rgb_image_array, rgb_image_buffer_length = self.convert_to_RGB(raw_image)
                    if rgb_image_array is None:
                        continue
                    numpy_image = numpy.frombuffer(rgb_image_array, dtype=numpy.ubyte, 
                                                  count=rgb_image_buffer_length).reshape(
                        raw_image.frame_data.height, raw_image.frame_data.width, 3)
                else:
                    numpy_image = raw_image.get_numpy_array()
                    
                if numpy_image is not None:
                    self.image_signal.emit(numpy_image)
                    
            except Exception as e:
                print(f"预览线程错误: {e}")
                break
                
    def convert_to_RGB(self, raw_image):
        """转换图像为RGB格式"""
        try:
            self.image_format_convert.set_dest_format(GxPixelFormatEntry.RGB8)
            valid_bits = self.get_best_valid_bits(raw_image.get_pixel_format())
            self.image_format_convert.set_valid_bits(valid_bits)
            
            buffer_out_size = self.image_format_convert.get_buffer_size_for_conversion(raw_image)
            output_image_array = (c_ubyte * buffer_out_size)()
            output_image = addressof(output_image_array)
            
            self.image_format_convert.convert(raw_image, output_image, buffer_out_size, False)
            if output_image is None:
                return None, 0
                
            return output_image_array, buffer_out_size
        except Exception as e:
            print(f"图像转换错误: {e}")
            return None, 0
            
    def get_best_valid_bits(self, pixel_format):
        """获取最佳有效位数"""
        if pixel_format in (GxPixelFormatEntry.MONO8,
                           GxPixelFormatEntry.BAYER_GR8, GxPixelFormatEntry.BAYER_RG8,
                           GxPixelFormatEntry.BAYER_GB8, GxPixelFormatEntry.BAYER_BG8,
                           GxPixelFormatEntry.RGB8, GxPixelFormatEntry.BGR8,
                           GxPixelFormatEntry.R8, GxPixelFormatEntry.B8, GxPixelFormatEntry.G8):
            return DxValidBit.BIT0_7
        elif pixel_format in (GxPixelFormatEntry.MONO10, GxPixelFormatEntry.MONO10_PACKED, GxPixelFormatEntry.MONO10_P,
                             GxPixelFormatEntry.BAYER_GR10, GxPixelFormatEntry.BAYER_RG10,
                             GxPixelFormatEntry.BAYER_GB10, GxPixelFormatEntry.BAYER_BG10,
                             GxPixelFormatEntry.BAYER_GR10_P, GxPixelFormatEntry.BAYER_RG10_P,
                             GxPixelFormatEntry.BAYER_GB10_P, GxPixelFormatEntry.BAYER_BG10_P,
                             GxPixelFormatEntry.BAYER_GR10_PACKED, GxPixelFormatEntry.BAYER_RG10_PACKED,
                             GxPixelFormatEntry.BAYER_GB10_PACKED, GxPixelFormatEntry.BAYER_BG10_PACKED):
            return DxValidBit.BIT2_9
        elif pixel_format in (GxPixelFormatEntry.MONO12, GxPixelFormatEntry.MONO12_PACKED, GxPixelFormatEntry.MONO12_P,
                             GxPixelFormatEntry.BAYER_GR12, GxPixelFormatEntry.BAYER_RG12,
                             GxPixelFormatEntry.BAYER_GB12, GxPixelFormatEntry.BAYER_BG12,
                             GxPixelFormatEntry.BAYER_GR12_P, GxPixelFormatEntry.BAYER_RG12_P,
                             GxPixelFormatEntry.BAYER_GB12_P, GxPixelFormatEntry.BAYER_BG12_P,
                             GxPixelFormatEntry.BAYER_GR12_PACKED, GxPixelFormatEntry.BAYER_RG12_PACKED,
                             GxPixelFormatEntry.BAYER_GB12_PACKED, GxPixelFormatEntry.BAYER_RG12_PACKED):
            return DxValidBit.BIT4_11
        elif pixel_format in (GxPixelFormatEntry.MONO14, GxPixelFormatEntry.MONO14_P,
                             GxPixelFormatEntry.BAYER_GR14, GxPixelFormatEntry.BAYER_RG14,
                             GxPixelFormatEntry.BAYER_GB14, GxPixelFormatEntry.BAYER_BG14,
                             GxPixelFormatEntry.BAYER_GR14_P, GxPixelFormatEntry.BAYER_RG14_P,
                             GxPixelFormatEntry.BAYER_GB14_P, GxPixelFormatEntry.BAYER_BG14_P):
            return DxValidBit.BIT6_13
        elif pixel_format in (GxPixelFormatEntry.MONO16,
                             GxPixelFormatEntry.BAYER_GR16, GxPixelFormatEntry.BAYER_RG16,
                             GxPixelFormatEntry.BAYER_GB16, GxPixelFormatEntry.BAYER_BG16):
            return DxValidBit.BIT8_15
        return DxValidBit.BIT0_7
        
    def stop(self):
        """停止预览"""
        self.running = False


class CaptureThread(QThread):
    """采集线程，用于数据采集"""
    progress_signal = pyqtSignal(int, int)  # 发送进度信号（当前数量，总数）
    finished_signal = pyqtSignal()  # 采集完成信号
    
    def __init__(self, cam, image_format_convert, capture_params):
        super().__init__()
        self.cam = cam
        self.image_format_convert = image_format_convert
        self.capture_params = capture_params
        self.running = False
        
    def run(self):
        """线程运行函数"""
        self.running = True
        save_path = self.capture_params['save_path']
        total_count = self.capture_params['total_count']
        frame_skip = self.capture_params['frame_skip']  # 抽帧数，10表示每10帧采集一次
        frame_counter = 0  # 帧计数器
        saved_count = 0  # 已保存数量
        
        try:
            # 创建保存目录
            if not os.path.exists(save_path):
                os.makedirs(save_path)
                
            while self.running and saved_count < total_count:
                try:
                    raw_image = self.cam.data_stream[0].get_image(1000)
                    if raw_image is None:
                        continue
                        
                    frame_counter += 1
                    
                    # 抽帧逻辑：只有满足抽帧条件才保存
                    if frame_counter % frame_skip == 0:
                        # 转换图像格式
                        if raw_image.get_pixel_format() != GxPixelFormatEntry.RGB8:
                            rgb_image_array, rgb_image_buffer_length = self.convert_to_RGB(raw_image)
                            if rgb_image_array is None:
                                continue
                            numpy_image = numpy.frombuffer(rgb_image_array, dtype=numpy.ubyte,
                                                          count=rgb_image_buffer_length).reshape(
                                raw_image.frame_data.height, raw_image.frame_data.width, 3)
                        else:
                            numpy_image = raw_image.get_numpy_array()
                            
                        if numpy_image is not None:
                            # 保存图像
                            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                            img_name = f"img_{saved_count:06d}_{timestamp}.jpg"
                            img_path = os.path.join(save_path, img_name)
                            
                            img = Image.fromarray(numpy_image, 'RGB')
                            img.save(img_path)
                            
                            saved_count += 1
                            self.progress_signal.emit(saved_count, total_count)
                            
                except Exception as e:
                    print(f"采集错误: {e}")
                    continue
                    
        except Exception as e:
            print(f"采集线程错误: {e}")
        finally:
            self.finished_signal.emit()
            
    def convert_to_RGB(self, raw_image):
        """转换图像为RGB格式"""
        try:
            self.image_format_convert.set_dest_format(GxPixelFormatEntry.RGB8)
            valid_bits = self.get_best_valid_bits(raw_image.get_pixel_format())
            self.image_format_convert.set_valid_bits(valid_bits)
            
            buffer_out_size = self.image_format_convert.get_buffer_size_for_conversion(raw_image)
            output_image_array = (c_ubyte * buffer_out_size)()
            output_image = addressof(output_image_array)
            
            self.image_format_convert.convert(raw_image, output_image, buffer_out_size, False)
            if output_image is None:
                return None, 0
                
            return output_image_array, buffer_out_size
        except Exception as e:
            print(f"图像转换错误: {e}")
            return None, 0
            
    def get_best_valid_bits(self, pixel_format):
        """获取最佳有效位数"""
        if pixel_format in (GxPixelFormatEntry.MONO8,
                           GxPixelFormatEntry.BAYER_GR8, GxPixelFormatEntry.BAYER_RG8,
                           GxPixelFormatEntry.BAYER_GB8, GxPixelFormatEntry.BAYER_BG8,
                           GxPixelFormatEntry.RGB8, GxPixelFormatEntry.BGR8,
                           GxPixelFormatEntry.R8, GxPixelFormatEntry.B8, GxPixelFormatEntry.G8):
            return DxValidBit.BIT0_7
        elif pixel_format in (GxPixelFormatEntry.MONO10, GxPixelFormatEntry.MONO10_PACKED, GxPixelFormatEntry.MONO10_P,
                             GxPixelFormatEntry.BAYER_GR10, GxPixelFormatEntry.BAYER_RG10,
                             GxPixelFormatEntry.BAYER_GB10, GxPixelFormatEntry.BAYER_BG10,
                             GxPixelFormatEntry.BAYER_GR10_P, GxPixelFormatEntry.BAYER_RG10_P,
                             GxPixelFormatEntry.BAYER_GB10_P, GxPixelFormatEntry.BAYER_BG10_P,
                             GxPixelFormatEntry.BAYER_GR10_PACKED, GxPixelFormatEntry.BAYER_RG10_PACKED,
                             GxPixelFormatEntry.BAYER_GB10_PACKED, GxPixelFormatEntry.BAYER_BG10_PACKED):
            return DxValidBit.BIT2_9
        elif pixel_format in (GxPixelFormatEntry.MONO12, GxPixelFormatEntry.MONO12_PACKED, GxPixelFormatEntry.MONO12_P,
                             GxPixelFormatEntry.BAYER_GR12, GxPixelFormatEntry.BAYER_RG12,
                             GxPixelFormatEntry.BAYER_GB12, GxPixelFormatEntry.BAYER_BG12,
                             GxPixelFormatEntry.BAYER_GR12_P, GxPixelFormatEntry.BAYER_RG12_P,
                             GxPixelFormatEntry.BAYER_GB12_P, GxPixelFormatEntry.BAYER_BG12_P,
                             GxPixelFormatEntry.BAYER_GR12_PACKED, GxPixelFormatEntry.BAYER_RG12_PACKED,
                             GxPixelFormatEntry.BAYER_GB12_PACKED, GxPixelFormatEntry.BAYER_RG12_PACKED):
            return DxValidBit.BIT4_11
        elif pixel_format in (GxPixelFormatEntry.MONO14, GxPixelFormatEntry.MONO14_P,
                             GxPixelFormatEntry.BAYER_GR14, GxPixelFormatEntry.BAYER_RG14,
                             GxPixelFormatEntry.BAYER_GB14, GxPixelFormatEntry.BAYER_BG14,
                             GxPixelFormatEntry.BAYER_GR14_P, GxPixelFormatEntry.BAYER_RG14_P,
                             GxPixelFormatEntry.BAYER_GB14_P, GxPixelFormatEntry.BAYER_BG14_P):
            return DxValidBit.BIT6_13
        elif pixel_format in (GxPixelFormatEntry.MONO16,
                             GxPixelFormatEntry.BAYER_GR16, GxPixelFormatEntry.BAYER_RG16,
                             GxPixelFormatEntry.BAYER_GB16, GxPixelFormatEntry.BAYER_BG16):
            return DxValidBit.BIT8_15
        return DxValidBit.BIT0_7
        
    def stop(self):
        """停止采集"""
        self.running = False


class DataCollectWindow(QMainWindow):
    """数据采集主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("数据采集系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设备相关
        self.device_manager = None
        self.cam = None
        self.image_format_convert = None
        self.dev_info_list = []
        self.dev_num = 0
        
        # 线程相关
        self.preview_thread = None
        self.capture_thread = None
        
        # 状态标志
        self.is_device_open = False
        self.is_preview_mode = False
        self.is_capturing = False
        
        self.init_ui()
        self.init_device_manager()
        
    def init_ui(self):
        """初始化UI界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #0f172a; color: #e2e8f0;")
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_panel.setFixedWidth(350)
        left_panel.setStyleSheet("background-color: #1e293b; color: #e2e8f0;")
        left_layout = QVBoxLayout(left_panel)
        
        # 设备选择组
        device_group = QGroupBox("设备选择")
        device_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 16px; font-weight: bold; border: 1px solid #334155; padding-top: 10px; margin-top: 10px; background-color: #1e293b; } QLabel { color: #e2e8f0; }")
        device_layout = QVBoxLayout()
        self.device_combo = QComboBox()
        self.open_device_btn = QPushButton("打开相机")
        self.close_device_btn = QPushButton("关闭相机")
        self.close_device_btn.setEnabled(False)
        device_layout.addWidget(QLabel("选择设备:"))
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(self.open_device_btn)
        device_layout.addWidget(self.close_device_btn)
        device_group.setLayout(device_layout)
        left_layout.addWidget(device_group)
        
        # 相机参数设置组
        params_group = QGroupBox("相机参数设置")
        params_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 16px; font-weight: bold; border: 1px solid #334155; padding-top: 10px; margin-top: 10px; background-color: #1e293b; } QLabel { color: #e2e8f0; }")
        params_layout = QFormLayout()
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(list(RESOLUTION_PRESETS.keys()))
        self.resolution_combo.setCurrentText("2K (1920x1080)")
        params_layout.addRow("分辨率:", self.resolution_combo)
        
        self.apply_params_btn = QPushButton("应用参数")
        self.apply_params_btn.setEnabled(False)
        params_layout.addRow("", self.apply_params_btn)
        
        params_group.setLayout(params_layout)
        left_layout.addWidget(params_group)
        
        # 采集设置组
        capture_group = QGroupBox("采集设置")
        capture_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 16px; font-weight: bold; border: 1px solid #334155; padding-top: 10px; margin-top: 10px; background-color: #1e293b; } QLabel { color: #e2e8f0; }")
        capture_layout = QFormLayout()
        
        self.total_count_edit = QLineEdit("100")
        capture_layout.addRow("采集张数:", self.total_count_edit)
        
        self.framerate_edit = QLineEdit("20")
        capture_layout.addRow("帧率(fps):", self.framerate_edit)
        
        self.frame_skip_check = QCheckBox("启用抽帧采集")
        self.frame_skip_check.setChecked(False)
        capture_layout.addRow("", self.frame_skip_check)
        
        self.frame_skip_combo = QComboBox()
        self.frame_skip_combo.addItems(["10", "20", "30", "40", "50", "60"])
        self.frame_skip_combo.setCurrentText("10")
        self.frame_skip_combo.setEnabled(False)  # 默认禁用，只有启用抽帧采集时才可用
        capture_layout.addRow("抽帧间隔:", self.frame_skip_combo)
        
        # 连接信号，当复选框状态改变时启用/禁用下拉框
        self.frame_skip_check.stateChanged.connect(lambda state: self.frame_skip_combo.setEnabled(state == Qt.Checked))
        
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setText(os.path.join(os.getcwd(), "captured_images"))
        self.browse_path_btn = QPushButton("浏览...")
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.save_path_edit)
        path_layout.addWidget(self.browse_path_btn)
        capture_layout.addRow("保存路径:", path_layout)
        
        capture_group.setLayout(capture_layout)
        left_layout.addWidget(capture_group)
        
        # 控制按钮组
        control_group = QGroupBox("控制")
        control_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 16px; font-weight: bold; border: 1px solid #334155; padding-top: 10px; margin-top: 10px; background-color: #1e293b; } QLabel { color: #e2e8f0; }")
        control_layout = QVBoxLayout()
        
        self.preview_btn = QPushButton("开始预览")
        self.preview_btn.setEnabled(False)
        self.stop_preview_btn = QPushButton("停止预览")
        self.stop_preview_btn.setEnabled(False)
        
        self.start_capture_btn = QPushButton("开始采集")
        self.start_capture_btn.setEnabled(False)
        self.stop_capture_btn = QPushButton("停止采集")
        self.stop_capture_btn.setEnabled(False)
        
        control_layout.addWidget(self.preview_btn)
        control_layout.addWidget(self.stop_preview_btn)
        control_layout.addWidget(self.start_capture_btn)
        control_layout.addWidget(self.stop_capture_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("准备就绪")
        control_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.progress_label)
        
        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)
        
        left_layout.addStretch()
        main_layout.addWidget(left_panel)
        
        # 右侧图像显示区域
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #0f172a; color: #e2e8f0;")
        right_layout = QVBoxLayout(right_panel)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 2px solid #334155; background-color: #0f172a; color: #e2e8f0;")
        self.image_label.setText("等待打开相机...")
        self.image_label.setMinimumSize(800, 600)
        right_layout.addWidget(self.image_label)
        
        main_layout.addWidget(right_panel, 1)
        
        # 连接信号槽
        self.open_device_btn.clicked.connect(self.open_device)
        self.close_device_btn.clicked.connect(self.close_device)
        self.apply_params_btn.clicked.connect(self.apply_camera_params)
        self.browse_path_btn.clicked.connect(self.browse_save_path)
        self.preview_btn.clicked.connect(self.start_preview)
        self.stop_preview_btn.clicked.connect(self.stop_preview)
        self.start_capture_btn.clicked.connect(self.start_capture)
        self.stop_capture_btn.clicked.connect(self.stop_capture)
        
    def init_device_manager(self):
        """初始化设备管理器"""
        try:
            self.device_manager = gx.DeviceManager()
            self.dev_num, self.dev_info_list = self.device_manager.update_all_device_list()
            
            if self.dev_num == 0:
                QMessageBox.warning(self, "警告", "未检测到设备，请连接相机后重启程序！")
                return
                
            # 添加设备到下拉框
            for dev_info in self.dev_info_list:
                self.device_combo.addItem(dev_info.get("display_name"))
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"初始化设备管理器失败: {e}")
            
    def open_device(self):
        """打开设备"""
        try:
            if self.dev_num == 0:
                QMessageBox.warning(self, "警告", "没有可用设备！")
                return
                
            index = self.device_combo.currentIndex()
            if index < 0:
                return
                
            sn = self.dev_info_list[index].get("sn")
            self.cam = self.device_manager.open_device_by_sn(sn)
            
            # 创建图像格式转换对象
            self.image_format_convert = self.device_manager.create_image_format_convert()
            
            self.is_device_open = True
            self.open_device_btn.setEnabled(False)
            self.close_device_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)
            self.apply_params_btn.setEnabled(True)
            
            # 自动启动预览
            QTimer.singleShot(100, self.start_preview)
            
            QMessageBox.information(self, "成功", "设备打开成功，正在启动预览...")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开设备失败: {e}")
            
    def close_device(self):
        """关闭设备"""
        try:
            if self.is_preview_mode:
                self.stop_preview()
            if self.is_capturing:
                self.stop_capture()
                
            if self.cam:
                self.cam.close_device()
                self.cam = None
                
            self.is_device_open = False
            self.open_device_btn.setEnabled(True)
            self.close_device_btn.setEnabled(False)
            self.preview_btn.setEnabled(False)
            self.apply_params_btn.setEnabled(False)
            self.start_capture_btn.setEnabled(False)
            self.image_label.setText("设备已关闭")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"关闭设备失败: {e}")
            
    def apply_camera_params(self):
        """应用相机参数"""
        if not self.is_device_open:
            return
        
        # 如果正在预览或采集，提示用户先停止
        if self.is_preview_mode or self.is_capturing:
            QMessageBox.warning(self, "提示", "请先停止预览或采集后再应用参数！")
            return
            
        try:
            remote_feature = self.cam.get_remote_device_feature_control()
            
            # 设置分辨率
            resolution_text = self.resolution_combo.currentText()
            width, height = RESOLUTION_PRESETS[resolution_text]
            
            # 检查是否可写
            if self.cam.Width.is_writable() and self.cam.Height.is_writable():
                self.cam.Width.set(width)
                self.cam.Height.set(height)
            else:
                QMessageBox.warning(self, "提示", "分辨率当前不可写，请检查相机状态")
                return
            
            # 设置帧率
            framerate = float(self.framerate_edit.text())
            if remote_feature.is_implemented("AcquisitionFrameRateMode"):
                if remote_feature.is_writable("AcquisitionFrameRateMode"):
                    remote_feature.get_enum_feature("AcquisitionFrameRateMode").set("On")
            if remote_feature.is_implemented("AcquisitionFrameRate"):
                if remote_feature.is_writable("AcquisitionFrameRate"):
                    remote_feature.get_float_feature("AcquisitionFrameRate").set(framerate)
                else:
                    QMessageBox.warning(self, "提示", "帧率当前不可写，请检查相机状态")
                    return
                
            QMessageBox.information(self, "成功", f"参数应用成功！\n分辨率: {width}x{height}\n帧率: {framerate} fps")
            
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的帧率数值！")
        except Exception as e:
            error_msg = str(e)
            if "not writable" in error_msg or "AccessException" in error_msg:
                QMessageBox.warning(self, "提示", "参数当前不可写。\n请先停止预览或采集后再应用参数。")
            else:
                QMessageBox.critical(self, "错误", f"应用参数失败: {error_msg}")
            
    def browse_save_path(self):
        """浏览保存路径"""
        path = QFileDialog.getExistingDirectory(self, "选择保存路径", self.save_path_edit.text())
        if path:
            self.save_path_edit.setText(path)
            
    def start_preview(self):
        """开始预览"""
        if not self.is_device_open or self.is_capturing:
            return
            
        try:
            # 停止采集（如果正在采集）
            if self.capture_thread and self.capture_thread.isRunning():
                self.stop_capture()
                
            # 启动数据流
            self.cam.stream_on()
            
            # 创建预览线程
            self.preview_thread = PreviewThread(self.cam, self.image_format_convert)
            self.preview_thread.image_signal.connect(self.update_preview_image)
            self.preview_thread.start()
            
            self.is_preview_mode = True
            self.preview_btn.setEnabled(False)
            self.stop_preview_btn.setEnabled(True)
            self.start_capture_btn.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"开始预览失败: {e}")
            
    def stop_preview(self):
        """停止预览"""
        try:
            if self.preview_thread:
                self.preview_thread.stop()
                self.preview_thread.wait(2000)
                self.preview_thread = None
                
            if self.cam:
                self.cam.stream_off()
                
            self.is_preview_mode = False
            self.preview_btn.setEnabled(True)
            self.stop_preview_btn.setEnabled(False)
            self.start_capture_btn.setEnabled(True)
            self.image_label.setText("预览已停止")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止预览失败: {e}")
            
    def update_preview_image(self, numpy_image):
        """更新预览图像"""
        try:
            height, width, channel = numpy_image.shape
            q_image = QImage(numpy_image.data, width, height, width * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            
            # 缩放以适应Label
            label_size = self.image_label.size()
            scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"更新预览图像错误: {e}")
            
    def start_capture(self):
        """开始采集"""
        if not self.is_device_open or self.is_preview_mode:
            return
            
        try:
            # 验证参数
            total_count = int(self.total_count_edit.text())
            if total_count <= 0:
                QMessageBox.warning(self, "警告", "采集张数必须大于0！")
                return
                
            save_path = self.save_path_edit.text()
            if not save_path:
                QMessageBox.warning(self, "警告", "请设置保存路径！")
                return
                
            # 停止预览（如果正在预览）
            if self.is_preview_mode:
                self.stop_preview()
                
            # 设置帧率
            framerate = float(self.framerate_edit.text())
            remote_feature = self.cam.get_remote_device_feature_control()
            if remote_feature.is_implemented("AcquisitionFrameRateMode"):
                remote_feature.get_enum_feature("AcquisitionFrameRateMode").set("On")
            if remote_feature.is_implemented("AcquisitionFrameRate"):
                remote_feature.get_float_feature("AcquisitionFrameRate").set(framerate)
                
            # 启动数据流
            self.cam.stream_on()
            
            # 创建采集参数
            if self.frame_skip_check.isChecked():
                frame_skip = int(self.frame_skip_combo.currentText())
            else:
                frame_skip = 1
            capture_params = {
                'save_path': save_path,
                'total_count': total_count,
                'frame_skip': frame_skip
            }
            
            # 创建采集线程
            self.capture_thread = CaptureThread(self.cam, self.image_format_convert, capture_params)
            self.capture_thread.progress_signal.connect(self.update_capture_progress)
            self.capture_thread.finished_signal.connect(self.capture_finished)
            self.capture_thread.start()
            
            self.is_capturing = True
            self.start_capture_btn.setEnabled(False)
            self.stop_capture_btn.setEnabled(True)
            self.preview_btn.setEnabled(False)
            self.image_label.setText("正在采集，画面已关闭...")
            self.progress_bar.setMaximum(total_count)
            self.progress_bar.setValue(0)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"开始采集失败: {e}")
            
    def stop_capture(self):
        """停止采集"""
        try:
            if self.capture_thread:
                self.capture_thread.stop()
                self.capture_thread.wait(3000)
                self.capture_thread = None
                
            if self.cam:
                self.cam.stream_off()
                
            self.is_capturing = False
            self.start_capture_btn.setEnabled(True)
            self.stop_capture_btn.setEnabled(False)
            self.preview_btn.setEnabled(True)
            self.image_label.setText("采集已停止")
            self.progress_label.setText("采集已停止")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止采集失败: {e}")
            
    def update_capture_progress(self, current, total):
        """更新采集进度"""
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"已采集: {current}/{total}")
        
    def capture_finished(self):
        """采集完成"""
        self.is_capturing = False
        self.start_capture_btn.setEnabled(True)
        self.stop_capture_btn.setEnabled(False)
        self.preview_btn.setEnabled(True)
        self.image_label.setText("采集完成！")
        self.progress_label.setText("采集完成！")
        
        if self.cam:
            self.cam.stream_off()
            
        QMessageBox.information(self, "完成", "数据采集完成！")
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.is_preview_mode:
            self.stop_preview()
        if self.is_capturing:
            self.stop_capture()
        if self.is_device_open:
            self.close_device()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DataCollectWindow()
    window.show()
    sys.exit(app.exec_())

