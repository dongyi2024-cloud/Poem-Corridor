import bpy
import math

# 删除默认的立方体
bpy.ops.object.select_all(action='DESELECT')
bpy.data.objects['Cube'].select_set(True)
bpy.ops.object.delete()

# 设置单位系统为毫米
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 0.001  # 1米 = 1000毫米

# 创建一个平面 (100mm x 100mm = 0.1m x 0.1m)
bpy.ops.mesh.primitive_plane_add(size=0.1, location=(0, 0, 0))

# 获取创建的平面对象
plane = bpy.context.active_object
plane.name = "100mm_Rectangle"

# 将平面转换为曲线以便更好地控制
bpy.ops.object.convert(target='CURVE')

# 调整曲线属性
curve = plane.data
curve.bevel_depth = 0.002  # 2mm厚度
curve.bevel_resolution = 2

# 添加材质
mat = bpy.data.materials.new(name="Rectangle_Material")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.8, 0.2, 0.2, 1)  # 红色
bsdf.inputs['Metallic'].default_value = 0.0
bsdf.inputs['Roughness'].default_value = 0.5

plane.data.materials.append(mat)

# 保存文件
bpy.ops.wm.save_as_mainfile(filepath="c:/Users/Administrator/Desktop/算法/rectangle_100mm.blend")

print("Blender文件已创建: rectangle_100mm.blend")
print("矩形尺寸: 100mm x 100mm")