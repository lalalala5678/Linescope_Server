#!/usr/bin/env python3
"""
数据格式升级脚本
为现有的数据文件添加 wire_foreign_object 列
"""
import random
from pathlib import Path

def upgrade_data_format():
    """升级数据文件格式，添加异物检测列"""
    data_dir = Path(__file__).resolve().parent / "data"
    data_file = data_dir / "data.txt"
    
    if not data_file.exists():
        print(f"数据文件不存在: {data_file}")
        return
    
    print(f"读取数据文件: {data_file}")
    with data_file.open('r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        print("数据文件为空")
        return
    
    # 检查是否已经包含异物检测列
    header = lines[0].strip()
    if "wire_foreign_object" in header:
        print("数据文件已包含异物检测列，无需升级")
        return
    
    print(f"原始表头: {header}")
    
    # 更新表头
    new_header = header + ",wire_foreign_object\n"
    print(f"新表头: {new_header.strip()}")
    
    # 更新数据行，为每行添加异物检测值（随机生成，约5%概率为1）
    updated_lines = [new_header]
    
    for i, line in enumerate(lines[1:], 1):
        if line.strip():  # 跳过空行
            # 生成异物检测值：约5%概率检测到异物
            wire_foreign_object = 1 if random.random() < 0.05 else 0
            updated_line = line.strip() + f",{wire_foreign_object}\n"
            updated_lines.append(updated_line)
    
    # 写入更新后的数据
    print(f"更新 {len(updated_lines)-1} 行数据")
    with data_file.open('w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    
    print(f"数据格式升级完成!")
    
    # 验证更新结果
    print("\n验证更新结果:")
    with data_file.open('r', encoding='utf-8') as f:
        first_few_lines = [next(f) for _ in range(min(3, len(updated_lines)))]
    
    for i, line in enumerate(first_few_lines):
        print(f"  第{i+1}行: {line.strip()}")

if __name__ == "__main__":
    upgrade_data_format()