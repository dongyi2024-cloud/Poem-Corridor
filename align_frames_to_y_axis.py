"""
Blender 脚本：将所有 Frame_ 对象的对齐到 Y 轴
运行方式：
1. 打开 Blender
2. 在 Scripting 工作区创建新文本，粘贴此代码
3. 按 Run Script
"""
import bpy

# 要处理的对象名称前缀
PREFIX = "Frame_"

# Y 轴目标位置
TARGET_Y = 0.0  # Y 轴中心线

# 获取所有以 Frame_ 开头的对象
frame_objects = [obj for obj in bpy.data.objects if obj.name.startswith(PREFIX)]

print(f"找到 {len(frame_objects)} 个 Frame 对象")

# 将每个对象的对齐到 Y 轴
for obj in frame_objects:
    # 记录当前 Y 轴位置
    current_y = obj.location.y

    # 将 Y 轴位置设为 0（对齐到 Y 轴中心线）
    # 如果想让它们沿着 Y 轴排列，不要移动 Y，只移动 X 到 0
    obj.location.x = 0.0

    # 打印
    print(f"{obj.name}: Y={current_y:.4f} -> X=0, 保持 Y={obj.location.y:.4f}")

print("完成！现在可以导出 GLTF")