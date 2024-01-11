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

def create_joint_motor_holder(base_cylinder):
   

    joint_motor_holder = create_sloped_wall(joint_motor_holder_slope_length, joint_motor_holder_height, joint_motor_holder_width_for_base, 70,offset_length=joint_motor_holder_length*2)

    #make a square hole for the motor with the motor height and and width

    joint_motor_holder_cut = create_centered_rectangle(joint_motor_holder_slope_length, joint_motor_holder_width + tolerance, joint_motor_holder_height)

    joint_motor_holder_cut.Placement = App.Placement(App.Vector((joint_motor_holder_length), 0, 0), App.Rotation(App.Vector(0,0,1),0))

    joint_motor_holder = cut(joint_motor_holder, joint_motor_holder_cut)

    joint_motor_holder.Placement = App.Placement(App.Vector(0, 50, first_joint_base_initial_height + base_cylinder_height), App.Rotation(App.Vector(0,0,1),90))

    # now for the cuts for the motor holes

    # Create the motor holes

    motor_hole_radius = 6.21/2 + tolerance/2
    motor_hole_distance_from_center = 49.21

    for i in range(4):
        angle = (360/4 * i) + 360/4/2

        x = math.cos(math.radians(angle)) * motor_hole_distance_from_center
        y = math.sin(math.radians(angle)) * motor_hole_distance_from_center

        joint_motor_holder = make_hole(joint_motor_holder, motor_hole_radius*2, HOLE_INF, (x,0,y + first_joint_base_initial_height + joint_motor_holder_height / 2 + base_cylinder_height),through_hole=True,hole_rotation=[(0,90,0),(90,0,0)])

    # now for the motor shaft hole
        
    shaft_hole_radius = 28
        
    joint_motor_holder = make_hole(joint_motor_holder, shaft_hole_radius*2, HOLE_INF, (0,0,first_joint_base_initial_height + joint_motor_holder_height / 2 + base_cylinder_height),through_hole=True,hole_rotation=[(0,90,0),(90,0,0)])

    # move joint motor holder to the center and add the side bars and hole
    
    joint_motor_holder_current_position = 17.5 + motor_shaft_hole_radius + 20
    joint_motor_holder.Placement = App.Placement(App.Vector(0, -(joint_motor_holder_current_position),0), App.Rotation(App.Vector(0,0,1),0))

    # add the side bars

    side_bar_length = 40
    side_bar_height = 5
    side_bar_width = m5_size*2 + (4 + 4)
    for i in range(2):
        side_bar = create_centered_rectangle(side_bar_width, side_bar_length, side_bar_height)

        # add two holes in each
    
        side_bar_hole_distance_from_center = 15
        for j in range(2):
            side_bar = make_hole(side_bar, m5_size*2, HOLE_INF, (0,(lerp([0,1],[-1,1])(j)) * side_bar_hole_distance_from_center,0),through_hole=True)

            # make holes also in the main cylinder
                
            base_cylinder = make_hole(base_cylinder, m5_size*2, HOLE_INF, ((lerp([0,1],[-1,1])(i)) * (joint_motor_holder_width_for_base/2 + side_bar_width/2) , 0 + (lerp([0,1],[-1,1])(j)) * side_bar_hole_distance_from_center, first_joint_base_initial_height + base_cylinder_height),through_hole=True)
        
        
        
        side_bar.Placement = App.Placement(App.Vector((lerp([0,1],[-1,1])(i)) * (joint_motor_holder_width_for_base/2 + side_bar_width/2) , 0, first_joint_base_initial_height + base_cylinder_height), App.Rotation(App.Vector(0,0,1),0))

        # join the side bar to the joint motor holder

        joint_motor_holder = join_parts(joint_motor_holder, side_bar)

    # Add a rectangle on the left side of the joint motor holder with a rounded top to add the endstop
        

    endstop_rectangle_height = 40
    endstop_rectangle_width = 100
    endstop_rectangle_length = 8

    endstop_rectangle = create_centered_rectangle(endstop_rectangle_length, endstop_rectangle_width, endstop_rectangle_height)

    # position it in front of the joint motor holder

    endstop_start_y = -endstop_rectangle_width/2 - motor_shaft_hole_radius - 12.5

    endstop_rectangle.Placement = App.Placement(App.Vector(-joint_motor_holder_width_for_base/2 + endstop_rectangle_length/2, endstop_start_y, first_joint_base_initial_height + base_cylinder_height), App.Rotation(App.Vector(0,0,1),0))

    # add a rounded by joining a cylinder and a rectangle

    endstop_rounded_radius = endstop_rectangle_length/2

    endstop_rounded = create_cylinder(endstop_rectangle_width, endstop_rounded_radius, (0,0,0))

    endstop_rounded.Placement = App.Placement(App.Vector(-joint_motor_holder_width_for_base/2 + endstop_rectangle_length/2,endstop_start_y - endstop_rectangle_width/2, first_joint_base_initial_height + base_cylinder_height + endstop_rectangle_height), compound_rotation([(0,90,0),(90,0,0)]))

    endstop_rectangle = join_parts(endstop_rectangle, endstop_rounded)

    # now make 4 holes in the endstop rectangle

    endstop_hole_radius = m5_size
    length_until_border = 60.15

    for i in range(2):
        angle = (360/2 * i) + 360/2/2

        x = math.cos(math.radians(angle)) * endstop_rectangle_height/3
        y = math.sin(math.radians(angle)) * length_until_border/6

        endstop_rectangle = make_hole(endstop_rectangle, endstop_hole_radius*2, HOLE_INF, (0,-y - length_until_border/1.2,x + first_joint_base_initial_height + base_cylinder_height + endstop_rectangle_height - spacer_radius ),through_hole=True,hole_rotation=[(0,90,0),(0,0,0)])
    
    
    # add a sloped wall to the endstop rectangle
        
    endstop_slope_angle = 30

    endstop_slope = create_sloped_wall(100, endstop_rectangle_height - spacer_radius*2, endstop_rectangle_width, endstop_slope_angle,offset_length=0,label="Endstop Slope")

    endstop_slope.Placement = App.Placement(App.Vector(-joint_motor_holder_width_for_base/2 - 100/2, endstop_start_y, first_joint_base_initial_height + base_cylinder_height), App.Rotation(App.Vector(0,0,1),180))

    endstop_rectangle = join_parts(endstop_rectangle, endstop_slope)


    # now cut the part after the outer radius

    endstop_rectangle = cut(endstop_rectangle, create_hollow_cylinder(200, base_cylinder_radius, HOLE_INF, position=(0,0,0)))

    # now make a hole for a screw on the outer radius of the base cylinder 

    angle = 215

    x = math.cos(math.radians(angle)) * (base_cylinder_radius - spacer_radius)
    y = math.sin(math.radians(angle)) * (base_cylinder_radius - spacer_radius)

    endstop_rectangle = make_hole(endstop_rectangle, spacer_radius*2, HOLE_INF, (x,y, first_joint_base_initial_height + base_cylinder_height + side_bar_height))
    


    # join the endstop to the joint motor holder

    joint_motor_holder = join_parts(joint_motor_holder, endstop_rectangle)

    # make a hole on the other side of the joint motor holder for the endstop holding screw

    joint_motor_holder = make_hole(joint_motor_holder, m5_size*2, HOLE_INF, (x,y, first_joint_base_initial_height + base_cylinder_height + side_bar_height),through_hole=True)
    
    base_cylinder = make_hole(base_cylinder, m5_size*2, HOLE_INF, (x,y, first_joint_base_initial_height + base_cylinder_height),through_hole=True)
    
    base_cylinder.Label = "Base For First Joint"

    joint_motor_holder.Label = "Motor Holder For First Joint"

    return joint_motor_holder,base_cylinder

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

HOLE_INF = 1000
joint_motor_holder_height = 86
joint_motor_holder_width = 86
joint_motor_holder_width_for_base = joint_motor_holder_width + 8 + 8
joint_motor_holder_length = 8
joint_motor_holder_slope_length = 50
tolerance = 0.5
m5_size = 2.5 + tolerance*2
first_joint_base_initial_height = 50
base_cylinder_radius = 95
spacer_radius = 8 + tolerance
base_cylinder_height = 8
motor_shaft_hole_radius = 7 + tolerance
bearing_width = 7 + tolerance
bearing_outer_radius = 22/2 + tolerance
bearing_inner_radius = 8/2 + tolerance/2

def main():

    doc = App.ActiveDocument

    # Bearing dimensions

    



    extra_height = 10
    radius_range_to_keep = [base_cylinder_radius - 14, base_cylinder_radius - 26]


    
    base_cylinder = create_cylinder(base_cylinder_height + extra_height, base_cylinder_radius, (0,0,first_joint_base_initial_height - extra_height))

    # Create the hollow cylinder to cut the base cylinder to keep the radius

    hollow_cylinder = create_hollow_cylinder(base_cylinder_radius, radius_range_to_keep[0], extra_height, position=(0,0,first_joint_base_initial_height - extra_height))

    # Cut the base cylinder with the hollow cylinder

    base_cylinder = cut(base_cylinder, hollow_cylinder)

    # Create the hollow cylinder to cut the base cylinder to keep the radius

    hollow_cylinder = create_hollow_cylinder(radius_range_to_keep[1], 0, extra_height, position=(0,0,first_joint_base_initial_height - extra_height))

    # Cut the base cylinder with the hollow cylinder

    base_cylinder = cut(base_cylinder, hollow_cylinder)

    # now create some extra depth in the motor shaft

    extra_depth_motor_shaft = 18
    extra_depth_motor_shaft_radius = motor_shaft_hole_radius + 10

    extra_depth_motor_shaft_base_cylinder = create_cylinder(extra_depth_motor_shaft, base_cylinder_radius, (0,0,first_joint_base_initial_height - extra_depth_motor_shaft))

    hollow_cylinder = create_hollow_cylinder(base_cylinder_radius, extra_depth_motor_shaft_radius, extra_depth_motor_shaft, position=(0,0,first_joint_base_initial_height  - extra_depth_motor_shaft))
    
    extra_depth_motor_shaft_base_cylinder = cut(extra_depth_motor_shaft_base_cylinder, hollow_cylinder)

    base_cylinder = join_parts(base_cylinder, extra_depth_motor_shaft_base_cylinder)
    
    base_cylinder = make_hole(base_cylinder, motor_shaft_hole_radius*2, HOLE_INF, (0,0,0),through_hole=True)

    # Now a square hole for the key

    key_hole_width = 5 + tolerance/3

    key_hole = create_centered_rectangle(key_hole_width, key_hole_width, HOLE_INF)


    key_hole.Placement = App.Placement(App.Vector(-motor_shaft_hole_radius - key_hole_width/3, 0, 0), App.Rotation())

    base_cylinder = cut(base_cylinder, key_hole)

    


    # Make the first joint motor holder

    
    joint_motor_holder,base_cylinder = create_joint_motor_holder(base_cylinder)

    



    # Update the view
    Gui.ActiveDocument.recompute()
    Gui.SendMsgToActiveView("ViewFit")

if App.ActiveDocument is None:
    App.newDocument()

main()
