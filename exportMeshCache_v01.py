bl_info = {
    "name": "Export Mesh Cache (.mdd)",
    "author": "Anyone",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Mesh Cache Export",
    "description": "Export selected mesh objects' vertex animation as .mdd",
    "category": "Import-Export",
}

import bpy
import struct
from bpy.props import StringProperty, EnumProperty, IntProperty
from bpy.types import Operator, Panel, PropertyGroup

# -----------------------------
# Cache Export Core Functions
# -----------------------------

def collect_vertex_animation_data(obj, frame_start, frame_end):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_obj = obj.evaluated_get(depsgraph)

    frames = []
    frame_times = []

    for frame in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(frame)
        depsgraph.update()

        mesh = evaluated_obj.to_mesh()
        vertices = [(v.co.x, v.co.y, v.co.z) for v in mesh.vertices]
        frames.append(vertices)
        frame_times.append(frame / bpy.context.scene.render.fps)

        evaluated_obj.to_mesh_clear()

    return frame_times, frames

def write_mdd(filepath, frame_times, frames):
    num_frames = len(frames)
    num_points = len(frames[0])

    with open(filepath, 'wb') as f:
        f.write(struct.pack('>2i', num_frames, num_points))
        for t in frame_times:
            f.write(struct.pack('>f', t))
        for frame in frames:
            for (x, y, z) in frame:
                f.write(struct.pack('>fff', x, y, z))

# -----------------------------
# UI Properties
# -----------------------------

class MeshCacheExportProperties(PropertyGroup):
    filepath: StringProperty(
        name="File Path",
        description="Path to save the cache file",
        subtype='FILE_PATH'
    )
    file_format: EnumProperty(
        name="Format",
        description="Choose cache file format",
        items=[
            ('MDD', "MDD", "Motion Designer Data (.mdd)"),
        ],
        default='MDD'
    )
    frame_start: IntProperty(
        name="Start Frame",
        description="Start frame of export range",
        default=1,
        min=0
    )
    frame_end: IntProperty(
        name="End Frame",
        description="End frame of export range",
        default=250,
        min=1
    )

# -----------------------------
# Operator
# -----------------------------

class EXPORT_OT_mesh_cache(Operator):
    bl_idname = "export.mesh_cache"
    bl_label = "Export Mesh Cache"
    bl_description = "Export selected mesh objects as vertex cache"

    def execute(self, context):
        props = context.scene.mesh_cache_export
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not selected_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        for obj in selected_objects:
            frame_times, frames = collect_vertex_animation_data(
                obj,
                props.frame_start,
                props.frame_end
            )

            if props.file_format == 'MDD':
                write_mdd(props.filepath, frame_times, frames)

        self.report({'INFO'}, f"Exported mesh cache to {props.filepath}")
        return {'FINISHED'}

# -----------------------------
# UI Panel
# -----------------------------

class VIEW3D_PT_mesh_cache_export(Panel):
    bl_label = "Mesh Cache Export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mesh Cache Export'

    def draw(self, context):
        layout = self.layout
        props = context.scene.mesh_cache_export

        layout.prop(props, "filepath")
        layout.prop(props, "file_format")
        layout.prop(props, "frame_start")
        layout.prop(props, "frame_end")
        layout.operator("export.mesh_cache", icon='EXPORT')

# -----------------------------
# Registration
# -----------------------------

classes = (
    MeshCacheExportProperties,
    EXPORT_OT_mesh_cache,
    VIEW3D_PT_mesh_cache_export,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mesh_cache_export = bpy.props.PointerProperty(type=MeshCacheExportProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mesh_cache_export

if __name__ == "__main__":
    register()

"""
해당 스크립트는 Machine Learning Deformer를 만들었을 때,
deform 정보를 저장해 Mesh cache modifier로 deform 정보를 불러올 수 있도록 하기 위해 작성되었다

python을 이용해 만들어진 deform 정보는 rendering 시 적용이 되지 않는다
때문에 렌더링 시 연동되도록 전처리 단계가 필요한데
이를 Mesh Cache modifier로 구현하고자 한다

shapekey 대신 mesh cache를 쓰는 이유는
shapekey 데이터가 많아지면 blender가 무겁고 불안정해져 위험하기 때문이다


This script was created during the development of the ML Deformer.
Since Python cannot apply deformations during rendering,
deformation data must be saved in advance.

To achieve this,
the script writes deformation data to an .mdd (Motion Deformation Data) file.

Shape Keys are not reliable when dealing with a large number of deformations,
as they may not be saved correctly.
Therefore, a Mesh Cache modifier is used instead to ensure stable playback of the deformation data.
"""
