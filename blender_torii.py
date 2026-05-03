"""
诗意长廊生成器：千本鸟居 - 增强版
14行数据插值为150个密集切片，非线性放大，极致扭转起伏
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
print("开始运行 Blender 诗意长廊脚本（千本鸟居）")
print("=" * 50)

# 参数设置
SPACING = 0.2                    # 框间距（米）- 极密
NUM_INTERPOLATED = 150                # 插值后节点数
THICKNESS = 0.05                  # 框的深度
FRAME_THICKNESS = 0.05              # 边框厚度

# 尺寸范围（极端放大）
WIDTH_MIN, WIDTH_MAX = 1.5, 8.0    # 内部宽度
HEIGHT_MIN, HEIGHT_MAX = 2.0, 10.0   # 内部高度

# 形态扭曲参数
Z_WAVE_AMPLITUDE = 1.5             # Z轴起伏幅度
Z_WAVE_FREQUENCY = 0.05            # 起伏频率
ROTATION_INCREMENT = 2.0           # 每单位Subjectivity的累积旋转增量（度）

def cosine_interpolation(y1, y2, mu):
    """
    Cosine Interpolation（余弦插值）
    在两个值之间产生平滑过渡
    """
    mu2 = (1 - math.cos(mu * math.pi)) / 2
    return y1 * (1 - mu2) + y2 * mu2

def cubic_interpolation(y0, y1, y2, y3, mu):
    """
    Cubic Hermite Spline Interpolation
    产生更平滑的曲线，适合情感数据
    """
    mu2 = mu * mu
    mu3 = mu2 * mu
    return (
        y1 +
        (-y0/2 + y2/2) * mu +
        (y0 - 5*y1/2 + 2*y2 - y3/2) * mu2 +
        (-y0/2 + 3*y1/2 - 3*y2/2 + y3/2) * mu3
    )

def interpolate_data(csv_data, num_points):
    """
    将原始14行数据插值为num_points个节点
    使用Cubic Spline保证平滑连续
    """
    n = len(csv_data)
    original_polarities = [float(row['Polarity']) for row in csv_data]
    original_subjectivities = [float(row['Subjectivity']) for row in csv_data]

    interpolated = []

    for i in range(num_points):
        # 计算当前位置对应原始数据的哪个区间
        t = i / (num_points - 1)  # 0 到 1
        index = t * (n - 1)       # 0 到 n-1
        idx = int(index)           # 整数部分
        frac = index - idx         # 小数部分

        # 获取周围的4个点用于Cubic插值
        idx0 = max(0, idx - 1)
        idx1 = idx
        idx2 = min(n - 1, idx + 1)
        idx3 = min(n - 1, idx + 2)

        # Cubic插值
        pol = cubic_interpolation(
            original_polarities[idx0],
            original_polarities[idx1],
            original_polarities[idx2],
            original_polarities[idx3],
            frac
        )

        sub = cubic_interpolation(
            original_subjectivities[idx0],
            original_subjectivities[idx1],
            original_subjectivities[idx2],
            original_subjectivities[idx3],
            frac
        )

        interpolated.append({
            'Polarity': pol,
            'Subjectivity': sub
        })

    print(f"\n[数据插值]")
    print(f"  原始: {n} 行 -> 插值后: {num_points} 个节点")
    print(f"  Polarity 范围: [{min(r['Polarity'] for r in interpolated):.4f}, {max(r['Polarity'] for r in interpolated):.4f}]")
    print(f"  Subjectivity 范围: [{min(r['Subjectivity'] for r in interpolated):.4f}, {max(r['Subjectivity'] for r in interpolated):.4f}]")

    return interpolated

def nonlinear_exaggeration(value, exponent=3):
    """
    非线性放大：保留符号的幂函数
    y = sign(x) * |x|^exponent
    将微小波动成倍放大
    """
    sign = 1 if value >= 0 else -1
    return sign * math.pow(abs(value), exponent)

def remap_nonlinear(value, in_min, in_max, out_min, out_max, exponent=3):
    """
    先进行非线性放大，再映射到输出范围
    """
    # 归一化到 -1 到 1
    if in_max - in_min == 0:
        normalized = 0
    else:
        normalized = (value - in_min) / (in_max - in_min) * 2 - 1  # 映射到 -1~1

    # 非线性放大
    amplified = nonlinear_exaggeration(normalized, exponent)

    # 映射回输出范围（-1~1 -> out_min~out_max）
    result = out_min + (amplified + 1) / 2 * (out_max - out_min)

    return result

def clear_existing_objects():
    """清空场景中之前生成的对象"""
    objects_to_delete = [obj for obj in bpy.data.objects if obj.name.startswith("Torii_")]
    for obj in objects_to_delete:
        bpy.data.objects.remove(obj, do_unlink=True)

    meshes_to_delete = [mesh for mesh in bpy.data.meshes if mesh.name.startswith("Torii_")]
    for mesh in meshes_to_delete:
        bpy.data.meshes.remove(mesh)

    print(f"已清空 {len(objects_to_delete)} 个之前的对象")

def create_rectangular_solid_frame(obj_name, width, height, position, rotation_y, z_offset):
    """
    创建中空矩形实体框（门框样式）
    参数:
        width: 门洞内宽
        height: 门洞内高
        position: (x, y, z) 位置
        rotation_y: 绕Y轴旋转角度
        z_offset: Z轴起伏偏移
    """
    t = FRAME_THICKNESS
    w = width
    h = height
    depth = THICKNESS

    mesh = bpy.data.meshes.new(obj_name)
    bm = bmesh.new()

    def add_box(bm, cx, cy, cz, size_x, size_y, size_z):
        hx, hy, hz = size_x / 2, size_y / 2, size_z / 2
        v = [
            bm.verts.new((cx - hx, cy - hy, cz - hz)),
            bm.verts.new((cx + hx, cy - hy, cz - hz)),
            bm.verts.new((cx + hx, cy + hy, cz - hz)),
            bm.verts.new((cx - hx, cy + hy, cz - hz)),
            bm.verts.new((cx - hx, cy - hy, cz + hz)),
            bm.verts.new((cx + hx, cy - hy, cz + hz)),
            bm.verts.new((cx + hx, cy + hy, cz + hz)),
            bm.verts.new((cx - hx, cy + hy, cz + hz)),
        ]
        bm.faces.new([v[0], v[3], v[2], v[1]])
        bm.faces.new([v[4], v[5], v[6], v[7]])
        bm.faces.new([v[0], v[1], v[5], v[4]])
        bm.faces.new([v[2], v[3], v[7], v[6]])
        bm.faces.new([v[0], v[4], v[7], v[3]])
        bm.faces.new([v[1], v[2], v[6], v[5]])

    # 4个边框
    add_box(bm, 0, depth/2, t/2, w + 2*t, depth, t)
    add_box(bm, 0, depth/2, h + t/2, w + 2*t, depth, t)
    add_box(bm, -(w + t)/2, depth/2, h/2 + t, t, depth, h)
    add_box(bm, (w + t)/2, depth/2, h/2 + t, t, depth, h)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.verts.ensure_lookup_table()
    bm.to_mesh(mesh)
    bm.free()

    # 应用Z轴偏移
    adjusted_pos = (position[0], position[1], position[2] + z_offset)

    obj = bpy.data.objects.new(obj_name, mesh)
    obj.location = adjusted_pos
    obj.rotation_euler = (0, math.radians(rotation_y), 0)
    bpy.context.collection.objects.link(obj)

    return obj, z_offset

def main():
    clear_existing_objects()

    # ========== 读取CSV ==========
    print(f"\n检查 CSV 文件: {CSV_FILE_PATH}")

    if not os.path.exists(CSV_FILE_PATH):
        print(f"错误：找不到 CSV 文件 {CSV_FILE_PATH}")
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

    # ========== 步骤1: 数据插值 ==========
    interpolated_data = interpolate_data(data, NUM_INTERPOLATED)

    # ========== 步骤2: 计算形态参数 ==========
    polarities = [d['Polarity'] for d in interpolated_data]
    subjectivities = [d['Subjectivity'] for d in interpolated_data]

    pol_min, pol_max = min(polarities), max(polarities)
    sub_min, sub_max = min(subjectivities), max(subjectivities)

    # ========== 步骤3: 生成长廊 ==========
    print(f"\n开始生成千本鸟居长廊...")

    collection = bpy.data.collections.new("Torii_Collection")
    bpy.context.scene.collection.children.link(collection)

    # 累积变量
    cumulative_rotation = 0.0
    cumulative_z = 0.0
    prev_height = HEIGHT_MIN

    for idx, row in enumerate(interpolated_data):
        polarity = row['Polarity']
        subjectivity = row['Subjectivity']

        # === 非线性放大映射 ===
        # Polarity -> 宽度和高度（使用三次幂放大）
        width = remap_nonlinear(
            polarity, pol_min, pol_max,
            WIDTH_MIN, WIDTH_MAX,
            exponent=3
        )

        height = remap_nonlinear(
            polarity, pol_min, pol_max,
            HEIGHT_MIN, HEIGHT_MAX,
            exponent=3
        )

        # === Z轴起伏（基于Subjectivity的正弦波） ===
        # 每一帧的Z偏移 = 累加前一个 + 正弦波扰动
        z_wave = math.sin(idx * Z_WAVE_FREQUENCY) * Z_WAVE_AMPLITUDE * subjectivity
        z_offset = cumulative_z + z_wave
        cumulative_z = z_offset  # 累积

        # === Y轴累积旋转 ===
        # 每一帧的旋转 = 上一帧 + Subjectivity增量的累积
        rotation_increment = subjectivity * ROTATION_INCREMENT
        cumulative_rotation += rotation_increment
        rotation_y = cumulative_rotation

        # Y轴位置
        y_pos = idx * SPACING

        # 创建实体框
        obj_name = f"Torii_{idx:03d}"
        obj, actual_z = create_rectangular_solid_frame(
            obj_name=obj_name,
            width=width,
            height=height,
            position=(0, y_pos, 0),
            rotation_y=rotation_y,
            z_offset=z_offset
        )

        # 移动到集合
        for col in obj.users_collection:
            col.objects.unlink(obj)
        collection.objects.link(obj)

        # 打印前几个和后几个作为调试
        if idx < 5 or idx >= NUM_INTERPOLATED - 3:
            print(f"  {obj_name}: y={y_pos:.2f}, w={width:.2f}, h={height:.2f}, rot={rotation_y:.1f}°, z={z_offset:.2f}")

    print(f"\n{'='*50}")
    print(f"完成！")
    print(f"生成对象: {NUM_INTERPOLATED} 个密集切片")
    print(f"策略1: Cubic Spline 插值 (14 -> {NUM_INTERPOLATED})")
    print(f"策略2: 非线性放大 (x^3)")
    print(f"策略3: 累积Z轴起伏 + 累积扭转")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()