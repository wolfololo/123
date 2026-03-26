import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import json
import pandas as pd
import ifcopenshell
from collections import defaultdict, OrderedDict
import os
import sys
from pathlib import Path


# 重定向标准输出到GUI文本框
class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)

    def flush(self):
        pass


class IFCProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("模型文件处理")
        self.root.geometry("1000x700")
        self.root.configure(bg="#0a2647")

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", background="#0a2647", foreground="white", font=("微软雅黑", 10))
        self.style.configure("TButton", background="#144272", foreground="white", font=("微软雅黑", 10))
        self.style.configure("TFrame", background="#0a2647")
        self.style.configure("TLabelframe", background="#0a2647", foreground="white")
        self.style.configure("TLabelframe.Label", background="#0a2647", foreground="#2c74b3",
                             font=("微软雅黑", 11, "bold"))
        self.style.configure("TEntry", fieldbackground="#205295", foreground="white")
        self.style.configure("TCombobox", fieldbackground="#205295", foreground="white")

        # 创建主框架
        self.create_widgets()

        # 存储数据
        self.all_data = None
        self.data_by_type = None
        self.profile_data = None
        self.last_output_dir = None  # 记录最后的输出目录
        self.last_excel_file = None  # 记录最后生成的Excel文件

    def create_widgets(self):
        # 标题
        title_frame = ttk.Frame(self.root, style="TFrame")
        title_frame.pack(fill=tk.X, padx=20, pady=(20, 10))

        title_label = tk.Label(title_frame, text="模型文件处理",
                               font=("微软雅黑", 20, "bold"),
                               bg="#0a2647", fg="#2c74b3")
        title_label.pack()

        subtitle_label = tk.Label(title_frame, text="建筑信息模型数据提取与分析工具",
                                  font=("微软雅黑", 11),
                                  bg="#0a2647", fg="#8ac6d1")
        subtitle_label.pack(pady=(5, 0))

        # 主容器
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 左侧控制面板
        left_panel = ttk.LabelFrame(main_container, text="控制面板", padding=15)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # 文件路径输入
        file_frame = ttk.LabelFrame(left_panel, text="文件路径设置", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(file_frame, text="IFC文件路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ifc_path = tk.StringVar()
        ifc_entry = ttk.Entry(file_frame, textvariable=self.ifc_path, width=40)
        ifc_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_ifc).grid(row=0, column=2, padx=5)

        ttk.Label(file_frame, text="输出文件夹:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_path = tk.StringVar()
        output_entry = ttk.Entry(file_frame, textvariable=self.output_path, width=40)
        output_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_output).grid(row=1, column=2, padx=5)

        # 处理选项
        options_frame = ttk.LabelFrame(left_panel, text="处理选项", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))

        self.processing_mode = tk.IntVar(value=1)
        ttk.Radiobutton(options_frame, text="输出方式1: 生成原始表格",
                        variable=self.processing_mode, value=1).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(options_frame, text="输出方式2: 生成分类详细表格",
                        variable=self.processing_mode, value=2).pack(anchor=tk.W, pady=2)

        # 进度条
        progress_frame = ttk.LabelFrame(left_panel, text="处理进度", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 15))

        self.progress = ttk.Progressbar(progress_frame, mode='determinate', length=300)
        self.progress.pack(fill=tk.X, pady=5)

        self.status_label = ttk.Label(progress_frame, text="等待开始...")
        self.status_label.pack()

        # 控制按钮
        button_frame = ttk.Frame(left_panel, style="TFrame")
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="开始处理", command=self.start_processing,
                   style="TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="打开文件", command=self.open_output_folder,
                   style="TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出程序", command=self.root.quit).pack(side=tk.LEFT, padx=5)

        # 右侧日志和结果显示面板
        right_panel = ttk.Frame(main_container, style="TFrame")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 日志显示
        log_frame = ttk.LabelFrame(right_panel, text="处理日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, bg="#1a365d",
                                                  fg="white", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 重定向输出
        sys.stdout = RedirectText(self.log_text)

        # 分析结果显示
        result_frame = ttk.LabelFrame(right_panel, text="实体构成分析", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = scrolledtext.ScrolledText(result_frame, height=10, bg="#1a365d",
                                                     fg="#8ac6d1", font=("微软雅黑", 9))
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def browse_ifc(self):
        filename = filedialog.askopenfilename(
            title="选择IFC文件",
            filetypes=[("IFC files", "*.ifc"), ("All files", "*.*")]
        )
        if filename:
            # 确保路径没有多余的引号
            clean_path = filename.strip('"').strip("'")
            self.ifc_path.set(clean_path)
            # 自动设置输出路径
            if not self.output_path.get():
                output_dir = os.path.join(os.path.dirname(clean_path), "IFC输出结果")
                self.output_path.set(output_dir)

    def browse_output(self):
        directory = filedialog.askdirectory(title="选择输出文件夹")
        if directory:
            clean_dir = directory.strip('"').strip("'")
            self.output_path.set(clean_dir)

    def open_output_folder(self):
        """打开生成的Excel文件"""
        output_path = self.output_path.get()
        
        if not output_path:
            messagebox.showwarning("提示", "请先设置输出文件夹路径！")
            return
        
        # 清理路径
        clean_path = output_path.strip('"').strip("'")
        
        # 检查路径是否存在
        if not os.path.exists(clean_path):
            messagebox.showwarning("提示", f"输出文件夹不存在：{clean_path}\n请先运行处理程序生成文件。")
            return
        
        try:
            # 查找所有Excel文件
            excel_files = []
            for file in os.listdir(clean_path):
                if file.endswith('.xlsx'):
                    excel_files.append(os.path.join(clean_path, file))
            
            # 递归查找子目录中的Excel文件
            for root, dirs, files in os.walk(clean_path):
                for file in files:
                    if file.endswith('.xlsx'):
                        full_path = os.path.join(root, file)
                        if full_path not in excel_files:
                            excel_files.append(full_path)
            
            if not excel_files:
                messagebox.showwarning("提示", f"在 {clean_path} 中没有找到Excel文件！\n请先运行处理程序生成文件。")
                return
            
            # 按修改时间排序，获取最新的文件
            excel_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            latest_file = excel_files[0]
            
            # 根据操作系统打开Excel文件
            if sys.platform == 'win32':
                os.startfile(latest_file)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{latest_file}"')
            else:  # Linux
                os.system(f'xdg-open "{latest_file}"')
            
            print(f"✅ 已打开Excel文件: {os.path.basename(latest_file)}")
            
            # 如果有多个文件，提示用户
            if len(excel_files) > 1:
                print(f"ℹ️ 共找到 {len(excel_files)} 个Excel文件，已打开最新的文件")
                
        except Exception as e:
            messagebox.showerror("错误", f"打开Excel文件失败: {str(e)}")
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.result_text.delete(1.0, tk.END)

    def start_processing(self):
        if not self.ifc_path.get():
            messagebox.showerror("错误", "请选择IFC文件路径！")
            return

        if not self.output_path.get():
            messagebox.showerror("错误", "请选择输出文件夹！")
            return

        # 在新线程中运行处理
        thread = threading.Thread(target=self.run_processing)
        thread.daemon = True
        thread.start()

    def run_processing(self):
        try:
            self.progress['value'] = 0
            self.status_label.config(text="开始处理...")

            # 清理路径，去除多余的引号
            raw_ifc_path = self.ifc_path.get()
            ifc_path = raw_ifc_path.strip('"').strip("'")

            raw_output_path = self.output_path.get()
            output_dir = raw_output_path.strip('"').strip("'")

            print(f"IFC文件路径: {ifc_path}")
            print(f"输出文件夹: {output_dir}")

            # 检查文件是否存在
            if not os.path.exists(ifc_path):
                print(f"❌ 文件不存在: {ifc_path}")
                print(f"❌ 请检查路径是否正确，文件是否存在")
                return

            print("=" * 60)
            print("步骤1: 提取IFC文件中所有实体属性...")
            print("=" * 60)

            self.update_progress(10, "正在提取IFC实体属性...")
            self.extract_all_entities(ifc_path)

            # 步骤2: 统计实体类型
            print("\n" + "=" * 60)
            print("步骤2: 统计实体类型...")
            print("=" * 60)

            self.update_progress(40, "正在分类实体类型...")
            self.create_subtype_profiles()

            # 根据选择的方式进行处理
            if self.processing_mode.get() == 1:
                # 方式1: 生成原始表格
                print("\n" + "=" * 60)
                print("输出方式1: 生成原始表格...")
                print("=" * 60)

                self.update_progress(70, "正在生成原始表格...")
                self.generate_raw_table(output_dir)
            else:
                # 方式2: 生成五大类实体详细表格
                print("\n" + "=" * 60)
                print("输出方式2: 生成五大类实体详细表格...")
                print("=" * 60)

                self.update_progress(70, "正在生成五大类实体详细表格...")
                self.generate_detailed_tables(output_dir)

            # 步骤3: 实体构成分析
            print("\n" + "=" * 60)
            print("步骤3: 实体构成分析...")
            print("=" * 60)

            self.update_progress(90, "正在进行实体构成分析...")
            self.analyze_subtype_composition()

            self.update_progress(100, "处理完成！")
            print("\n✅ 所有处理已完成！")

            # 在结果框中显示最终分析结果
            self.display_analysis_results()

        except Exception as e:
            print(f"❌ 处理过程中出现错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def update_progress(self, value, message):
        self.progress['value'] = value
        self.status_label.config(text=message)
        self.root.update_idletasks()

    # ========== 原2.3代码功能 ==========
    def get_properties_from_pset(self, pset_entity):
        properties = {}
        if hasattr(pset_entity, 'HasProperties'):
            for prop in pset_entity.HasProperties:
                prop_name = prop.Name
                if prop.is_a('IfcPropertySingleValue'):
                    prop_value = prop.NominalValue.wrappedValue if prop.NominalValue else None
                elif prop.is_a('IfcPropertyEnumeratedValue'):
                    prop_value = prop.EnumerationValues[0].wrappedValue if prop.EnumerationValues else None
                else:
                    prop_value = str(prop)
                properties[prop_name] = prop_value
        return properties

    def get_quantities_from_qto(self, qto_entity):
        quantities = {}
        if hasattr(qto_entity, 'Quantities'):
            for quantity in qto_entity.Quantities:
                qty_name = quantity.Name
                if hasattr(quantity, 'LengthValue'):
                    qty_value = quantity.LengthValue
                elif hasattr(quantity, 'AreaValue'):
                    qty_value = quantity.AreaValue
                elif hasattr(quantity, 'VolumeValue'):
                    qty_value = quantity.VolumeValue
                elif hasattr(quantity, 'WeightValue'):
                    qty_value = quantity.WeightValue
                else:
                    qty_value = None
                quantities[qty_name] = qty_value
        return quantities

    def get_material_info(self, element):
        materials = []
        if hasattr(element, 'HasAssociations'):
            for assoc in element.HasAssociations:
                if assoc.is_a('IfcRelAssociatesMaterial'):
                    relating_mat = assoc.RelatingMaterial
                    if relating_mat.is_a('IfcMaterial'):
                        materials.append(relating_mat.Name)
                    elif relating_mat.is_a('IfcMaterialLayerSet'):
                        for layer in relating_mat.MaterialLayers:
                            if layer.Material:
                                materials.append(layer.Material.Name)
        return materials

    def extract_element_data(self, element):
        data = OrderedDict()

        # 基本属性
        data['GlobalId'] = element.GlobalId
        data['Name'] = getattr(element, 'Name', None)
        data['ObjectType'] = getattr(element, 'ObjectType', None)
        data['PredefinedType'] = getattr(element, 'PredefinedType', 'NOTDEFINED')
        data['IFC_Type'] = element.is_a()

        # 属性集数据
        data['PropertySets'] = {}
        if hasattr(element, 'IsDefinedBy'):
            for rel in element.IsDefinedBy:
                if rel.is_a('IfcRelDefinesByProperties'):
                    prop_def = rel.RelatingPropertyDefinition
                    if prop_def.is_a('IfcPropertySet'):
                        pset_name = prop_def.Name
                        data['PropertySets'][pset_name] = self.get_properties_from_pset(prop_def)
                    elif prop_def.is_a('IfcElementQuantity'):
                        qto_name = prop_def.Name
                        if 'QuantitySets' not in data:
                            data['QuantitySets'] = {}
                        data['QuantitySets'][qto_name] = self.get_quantities_from_qto(prop_def)

        # 类型信息
        data['TypeInfo'] = None
        if hasattr(element, 'IsDefinedBy'):
            for rel in element.IsDefinedBy:
                if rel.is_a('IfcRelDefinesByType'):
                    type_entity = rel.RelatingType
                    type_info = {
                        'TypeName': getattr(type_entity, 'Name', None),
                        'Type_GlobalId': type_entity.GlobalId,
                        'Type_ObjectType': getattr(type_entity, 'ObjectType', None)
                    }
                    data['TypeInfo'] = type_info
                    break

        # 空间位置信息
        data['ContainedIn'] = None
        if hasattr(element, 'ContainedInStructure'):
            for rel in element.ContainedInStructure:
                if rel.is_a('IfcRelContainedInSpatialStructure'):
                    spatial_obj = rel.RelatingStructure
                    data['ContainedIn'] = {
                        'Spatial_Type': spatial_obj.is_a(),
                        'Spatial_Name': getattr(spatial_obj, 'Name', None),
                        'Spatial_GlobalId': spatial_obj.GlobalId
                    }
                    break

        # 材料信息
        data['Materials'] = self.get_material_info(element)

        # 几何表达信息
        data['GeometryShape'] = None
        if hasattr(element, 'Representation'):
            if element.Representation:
                rep = element.Representation
                data['GeometryShape'] = rep.is_a()

        # 定位信息
        data['Placement'] = None
        if hasattr(element, 'ObjectPlacement'):
            if element.ObjectPlacement:
                data['Placement'] = element.ObjectPlacement.is_a()

        return data

    def extract_all_entities(self, ifc_file_path):
        print(f"正在打开IFC文件: {ifc_file_path}")

        try:
            file = ifcopenshell.open(ifc_file_path)
        except Exception as e:
            print(f"❌ 无法打开IFC文件: {str(e)}")
            raise

        target_element_types = [
            'IfcColumn',
            'IfcBeam',
            'IfcPlate',
            'IfcElementAssembly',
            'IfcDiscreteAccessory'
        ]

        all_elements_data = []

        for elem_type in target_element_types:
            print(f"正在提取 {elem_type} ...")
            elements = file.by_type(elem_type)

            for elem in elements:
                elem_data = self.extract_element_data(elem)
                all_elements_data.append(elem_data)

        print(f"提取完成！共处理 {len(all_elements_data)} 个核心构件。")

        # 按IFC类型分组
        self.data_by_type = defaultdict(list)
        for item in all_elements_data:
            self.data_by_type[item['IFC_Type']].append(item)

        self.all_data = all_elements_data
        return all_elements_data

    # ========== 原2.4代码功能 ==========
    def safe_get_first_item(self, items, default='无'):
        if items and isinstance(items, list) and len(items) > 0:
            return items[0]
        return default

    def create_subtype_profiles(self):
        if self.data_by_type is None:
            print("错误：没有找到分类数据")
            return

        all_profiles = {}
        core_elements = ['IfcColumn', 'IfcBeam', 'IfcPlate', 'IfcElementAssembly', 'IfcDiscreteAccessory']

        for elem_type in core_elements:
            if elem_type in self.data_by_type:
                instances = self.data_by_type[elem_type]
                profile = defaultdict(list)

                for instance in instances:
                    object_type = instance.get('ObjectType')

                    if object_type and object_type != 'None':
                        subtype_key = object_type
                    else:
                        type_info = instance.get('TypeInfo')
                        if type_info and isinstance(type_info, dict):
                            type_name = type_info.get('TypeName')
                        else:
                            type_name = None

                        property_sets = instance.get('PropertySets', {})
                        pset_column_common = property_sets.get('Pset_ColumnCommon', {})

                        materials = instance.get('Materials')
                        material_str = self.safe_get_first_item(materials, '未知材料')

                        subtype_key = (type_name or
                                       pset_column_common.get('Reference') or
                                       material_str or
                                       '未知子类')

                    if subtype_key is None:
                        subtype_key = '未知子类'
                    else:
                        subtype_key = str(subtype_key).strip()
                        if subtype_key == '':
                            subtype_key = '未知子类'

                    profile[subtype_key].append(instance)

                subtype_report = {}
                for subtype, items in profile.items():
                    if not items:
                        continue

                    sample = items[0]

                    materials = sample.get('Materials')
                    property_sets = sample.get('PropertySets', {})

                    total_weight = 0
                    count_with_weight = 0
                    for item in items:
                        base_quantities = item.get('QuantitySets', {}).get('BaseQuantities', {})
                        weight = base_quantities.get('NetWeight')
                        if weight is not None:
                            total_weight += weight
                            count_with_weight += 1

                    avg_weight = total_weight / count_with_weight if count_with_weight > 0 else 0

                    subtype_report[subtype] = {
                        '数量': len(items),
                        '示例_GlobalId': sample.get('GlobalId', '无'),
                        '示例_材料': self.safe_get_first_item(materials, '无'),
                        '示例_参考编号': property_sets.get('Pset_ColumnCommon', {}).get('Reference', '无'),
                        '示例_底部标高': property_sets.get('Tekla Common', {}).get('Bottom elevation', '无'),
                        '关键工程量_平均净重(kg)': avg_weight
                    }

                sorted_report = dict(sorted(subtype_report.items(), key=lambda x: x[1]['数量'], reverse=True))

                print(f"{elem_type} 子类分析完成: {len(sorted_report)} 种子类")
                all_profiles[elem_type] = sorted_report

        self.profile_data = all_profiles
        return all_profiles

    # ========== 原3代码功能 ==========
    def generate_raw_table(self, output_dir):
        if self.all_data is None:
            print("错误：没有找到提取的数据")
            return

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 生成原始表格
        raw_df = pd.json_normalize(self.all_data, sep='_')
        print(f"【原始表格】形状: {raw_df.shape} (行数: {raw_df.shape[0]}, 列数: {raw_df.shape[1]})")

        # 保存Excel
        base_name = os.path.splitext(os.path.basename(self.ifc_path.get()))[0]
        raw_excel_path = os.path.join(output_dir, f'{base_name}_原始表格.xlsx')
        raw_df.to_excel(raw_excel_path, index=False)
        print(f"✅ 原始表格已保存至: {raw_excel_path}")
        
        # 记录最后生成的文件
        self.last_excel_file = raw_excel_path

    # ========== 五大类实体表格功能 ==========
    def flatten_dict(self, d, parent_key='', sep='_'):
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self.flatten_dict(v, new_key, sep=sep))
            elif isinstance(v, list):
                if v and isinstance(v[0], str):
                    items[new_key] = v[0]
                else:
                    items[new_key] = str(v)
            else:
                items[new_key] = v
        return items

    def generate_detailed_tables(self, output_dir):
        if self.data_by_type is None:
            print("错误：没有找到分类数据")
            return

        table_dir = os.path.join(output_dir, "五大类实体详细表格")
        os.makedirs(table_dir, exist_ok=True)

        core_entity_types = [
            'IfcColumn',
            'IfcBeam',
            'IfcPlate',
            'IfcElementAssembly',
            'IfcDiscreteAccessory'
        ]

        for entity_type in core_entity_types:
            if entity_type in self.data_by_type:
                entity_data_list = self.data_by_type[entity_type]

                if not entity_data_list:
                    print(f"警告: {entity_type} 没有数据，跳过。")
                    continue

                print(f"正在处理 {entity_type}，共 {len(entity_data_list)} 个实例...")

                # 收集所有可能的属性路径
                all_keys_set = set()
                flattened_samples = []

                for item in entity_data_list:
                    flat_item = self.flatten_dict(item, sep='.')
                    flattened_samples.append(flat_item)
                    all_keys_set.update(flat_item.keys())

                # 创建有序的列名列表
                preferred_first_columns = ['GlobalId', 'Name', 'ObjectType', 'IFC_Type', 'PredefinedType']
                first_columns = [col for col in preferred_first_columns if col in all_keys_set]
                other_columns = sorted([col for col in all_keys_set if col not in first_columns])
                ordered_columns = first_columns + other_columns

                print(f"  发现 {len(ordered_columns)} 个不同的属性列。")

                # 构建数据行
                table_rows = []
                for flat_item in flattened_samples:
                    row = OrderedDict()
                    for col in ordered_columns:
                        row[col] = flat_item.get(col, None)
                    table_rows.append(row)

                # 创建DataFrame并保存为Excel
                df = pd.DataFrame(table_rows, columns=ordered_columns)
                output_path = os.path.join(table_dir, f'{entity_type}_详细属性表.xlsx')

                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name=entity_type)
                    worksheet = writer.sheets[entity_type]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if cell.value:
                                    max_length = max(max_length, len(str(cell.value)))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

                print(f"  表格已生成: {output_path}")
                print(f"  表格尺寸: {df.shape[0]} 行 x {df.shape[1]} 列")

    # ========== 原2.5代码功能 ==========
    def analyze_subtype_composition(self):
        if self.profile_data is None:
            print("错误：没有找到子类档案数据")
            return

        all_stats = {}

        for entity_type, subtype_profile in self.profile_data.items():
            total_instances = sum(info['数量'] for info in subtype_profile.values())
            num_subtypes = len(subtype_profile)

            sorted_subtypes = sorted(subtype_profile.items(), key=lambda x: x[1]['数量'], reverse=True)
            top3_count = sum(info['数量'] for _, info in sorted_subtypes[:3])
            top3_ratio = (top3_count / total_instances * 100) if total_instances > 0 else 0

            unknown_count = subtype_profile.get('未知子类', {'数量': 0})['数量']
            unknown_ratio = (unknown_count / total_instances * 100) if total_instances > 0 else 0

            all_stats[entity_type] = {
                '实例总数': total_instances,
                '子类数量': num_subtypes,
                '最主要子类': sorted_subtypes[0][0] if sorted_subtypes else '无',
                'Top3子类集中度': f"{top3_ratio:.1f}%",
                '未知分类占比': f"{unknown_ratio:.1f}%",
                '示例材料': sorted_subtypes[0][1]['示例_材料'] if sorted_subtypes else '无'
            }

        # 打印分析报告
        print("\n" + "=" * 80)
        print("构件子类档案综合分析报告")
        print("=" * 80)

        sorted_stats = sorted(all_stats.items(), key=lambda x: x[1]['实例总数'], reverse=True)

        for entity_type, stats in sorted_stats:
            print(f"\n▶ {entity_type}")
            print(f"   实例总数: {stats['实例总数']:>6}")
            print(f"   子类数量: {stats['子类数量']:>6}")
            print(f"   最主要子类: {stats['最主要子类']}")
            print(f"   Top3子类集中度: {stats['Top3子类集中度']:>10} （前3种占总数比例）")
            print(f"   '未知'分类占比: {stats['未知分类占比']:>10} （比例越高，数据质量风险越大）")
            print(f"   示例材料: {stats['示例材料']}")

        print("\n" + "=" * 80)
        print("报告解读与建议")
        print("=" * 80)

        for entity_type, stats in sorted_stats:
            suggestions = []
            if stats['子类数量'] == 1 and stats['实例总数'] > 10:
                suggestions.append("⚠️ 子类单一，分类字段可能无效，建议检查其他属性。")
            if float(stats['未知分类占比'].rstrip('%')) > 20:
                suggestions.append("⚠️ 大量实例未识别，数据完整性需核查。")
            if float(stats['Top3子类集中度'].rstrip('%')) > 80:
                suggestions.append("✅ 子类集中度高，模型标准化程度好。")
            if entity_type == 'IfcDiscreteAccessory' and stats['子类数量'] > 100:
                suggestions.append("🔍 子类极其繁多，建议按前缀（如'PL'、'BOLT'）进行业务归并。")

            if suggestions:
                print(f"\n{entity_type}:")
                for s in suggestions:
                    print(f"   {s}")

    def display_analysis_results(self):
        if self.profile_data is None:
            return

        self.result_text.delete(1.0, tk.END)

        # 显示实体构成统计
        self.result_text.insert(tk.END, "实体构成统计:\n")
        self.result_text.insert(tk.END, "=" * 50 + "\n\n")

        core_elements = ['IfcColumn', 'IfcBeam', 'IfcPlate', 'IfcElementAssembly', 'IfcDiscreteAccessory']

        for elem_type in core_elements:
            if elem_type in self.data_by_type:
                count = len(self.data_by_type[elem_type])
                self.result_text.insert(tk.END, f"{elem_type}: {count} 个实例\n")

        # 显示主要实体类型统计
        if self.profile_data:
            self.result_text.insert(tk.END, "\n主要实体类型统计:\n")
            self.result_text.insert(tk.END, "=" * 50 + "\n\n")

            for entity_type, profile in self.profile_data.items():
                if profile:
                    total = sum(info['数量'] for info in profile.values())
                    subtypes = len(profile)
                    main_type = list(profile.keys())[0]
                    self.result_text.insert(tk.END, f"{entity_type}:\n")
                    self.result_text.insert(tk.END, f"  总数: {total}, 子类: {subtypes}\n")
                    self.result_text.insert(tk.END, f"  主要类型: {main_type}\n\n")

        self.result_text.insert(tk.END, "✅ 分析完成！Excel表格已保存在输出文件夹中。\n")


def main():
    root = tk.Tk()
    app = IFCProcessorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()