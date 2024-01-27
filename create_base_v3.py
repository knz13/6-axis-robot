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

def create_extruded_circle_sector(radius, angle, height):
    """
    Create and extrude a sector of a circle in FreeCAD, with lines from the
    outer edge to the center, forming a closed shape.

    Parameters:
    radius: Radius of the circle.
    angle: Angle of the sector in degrees.
    height: Height of the extrusion.
    """
    doc = App.activeDocument()
    if doc is None:
        doc = App.newDocument()

    # Create a circle edge
    circle_edge = Part.makeCircle(radius, App.Vector(0, 0, 0), App.Vector(0, 0, 1), 0, angle)

    # Create lines from the center to the circle edge
    center = App.Vector(0, 0, 0)
    edge_point1 = App.Vector(radius * math.cos(math.radians(0)), radius * math.sin(math.radians(0)), 0)
    edge_point2 = App.Vector(radius * math.cos(math.radians(angle)), radius * math.sin(math.radians(angle)), 0)

    line1 = Part.makeLine(center, edge_point1)
    line2 = Part.makeLine(center, edge_point2)

    # Join the circle edge and lines to form a wire
    sector_wire = Part.Wire([line1, circle_edge, line2])

    # Create a face from the wire
    sector_face = Part.Face(sector_wire)


    # Extrude the face
    extrusion = sector_face.extrude(App.Vector(0, 0, height))

    extrusion.Placement = App.Placement(App.Vector(0, 0, -height/2), App.Rotation(App.Vector(0, 0, 1), 0))

    # Add the extruded shape to the document
    extruded_shape = doc.addObject("Part::Feature", "ExtrudedSector")
    extruded_shape.Shape = extrusion
    

    return extruded_shape

def reset_rotation(obj):

    new_obj = create_centered_rectangle(0.001,0.001,0.001,label="ResetRotation")

    # put it very far away

    new_obj.Placement = App.Placement(App.Vector(100000,100000,100000), App.Rotation(App.Vector(0, 0, 1), 0))

    obj = cut(obj,new_obj)

    return obj

HOLE_INF = 1000

def main():

    doc = App.ActiveDocument

    # Bearing dimensions

    tolerance = 0.5

    bearing_width = 7 + tolerance
    bearing_outer_radius = 22/2 
    bearing_inner_radius = 8/2 + tolerance/2

    m5_size = 2.5 + tolerance*2


    nut_holder_width = 10
    nut_holder_length = 6
    nut_holder_height = 2

    # Create two cylinders
    base_cylinder_radius = 95
    base_cylinder_height = 10
    base_cylinder = create_cylinder(base_cylinder_height, base_cylinder_radius, (0,0,0))




    number_of_holes = 8
    for i in range(number_of_holes):
        angle = (360/number_of_holes * i) + 360/number_of_holes 


        first_hole_distance_from_center = base_cylinder_radius - 10

        x = math.cos(math.radians(angle)) * first_hole_distance_from_center
        y = math.sin(math.radians(angle)) * first_hole_distance_from_center

        base_cylinder = make_hole(base_cylinder, m5_size * 2, HOLE_INF, (x,y,0),through_hole=True, hole_rotation=(0,0,0))

        first_nut_holder = create_centered_rectangle(nut_holder_length, nut_holder_width, nut_holder_height, label="FirstNutHolder")

        first_nut_holder.Placement = App.Placement(App.Vector(x, y, base_cylinder_height - nut_holder_height), App.Rotation(App.Vector(0, 0, 1), angle))

        base_cylinder = cut(base_cylinder, first_nut_holder)

        second_hole_distance_from_center = base_cylinder_radius - 25

        x = math.cos(math.radians(angle)) * second_hole_distance_from_center
        y = math.sin(math.radians(angle)) * second_hole_distance_from_center

        base_cylinder = make_hole(base_cylinder, m5_size * 2, HOLE_INF, (x,y,0),through_hole=True, hole_rotation=(0,0,0))

        second_nut_holder = create_centered_rectangle(nut_holder_length, nut_holder_width, nut_holder_height, label="SecondNutHolder")

        second_nut_holder.Placement = App.Placement(App.Vector(x, y, base_cylinder_height - nut_holder_height), App.Rotation(App.Vector(0, 0, 1), angle))

        base_cylinder = cut(base_cylinder, second_nut_holder)

    return

    # Create the bottom bearings holding squares
        
    number_of_bearings = 8

    inner_barrier_height = 14
    inner_barrier_width = 20
    inner_barrier_length = 10
    outer_barrier_length = 10
    bearings_distance = base_cylinder_radius - (bearing_width + inner_barrier_length + outer_barrier_length)

    for i in range(number_of_bearings):
        angle_deg = (360/number_of_bearings) * i + 360/number_of_bearings/2
        angle_rad = math.radians(angle_deg)

        # Calculate position based on angle
        x = (bearings_distance) * math.cos(angle_rad)
        y = (bearings_distance) * math.sin(angle_rad)

        radius_of_half_circle = inner_barrier_height

        chamfer_cylinder = create_extruded_circle_sector(radius_of_half_circle, 90, inner_barrier_width)

        rotate_object_around_center(chamfer_cylinder.Name, (0,1,0), -90)

        chamfer_cylinder.Placement = App.Placement(App.Vector(inner_barrier_width/2, -2, base_cylinder_height),chamfer_cylinder.Placement.Rotation)

        inner_barrier = reset_rotation(chamfer_cylinder)

        x = (bearings_distance) * math.cos(angle_rad)

        y = (bearings_distance) * math.sin(angle_rad)

        inner_barrier.Placement = App.Placement(App.Vector(x, y, 0), App.Rotation(App.Vector(0, 0, 1), angle_deg + 90))
        

        
        """ # Create a rectangle at the calculated position with appropriate rotation for the inner barrier
        inner_barrier = create_centered_rectangle(inner_barrier_length, inner_barrier_width, inner_barrier_height, label="InnerBarrier")
        inner_barrier.Placement = App.Placement(App.Vector(x, y, base_cylinder_height), App.Rotation(App.Vector(0, 0, 1), angle_deg))
 """
        x = (bearings_distance + inner_barrier_length/2 + bearing_width) * math.cos(angle_rad)

        y = (bearings_distance + inner_barrier_length/2 + bearing_width) * math.sin(angle_rad)


        

        # Create a rectangle at the calculated position with appropriate rotation for the outer barrier
        outer_barrier = create_centered_rectangle(outer_barrier_length, inner_barrier_width, inner_barrier_height, label="OuterBarrier")
        outer_barrier.Placement = App.Placement(App.Vector(x, y, base_cylinder_height), App.Rotation(App.Vector(0, 0, 1), angle_deg))

        # Join the inner and outer barriers
        barriers = join_parts(inner_barrier, outer_barrier)

        # Make a hole in the barriers for the bearing

        x = (bearings_distance - inner_barrier_length/2) * math.cos(angle_rad)

        y = (bearings_distance - inner_barrier_length/2) * math.sin(angle_rad)

        
        barriers = make_hole(barriers, bearing_inner_radius * 2, 30, (x, y, base_cylinder_height + inner_barrier_height*0.5),hole_rotation=[(0,90,0),(angle_deg,0,0)])

        # Add the rectangle to the compound object
        base_cylinder = join_parts(base_cylinder, barriers)

        # Add a rectangular hole with width equal to bearing width and length equal to bearing_outer_diameter to the base cylinder for the bearing

        bearing_width_for_cut = bearing_width + tolerance*2

        bearing_hole = create_centered_rectangle(bearing_width_for_cut, bearing_outer_radius*2, 50, label="BearingHole")
        
        x = (bearings_distance + (inner_barrier_length/2 + bearing_width)/2) * math.cos(angle_rad)
        y = (bearings_distance + (inner_barrier_length/2 + bearing_width)/2) * math.sin(angle_rad)
        
        

        bearing_hole.Placement = App.Placement(App.Vector(x, y, 0), App.Rotation(App.Vector(0, 0, 0), angle_deg))
        
        base_cylinder =  cut(base_cylinder, bearing_hole)   




    # Make the holes for the motor in the center
        
    motor_hole_radius = 6.21/2 + tolerance/2
    motor_hole_distance_from_center = 49.21 

    for i in range(4):
        angle_deg = (360/4) * i
        angle_rad = math.radians(angle_deg)

        # Calculate position based on angle
        x = (motor_hole_distance_from_center) * math.cos(angle_rad)
        y = (motor_hole_distance_from_center) * math.sin(angle_rad)

        base_cylinder = make_hole(base_cylinder, motor_hole_radius * 2, HOLE_INF,(x, y, base_cylinder_height),through_hole=True)
        
        motor_nut_holder = create_centered_rectangle(nut_holder_length, nut_holder_width, nut_holder_height, label="MotorNutHolder")

        motor_nut_holder.Placement = App.Placement(App.Vector(x, y, base_cylinder_height - nut_holder_height), App.Rotation(App.Vector(0, 0, 1), angle_deg))

        base_cylinder = cut(base_cylinder, motor_nut_holder)

    # now the hole for the shaft in the middle
        
    shaft_hole_radius = 28

    base_cylinder = make_hole(base_cylinder, shaft_hole_radius * 2, HOLE_INF,(0, 0, base_cylinder_height),through_hole=True)
    
    base_cylinder.Label = "Base for z axis"

    
if App.ActiveDocument is None:
    App.newDocument()

main()

Gui.ActiveDocument.recompute()
Gui.SendMsgToActiveView("ViewFit")

