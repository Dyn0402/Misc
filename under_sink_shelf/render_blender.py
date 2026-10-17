"""Render the shelf inside the measured cabinet, from model.json.

    blender -b --factory-startup --python under_sink_shelf/render_blender.py

Writes under_sink_shelf/renders/shelf_*.png. The model is mm; the scene is metres.
Context (walls, counter, basin, estimated pipes) comes from model.json too.
"""

import json
import pathlib

import bpy

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "renders"
S = 0.001  # mm -> m

model = json.loads((HERE / "model.json").read_text())

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    return m


MATS = {
    "shelf": material("Pine", (0.72, 0.50, 0.28), 0.55),
    "post": material("PinePost", (0.72, 0.50, 0.28), 0.55),
    "wall": material("CabinetWhite", (0.90, 0.90, 0.89), 0.8),
    "counter": material("OakCounter", (0.55, 0.36, 0.20), 0.5),
    "steel": material("Steel", (0.62, 0.63, 0.65), 0.25),
    "pipe": material("PipeGrey", (0.25, 0.26, 0.28), 0.5),
    "hose": material("HoseBlack", (0.08, 0.08, 0.08), 0.7),
    "floor": material("Floor", (0.45, 0.45, 0.46), 0.9),
    "bottle": material("RinseBottle", (0.10, 0.22, 0.55), 0.35),
    "roll": material("BinBags", (0.12, 0.12, 0.13), 0.7),
    "salt": material("SaltBox", (0.15, 0.35, 0.75), 0.5),
    "tabs": material("TabletBox", (0.45, 0.10, 0.25), 0.5),
}


def mesh_object(name, verts, faces, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x * S, y * S, z * S) for x, y, z in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


for p in model["parts"]:
    role = p["role"]
    mat = MATS.get(role, MATS["wall"])
    mesh_object(p["label"], p["verts"], p["faces"], mat)

# floor well beyond the cabinet, so the open left pocket has something to sit on
bpy.ops.mesh.primitive_plane_add(size=5.0, location=(-0.15, 0.3, -0.018))
bpy.context.active_object.data.materials.append(MATS["floor"])

bpy.ops.object.light_add(type="SUN", location=(0, 0, 3))
sun = bpy.context.active_object
sun.data.energy = 1.2
sun.rotation_euler = (0.8, 0.2, -0.6)
bpy.ops.object.light_add(type="AREA", location=(-0.6, -0.6, 1.6))
area = bpy.context.active_object
area.data.energy = 60
area.data.size = 1.5
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.92, 0.92, 0.93, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"


def camera(name, loc, target, up="Y"):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = 35
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (loc[0] * S, loc[1] * S, loc[2] * S)
    direction = (target[0] * S - loc[0] * S, target[1] * S - loc[1] * S, target[2] * S - loc[2] * S)
    from mathutils import Vector
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = Vector(direction).to_track_quat("-Z", "Y")
    if up == "flip":  # roll 180 degrees about the view axis (back of the kitchen at the top of a plan view)
        from mathutils import Quaternion
        cam.rotation_quaternion = cam.rotation_quaternion @ Quaternion((0, 0, 1), 3.141592653589793)
    return cam


views = {
    # from the open left side, front-left, above: the flat back and the open reach zone
    "iso": dict(loc=(-1350, -950, 1000), target=(-100, 250, 330), hide=("Oven front (blocks the extra space)", "Far left wall")),
    # same view with the counter and basin removed, to see the shelves and pipes
    "iso_open": dict(loc=(-1350, -950, 1000), target=(-100, 250, 330),
                     hide=("Corner counter top", "Basin bottom", "Basin front", "Basin back",
                           "Basin left", "Basin right", "Oven front (blocks the extra space)", "Far left wall")),
    # straight in from the open front
    "front": dict(loc=(-150, -2300, 450), target=(-150, 300, 330), hide=()),
}

for name, v in views.items():
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            ob.hide_render = ob.name in v["hide"]
    cam = camera(name, v["loc"], v["target"], v.get("up", "Y"))
    scene.camera = cam
    scene.render.filepath = str(OUT / f"shelf_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", scene.render.filepath)
