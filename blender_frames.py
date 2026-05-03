"""
参数化建筑建模：情感分析可视化走廊
根据 CSV 数据生成矩形实体框序列
"""
import bpy
import bmesh
import csv
import os
import math

# ============== 用户需要修改的路径 ==============
CSV_FILE_PATH = r"C:\Users\Administrator\Desktop\算法\sentiment_analysis_result.csv"
# ===========================================

print("=" * 50)
print("开始运行 Blender 情感分析可视化脚本")
print("=" * 50)

# 参数设置
SPACING = 3.0           # Y轴间距（米）
THICKNESS = 0.15        # 框的深度厚度（米） - 减小
FRAME_THICKNESS = 0.1  # 实体截面厚度（米） - 减小

# 映射范围
WIDTH_MIN, WIDTH_MAX = 2.0, 6.0      # 内部宽度（米）
HEIGHT_MIN, HEIGHT_MAX = 2.2, 8.0      # 内部高度（米）
ROTATION_MIN, ROTATION_MAX = 0, 60       # 旋转角度（度）

def remap(value, in_min, in_max, out_min, out_max):
    """线性映射函数"""
    # 考虑输入范围可能为负值
    if in_max - in_min == 0:
        return out_min
    normalized = (value - in_min) / (in_max - in_min)
    return out_min + normalized * (out_max - out_min)

def clear_existing_frames():
    """清空场景中之前生成的实体框"""
    # 删除所有 Frame_ 相关对象（包括父对象和子对象）
    objects_to_delete = [obj for obj in bpy.data.objects if obj.name.startswith("Frame_")]
    for obj in objects_to_delete:
        bpy.data.objects.remove(obj, do_unlink=True)

    # 删除空的集合
    collections_to_delete = [col for col in bpy.data.collections if col.name.startswith("Frame_")]
    for col in collections_to_delete:
        bpy.data.collections.remove(col)

    print(f"已清空 {len(objects_to_delete)} 个之前的实体框")

def create_rectangular_solid_frame(obj_name, width, height, position, rotation_y):
    """
    创建中空矩形实体框（门框样式）- 4个边框组成
    - width: 门洞内宽
    - height: 门洞内高
    - position: (x, y, z) 位置，沿 Y 轴排列
    - rotation_y: 绕 Y 轴旋转角度（度）
    框的平面垂直于 Y 轴
    """
    t = FRAME_THICKNESS  # 边框厚度 0.3m
    w = width           # 门洞内宽
    h = height         # 门洞内高
    depth = THICKNESS   # 框的深度（Y方向）

    # 创建单一 BMesh 和对象
    mesh = bpy.data.meshes.new(obj_name)
    bm = bmesh.new()

    # ========== 4个边框的尺寸和中心位置 ==========
    # 下边框: 宽=w+2t, 深=depth, 高=t, 中心=(0, depth/2, t/2)
    # 上边框: 宽=w+2t, 深=depth, 高=t, 中心=(0, depth/2, h+t/2)
    # 左边框: 宽=t, 深=depth, 高=h, 中心=(-(w+t)/2, depth/2, h/2+t)
    # 右边框: 宽=t, 深=depth, 高=h, 中心=((w+t)/2, depth/2, h/2+t)

    def add_box(bm, cx, cy, cz, size_x, size_y, size_z):
        """在 (cx, cy, cz) 位置创建尺寸为 (size_x, size_y, size_z) 的立方体"""
        hx, hy, hz = size_x / 2, size_y / 2, size_z / 2
        # 8个顶点
        v = [
            bm.verts.new((cx - hx, cy - hy, cz - hz)),  # 0: -x, -y, -z
            bm.verts.new((cx + hx, cy - hy, cz - hz)),  # 1: +x, -y, -z
            bm.verts.new((cx + hx, cy + hy, cz - hz)),  # 2: +x, +y, -z
            bm.verts.new((cx - hx, cy + hy, cz - hz)),  # 3: -x, +y, -z
            bm.verts.new((cx - hx, cy - hy, cz + hz)),  # 4: -x, -y, +z
            bm.verts.new((cx + hx, cy - hy, cz + hz)),  # 5: +x, -y, +z
            bm.verts.new((cx + hx, cy + hy, cz + hz)),  # 6: +x, +y, +z
            bm.verts.new((cx - hx, cy + hy, cz + hz)),  # 7: -x, +y, +z
        ]
        # 6个面 - 严格按顺序保证法线向外
        bm.faces.new([v[0], v[3], v[2], v[1]])  # 底 (-z)
        bm.faces.new([v[4], v[5], v[6], v[7]])  # 顶 (+z)
        bm.faces.new([v[0], v[1], v[5], v[4]])  # 前 (-y)
        bm.faces.new([v[2], v[3], v[7], v[6]])  # 后 (+y)
        bm.faces.new([v[0], v[4], v[7], v[3]])  # 左 (-x)
        bm.faces.new([v[1], v[2], v[6], v[5]])  # 右 (+x)

    # 4个边框的位置和尺寸
    # 下边框
    add_box(bm, 0, depth/2, t/2, w + 2*t, depth, t)
    # 上边框
    add_box(bm, 0, depth/2, h + t/2, w + 2*t, depth, t)
    # 左边框
    add_box(bm, -(w + t)/2, depth/2, h/2 + t, t, depth, h)
    # 右边框
    add_box(bm, (w + t)/2, depth/2, h/2 + t, t, depth, h)

    # 焊接重合顶点，形成单一实体
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    # 重新计算法线
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.verts.ensure_lookup_table()

    # 生成 Mesh
    bm.to_mesh(mesh)
    bm.free()

    # 创建对象
    obj = bpy.data.objects.new(obj_name, mesh)
    obj.location = position
    obj.rotation_euler = (0, math.radians(rotation_y), 0)
    bpy.context.collection.objects.link(obj)

    return obj

def main():
    # 清空之前的实体框
    clear_existing_frames()

    # ============== 读取CSV ==============
    print(f"\n检查 CSV 文件: {CSV_FILE_PATH}")

    if not os.path.exists(CSV_FILE_PATH):
        print(f"错误：找不到 CSV 文件 {CSV_FILE_PATH}")
        # 尝试列出目录内容帮助调试
        csv_dir = os.path.dirname(CSV_FILE_PATH)
        if os.path.exists(csv_dir):
            print(f"目录 {csv_dir} 存在，内容:")
            for f in os.listdir(csv_dir):
                print(f"  - {f}")
        return

    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)

    print(f"CSV 列名: {reader.fieldnames}")
    print(f"读取到 {len(data)} 行数据")

    # 调试：打印前几行数据
    for i, row in enumerate(data[:3]):
        print(f"  Row {i+1}: {row}")
    # ============== CSV 读取完成 ==============

    # 创建集合用于组织对象
    collection = bpy.data.collections.new("Frame_Collection")
    bpy.context.scene.collection.children.link(collection)

    for row in data:
        idx = int(row['Sentence_Index'])
        polarity = float(row['Polarity'])
        subjectivity = float(row['Subjectivity'])

        # 映射Polarity到宽度和高度
        width = remap(polarity, -1.0, 1.0, WIDTH_MIN, WIDTH_MAX)
        height = remap(polarity, -1.0, 1.0, HEIGHT_MIN, HEIGHT_MAX)

        # 映射Subjectivity到旋转角度（绕Y轴）
        rotation_y = remap(subjectivity, 0.0, 1.0, ROTATION_MIN, ROTATION_MAX)

        # 计算位置：沿Y轴排列，框的平面垂直于Y轴
        # 位置(x, y, z) = (0, idx * SPACING, 0)
        position = (0, idx * SPACING, 0)

        # 创建实体框
        obj_name = f"Frame_{idx:02d}"
        create_rectangular_solid_frame(
            obj_name=obj_name,
            width=width,
            height=height,
            position=position,
            rotation_y=rotation_y
        )

        # 移动到集合
        obj = bpy.data.objects.get(obj_name)
        if obj:
            for col in obj.users_collection:
                col.objects.unlink(obj)
            collection.objects.link(obj)

        print(f"Frame {idx}: Polarity={polarity}, Subjectivity={subjectivity}")
        print(f"  -> Width={width:.2f}m, Height={height:.2f}m, Rotation={rotation_y:.1f}°")

    print(f"\n{'='*50}")
    print(f"完成！共创建 {len(data)} 个实体框")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()