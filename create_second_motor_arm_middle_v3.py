import FreeCAD as App

import FreeCADGui as Gui
import Part
import math
from scipy.interpolate import interp1d as lerp
from copy import deepcopy

def create_cylinder(height, radius, position):
    """Create a cylinder with specified height, radius, and position."""
    cylinder = App.ActiveDocument.addObject("Part::Cylinder", "Cylinder")
    cylinder.Height = height
    cylinder.Radius = radius
    cylinder.Placement = App.Placement(App.Vector(*position), App.Rotation(App.Vector(0, 0, 1), 0))
    return cylinder

def compound_rotation(rotation_in_degrees_list_of_tuples):
    """Create a compound rotation from a list of rotations in degrees."""
    compound_rotation = App.Rotation(App.Vector(0, 0, 1), 0)
    for rotation in rotation_in_degrees_list_of_tuples:
        compound_rotation = create_rotation(rotation).multiply(compound_rotation)
    return compound_rotation


def create_rotation(rotation_in_degrees_tuple):
    return App.Rotation(*[i for i in rotation_in_degrees_tuple])
    

def cut(base_cylinder, tool_cylinder):
    """Cut the base cylinder with the tool cylinder."""
    cut = App.activeDocument().addObject("Part::Cut", "Cut")
    cut.Base = base_cylinder
    cut.Tool = tool_cylinder
    App.ActiveDocument.recompute()
    return cut



def make_hole(part, hole_diameter, hole_height, hole_position,hole_rotation=(0,0,0),through_hole=False):
    """
    Creates a hole in a given part.

    Parameters:
    part: The target part to make a hole in.
    hole_diameter: Diameter of the hole.
    hole_height: Height of the hole, should be greater than the part height to ensure it goes all the way through.
    hole_position: A tuple (x, y, z) indicating the position of the hole's center.
    """
    doc = App.activeDocument()

    # Create a cylinder to represent the hole
    hole = doc.addObject("Part::Cylinder", "Hole")
    hole.Radius = hole_diameter / 2
    hole.Height = hole_height
    hole.Placement = App.Placement(App.Vector(*hole_position), App.Rotation(App.Vector(0, 0, 1), 0))
    hole.Placement.Rotation = create_rotation(hole_rotation) if type(hole_rotation) is tuple else compound_rotation(hole_rotation)

    # If the hole is a through hole, extend it in the direction of its rotation back

    if through_hole:
        hole.Placement.Base = hole.Placement.Base - hole.Placement.Rotation.multVec(App.Vector(0,0,hole_height/2))

    # Cut the hole from the part
    cut = doc.addObject("Part::Cut", "Cut")
    cut.Base = part
    cut.Tool = hole
    doc.recompute()

    return cut

def join_parts(part1, part2):
    """
    Joins two parts into one using a fusion operation in FreeCAD.

    Parameters:
    part1: The first part to be joined.
    part2: The second part to be joined.
    """
    doc = App.activeDocument()

    # Create a fusion of the two parts
    fused_part = doc.addObject("Part::Fuse", "FusedPart")
    fused_part.Base = part1
    fused_part.Tool = part2
    doc.recompute()

    return fused_part

def create_centered_rectangle(length, width, height,label="Compound"):
    """
    Creates a rectangular box with its origin at the center of the X-Y plane.
    Also creates a compound object to group the rectangle.

    Parameters:
    length: Length of the rectangle (in the X direction).
    width: Width of the rectangle (in the Y direction).
    height: Height of the rectangle (in the Z direction).
    """
    doc = App.activeDocument()

    # Create the rectangle
    rectangle = doc.addObject("Part::Box", "CenteredRectangle")
    rectangle.Length = length
    rectangle.Width = width
    rectangle.Height = height
    rectangle.Placement = App.Placement(App.Vector(-length/2, -width/2, 0), App.Rotation())

    # Create a compound object and add the rectangle to it
    compound = doc.addObject("Part::Compound", label)
    compound.Links = [rectangle]

    doc.recompute()
    return compound

def create_sloped_wall(length, height, width, slope_angle,offset_length = 0,label="Sloped Wall"):
    """
    Create a wall with a slope on one side and return the DocumentObject.

    Parameters:
    doc (FreeCAD.Document): The FreeCAD document to add the wall to.
    length (float): Length of the wall.
    height (float): Height of the wall.
    width (float): Width (thickness) of the wall.
    slope_angle (float): Slope angle in degrees.

    Returns:
    FreeCAD.DocumentObject: The final sloped wall as a DocumentObject.
    """

    # Create the base wall
    base_wall = Part.makeBox(length, width, height)

    # Calculate the slope
    slope_height = height - (length * math.tan(math.radians(slope_angle)))
    
    # Define the points for the sloped face
    points = [App.Vector(0 + offset_length, 0 , height), 
              App.Vector(length + offset_length, 0 , slope_height),
              App.Vector(length + offset_length, 0, height)]

    # Create a face for the sloped side
    sloped_face = Part.makePolygon(points + [points[0]])
    sloped_face = Part.Face(sloped_face)

    # Extrude the sloped face
    sloped_wall = sloped_face.extrude(App.Vector(0, width, 0))

    # Cut the sloped part out of the base wall
    final_wall_shape = base_wall.cut(sloped_wall)

    # Add the shape to the FreeCAD document
    wall_obj = App.ActiveDocument.addObject("Part::Feature", "SlopedWallInternal")
    wall_obj.Shape = final_wall_shape
    wall_obj.Placement = App.Placement(App.Vector(-length/2, -width/2, 0), App.Rotation(App.Vector(0, 0, 1), 0))

    compound = App.ActiveDocument.addObject("Part::Compound", label)
    compound.Links = [wall_obj]

    # Recompute the document
    App.ActiveDocument.recompute()

    return compound


def create_hollow_cylinder(outer_radius, inner_radius, height, position=(0,0,0)):
    
    """Create a cylinder with a hole in the middle."""
    
    doc = App.ActiveDocument
    
    # Ensure the inner radius is smaller than the outer radius
    
    if inner_radius >= outer_radius:
        raise ValueError("Inner radius must be smaller than outer radius")

    # Create the outer cylinder
    outer_cylinder = Part.makeCylinder(outer_radius, height)
    outer_cylinder.translate(App.Vector(position[0], position[1], position[2]))

    # Create the inner cylinder (hole)
    inner_cylinder = Part.makeCylinder(inner_radius, height)
    inner_cylinder.translate(App.Vector(position[0], position[1], position[2]))

    # Subtract the inner cylinder from the outer cylinder
    hollow_cylinder = outer_cylinder.cut(inner_cylinder)

    # Create a FreeCAD object and set its shape
    cylinder_part = doc.addObject("Part::Feature", "HollowCylinder")
    cylinder_part.Shape = hollow_cylinder

    return cylinder_part

def rotate_object_around_center(object_name, axis, angle):
    """
    Rotates an object around its center by a given angle.

    :param object_name: Name of the object to rotate.
    :param axis: Tuple or App.Vector representing the axis of rotation.
    :param angle: Rotation angle in degrees.
    """
    obj = App.ActiveDocument.getObject(object_name)
    if obj is None:
        raise ValueError("Object not found: " + object_name)

    if isinstance(axis, tuple):
        axis = App.Vector(*axis)

    # Get the object's bounding box
    bbox = obj.Shape.BoundBox
    # Calculate the center of the bounding box
    center = bbox.Center

    # Create a rotation around the center
    rotation = App.Rotation(axis, angle)
    new_placement = App.Placement(center, rotation)
    
    # Adjust the position to keep the object centered after rotation
    new_placement.Base = new_placement.multVec(-center)
    
    obj.Placement = new_placement

HOLE_INF = 1000
tolerance = 0.5
m5_size = 2.5 + tolerance*2
m5_head_size = 8.5 + tolerance*2
motor_shaft_hole_radius = 9 + tolerance
bearing_width = 7 + tolerance
bearing_outer_radius = 22/2 + tolerance
bearing_inner_radius = 8/2 + tolerance/2
arm_cylinder_radius = 40
arm_cylinder_height = 35
base_current_height = 150

def main():

    doc = App.ActiveDocument

    # Bearing dimensions

    # Create the main arm cylinder

    arm_cylinder = create_cylinder(arm_cylinder_height, arm_cylinder_radius, (0,0,0))

    # Add 10 extra milimeters of cylinder on top
        
    arm_cylinder_extra_height = 8
    arm_cylinder_extra = create_cylinder(arm_cylinder_extra_height, arm_cylinder_radius, (0,0,-arm_cylinder_extra_height))


    arm_cylinder = join_parts(arm_cylinder, arm_cylinder_extra)

    number_of_slots = 4

    # Add 8 slots for screws on the outside of the arm cylinder
    
    for i in range(number_of_slots):

        angle = (360/number_of_slots * i) + 360/number_of_slots/2

        x = math.cos(math.radians(angle)) * (arm_cylinder_radius - m5_head_size)
        y = math.sin(math.radians(angle)) * (arm_cylinder_radius - m5_head_size)

        hole_height = 35
        
        x = math.cos(math.radians(angle)) * (arm_cylinder_radius - m5_head_size/2)
        y = math.sin(math.radians(angle)) * (arm_cylinder_radius - m5_head_size/2)

        extra_cut = create_centered_rectangle(m5_head_size*2.5, m5_head_size*2.5, hole_height)
        
        extra_cut.Placement = App.Placement(App.Vector(x,y,0), App.Rotation(App.Vector(0,0,1),angle + 45))
    
        
        arm_cylinder = cut(arm_cylinder, extra_cut)

        # now make an m5 cut on the top cylinder

        x = math.cos(math.radians(angle)) * (arm_cylinder_radius - m5_head_size)
        y = math.sin(math.radians(angle)) * (arm_cylinder_radius - m5_head_size)

        arm_cylinder = make_hole(arm_cylinder, m5_size*2, arm_cylinder_extra_height, (x,y,-arm_cylinder_extra_height),hole_rotation=(0,0,0))

    # now copy the arm cylinder and rotate it so that it is on top of the other one
        
    arm_cylinder_2 = App.ActiveDocument.copyObject(arm_cylinder, True)

    rotate_object_around_center(arm_cylinder_2.Name, (1,0,0), 180)

    # move it up

    arm_cylinder_2.Placement.Base = arm_cylinder_2.Placement.Base + App.Vector(0,0,arm_cylinder_height + arm_cylinder_extra_height)

    # now join the two cylinders

    arm_cylinder = join_parts(arm_cylinder, arm_cylinder_2)


    # now cut it in half

    box_cut = create_centered_rectangle(arm_cylinder_radius*2, arm_cylinder_radius*2, HOLE_INF)

    box_cut.Placement = App.Placement(App.Vector(0,arm_cylinder_radius,-HOLE_INF/2), App.Rotation(App.Vector(0,0,1),0))

    arm_cylinder = cut(arm_cylinder, box_cut)

    # rotate 90 degrees

    rotate_object_around_center(arm_cylinder.Name, (1,0,0), -90)

    # move it back to center

    arm_cylinder.Placement.Base = arm_cylinder.Placement.Base + App.Vector(0,arm_cylinder_height/2 + arm_cylinder_extra_height/2 - 1.564,0)

    # now create 4 holes
    number_of_slots = 4

    for i in range(number_of_slots):

        angle = (360/number_of_slots * i) + 360/number_of_slots/2 

        x = math.cos(math.radians(angle)) * (arm_cylinder_radius - m5_head_size)
        y = math.sin(math.radians(angle)) * (arm_cylinder_radius - m5_head_size)

        extra_offset_x = -8

        if i in [0,3]:
            extra_offset_x = -extra_offset_x

        arm_cylinder = make_hole(arm_cylinder, m5_size*2, HOLE_INF, (x + extra_offset_x,y,0),through_hole=True,hole_rotation=(0,0,0))


    # Update the view
    Gui.ActiveDocument.recompute()
    Gui.SendMsgToActiveView("ViewFit")

if App.ActiveDocument is None:
    App.newDocument()

main()
