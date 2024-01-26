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

def create_centered_triangle(side_length, height, label="Compound"):
    """
    Creates an equilateral triangle with its centroid at the center of the X-Y plane.
    Also creates a compound object to group the triangle.

    Parameters:
    side_length: Length of each side of the equilateral triangle.
    height: Height of the triangle (in the Z direction).
    """
    doc = App.activeDocument()

    # Calculate the vertices of the triangle
    h = math.sqrt(3) / 2 * side_length
    v1 = App.Vector(-side_length / 2, -h / 3, 0)
    v2 = App.Vector(side_length / 2, -h / 3, 0)
    v3 = App.Vector(0, 2 * h / 3, 0)

    # Create the triangle face
    wire = Part.makePolygon([v1, v2, v3, v1])
    face = Part.Face(wire)

    # Extrude the face to create a solid
    triangle = face.extrude(App.Vector(0, 0, height))

    # Create a compound object and add the triangle to it
    compound = doc.addObject("Part::Compound", label)
    compound.Links = [doc.addObject("Part::Feature", "CenteredTriangle")]
    compound.Links[0].Shape = triangle

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