import FreeCAD as App
import FreeCADGui as Gui
import Part
import math

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
    

def cut_cylinder(base_cylinder, tool_cylinder):
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
    rectangle.Placement = App.Placement(App.Vector(-width/2, -length/2, 0), App.Rotation())

    # Create a compound object and add the rectangle to it
    compound = doc.addObject("Part::Compound", label)
    compound.Links = [rectangle]

    doc.recompute()
    return compound

HOLE_INF = 1000

def main():

    doc = App.ActiveDocument
    # Create two cylinders
    cut_cylinder_height = 16
    second_cylinder_height = 8
    base_cylinder_final_height = 8
    base_cylinder_height = 8 + cut_cylinder_height + second_cylinder_height
    base_cylinder_radius = 100
    base_cylinder = create_cylinder(base_cylinder_height, base_cylinder_radius, (0,0,0))

    # Create a cylinder to cut the base cylinder

    cut_cylinder_radius = 80
    cut_cylinder_obj = create_cylinder(cut_cylinder_height, cut_cylinder_radius, (0,0,base_cylinder_final_height))

    # Cut the base cylinder with the cut cylinder

    base_cylinder = cut_cylinder(base_cylinder, cut_cylinder_obj)

    # Create the second cylinder

    second_cylinder_radius = 90
    second_cylinder = create_cylinder(second_cylinder_height, second_cylinder_radius, (0,0,base_cylinder_final_height+cut_cylinder_height))
    
    # Cut the base cylinder with the second cylinder

    
    base_cylinder = cut_cylinder(base_cylinder, second_cylinder)
    base_cylinder_height = base_cylinder_final_height

    # Create the bottom bearings holding squares
    bearing_width = 7
    bearing_outer_radius = 22/2
    bearing_inner_radius = 8/2
    number_of_bearings = 8
    inner_barrier_height = 20
    inner_barrier_width = 10
    inner_barrier_length = 10
    outer_barrier_length = 10
    bearings_distance = cut_cylinder_radius - (bearing_width + inner_barrier_length) 
    for i in range(number_of_bearings):
        angle_deg = (360/number_of_bearings) * i
        angle_rad = math.radians(angle_deg)

        # Calculate position based on angle
        x = (bearings_distance) * math.cos(angle_rad)
        y = (bearings_distance) * math.sin(angle_rad)
        
        # Create a rectangle at the calculated position with appropriate rotation for the inner barrier

        rectangle = create_centered_rectangle(inner_barrier_length, inner_barrier_width, inner_barrier_height, f"Rectangle_{i}")

        # Add a hole to the rectangle to fit the bearing inner radius

        rectangle.Placement = App.Placement(App.Vector(x, y, base_cylinder_height), App.Rotation(App.Vector(0, 0, 1), angle_deg))
        
        # Add the rectangle to the compound object

        base_cylinder = join_parts(base_cylinder, rectangle)
        
        # print angle to console

        Gui.SendMsgToActiveView(f"Angle: {angle_deg}")

        base_cylinder = make_hole(base_cylinder, bearing_inner_radius * 2, HOLE_INF, (0, 0, inner_barrier_height*0.5+base_cylinder_height),hole_rotation=[(0,90,0),(angle_deg,0,0)])




        

        



        

    # Update the view
    Gui.ActiveDocument.recompute()
    Gui.SendMsgToActiveView("ViewFit")

if App.ActiveDocument is None:
    App.newDocument()

main()
