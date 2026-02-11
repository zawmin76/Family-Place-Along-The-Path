# ============================================================================
# Dynamo Script: Curve Division with Family Placement
# Revit 2023+ Python Implementation (Modeless Form Pattern)
#
# Purpose:
#   - Select DetailCurves and ModelCurves from Revit model
#   - Configure division settings (distance, method)
#   - Optional: Reverse direction, apply start/end offsets
#   - Place family instances at division points with proper rotation
# ============================================================================

import sys
import clr
import math

# Import Dynamo geometry
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *

# Import Revit extensions
clr.AddReference("RevitNodes")
import Revit
clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)

# Import Revit API
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
from Autodesk.Revit.DB import Structure

# Import Revit UI
clr.AddReference("RevitAPIUI")
from Autodesk.Revit.UI.Selection import ISelectionFilter
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType

# Import Windows Forms for UI
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
import System.Windows.Forms as WinForms
import System.Drawing as Drawing
from System.Windows.Forms import *
from System.Drawing import *

# Import Revit Services
clr.AddReference('RevitServices')
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

# Get active document and UI document
doc = DocumentManager.Instance.CurrentDBDocument
uidoc = DocumentManager.Instance.CurrentUIApplication.ActiveUIDocument

# Global state
dialog_confirmed = False
form_data = {}

# ============================================================================
# CURVE DIVISION FUNCTIONS
# ============================================================================

# ============================================================================
# DIVISION FUNCTIONS (4 Combinations)
# ============================================================================

def divide_max_total_length(curves, distance_feet, start_offset_feet, end_offset_feet, reverse_direction=False, distance_measurement='arc_length'):
    """
    COMBINATION 1: Maximum spacing + Total Length method
    Uses DesignScript PolyCurve.ByJoinedCurves() for true equal spacing.
    All units are in mm (DesignScript). Returns XYZ points ready for family placement.
    distance_measurement: 'arc_length' or 'chord_length'
    """
    division_points = []

    # ===== Convert Revit curves to DesignScript curves directly =====
    # PolyCurve.ByJoinedCurves() handles curve ordering automatically
    ds_curves = []
    for curve in curves:
        ds_curve = curve.ToProtoType()
        ds_curves.append(ds_curve)

    # Use DesignScript PolyCurve.ByJoinedCurves() to create single curve
    polycurve = PolyCurve.ByJoinedCurves(ds_curves, 0.01)

    # ===== Reverse the PolyCurve if needed =====
    if reverse_direction:
        polycurve = polycurve.Reverse()

    # ===== Trim the PolyCurve using ExtendStart/ExtendEnd =====
    # Offsets are already in mm (from UI input)
    # Negative values trim the curve ends
    trimmed_polycurve = polycurve.ExtendStart(-start_offset_feet).ExtendEnd(-end_offset_feet)

    # Get usable length from trimmed curve (in mm)
    total_length = trimmed_polycurve.Length

    # Calculate optimal number of divisions using smart spacing algorithm
    # distance_feet is already in mm (from UI input)
    num_divs_ideal = total_length / distance_feet
    num_divs_floor = int(math.floor(num_divs_ideal))
    num_divs_ceil = int(math.ceil(num_divs_ideal))

    spacing_floor = total_length / num_divs_floor if num_divs_floor > 0 else total_length
    spacing_ceil = total_length / num_divs_ceil if num_divs_ceil > 0 else total_length

    if spacing_floor <= distance_feet:
        num_divisions = num_divs_floor
    else:
        num_divisions = num_divs_ceil

    # ===== Divide using equal spacing (arc or chord length) =====
    if distance_measurement == 'chord_length':
        # Use PointsAtEqualChordLength for equal chord distance spacing
        points_list = trimmed_polycurve.PointsAtEqualChordLength(num_divisions)
        for ds_point in points_list:
            xyz_point = ds_point.ToXyz()
            # Get parameter for tangent calculation
            param = trimmed_polycurve.ParameterAtPoint(ds_point)
            division_points.append({
                'point': xyz_point,
                'param': param,
                'polycurve': trimmed_polycurve
            })
    else:
        # Default: Use PointsAtEqualSegmentLength for equal arc length spacing
        points_list = trimmed_polycurve.PointsAtEqualSegmentLength(num_divisions)
        for ds_point in points_list:
            xyz_point = ds_point.ToXyz()
            # Get parameter for tangent calculation
            param = trimmed_polycurve.ParameterAtPoint(ds_point)
            division_points.append({
                'point': xyz_point,
                'param': param,
                'polycurve': trimmed_polycurve
            })

    return division_points


def divide_fixed_total_length(curves, distance_feet, start_offset_feet, end_offset_feet, reverse_direction=False, divide_position='start', distance_measurement='arc_length'):
    """
    COMBINATION 2: Fixed distance + Total Length method
    divide_position: 'start' or 'middle'
    - start: Place first point at curve start, intervals, remainder at end
    - middle: Balance remainder equally on start and end
    distance_measurement: 'arc_length' or 'chord_length'
    Uses DesignScript PolyCurve.ByJoinedCurves() for exact intervals.
    All units are in mm (DesignScript). Returns XYZ points ready for family placement.
    """
    division_points = []

    # ===== Convert Revit curves to DesignScript curves directly =====
    ds_curves = []
    for curve in curves:
        ds_curve = curve.ToProtoType()
        ds_curves.append(ds_curve)

    # Use DesignScript PolyCurve.ByJoinedCurves() to create single curve
    polycurve = PolyCurve.ByJoinedCurves(ds_curves, 0.01)

    # ===== Reverse the PolyCurve if needed =====
    if reverse_direction:
        polycurve = polycurve.Reverse()

    # ===== Trim the PolyCurve using ExtendStart/ExtendEnd =====
    # Offsets are already in mm (from UI input)
    # Negative values trim the curve ends
    trimmed_polycurve = polycurve.ExtendStart(-start_offset_feet).ExtendEnd(-end_offset_feet)

    # Get usable length from trimmed curve (in mm)
    total_length = trimmed_polycurve.Length

    # ===== Divide using FIXED DISTANCE intervals on TRIMMED PolyCurve =====
    distances = []

    if divide_position == 'middle':
        # MIDDLE: Balanced division algorithm
        max_full = int(total_length // distance_feet)
        best_n_full = 0
        best_end = 0.0

        # Find best balance: largest ends that are still ≤ target distance
        for n in range(max_full, -1, -1):
            middle = n * distance_feet
            remainder = total_length - middle
            end = remainder / 2.0

            if end <= distance_feet + 0.001:
                if end > best_end:
                    best_end = end
                    best_n_full = n

        # Create distances array
        if best_n_full > 0:
            start_offset = (total_length - best_n_full * distance_feet) / 2.0
            distances = [0] + [start_offset + i * distance_feet for i in range(best_n_full + 1)]
            distances = [d for d in distances if d < total_length - 0.001]
    else:
        # START: Simple fixed distance intervals from start
        distances = [i * distance_feet for i in range(int(total_length / distance_feet) + 1)]
        distances = [d for d in distances if d < total_length - 0.001]

    # Always add endpoint
    if not distances or distances[-1] < total_length - 1e-6:
        distances.append(total_length)

    # Place points at calculated distances using appropriate method
    if distance_measurement == 'chord_length':
        # Use PointsAtChordLengthFromPoint for chord-based distance (handles iteration internally)
        start_point = trimmed_polycurve.StartPoint
        points_list = trimmed_polycurve.PointsAtChordLengthFromPoint(start_point, distance_feet)
        for ds_point in points_list:
            if ds_point is not None:
                xyz_point = ds_point.ToXyz()
                param = trimmed_polycurve.ParameterAtPoint(ds_point)
                division_points.append({
                    'point': xyz_point,
                    'param': param,
                    'polycurve': trimmed_polycurve
                })
    else:
        # Default: Use PointAtSegmentLength for arc-based distance
        for distance in distances:
            ds_point = trimmed_polycurve.PointAtSegmentLength(distance)

            if ds_point is not None:
                xyz_point = ds_point.ToXyz()
                param = trimmed_polycurve.ParameterAtPoint(ds_point)
                division_points.append({
                    'point': xyz_point,
                    'param': param,
                    'polycurve': trimmed_polycurve
                })

    return division_points


def divide_max_each_segment(curves, distance_feet, start_offset_feet, end_offset_feet, reverse_direction=False, distance_measurement='arc_length'):
    """
    COMBINATION 3: Maximum spacing + Each Segment method
    Each curve gets optimal equal spacing independently.
    Uses DesignScript PolyCurve for consistent curve direction.
    distance_measurement: 'arc_length' or 'chord_length'
    """
    division_points = []

    # ===== Convert Revit curves to DesignScript curves =====
    ds_curves = []
    for curve in curves:
        ds_curve = curve.ToProtoType()
        ds_curves.append(ds_curve)

    # Use DesignScript PolyCurve.ByJoinedCurves() to ensure proper ordering
    polycurve = PolyCurve.ByJoinedCurves(ds_curves, 0.01)

    # ===== Reverse the PolyCurve if needed =====
    if reverse_direction:
        polycurve = polycurve.Reverse()

    # ===== Explode the PolyCurve to get individual curves with correct direction =====
    exploded_curves = polycurve.Curves()

    # ===== Loop through each exploded curve =====
    for exploded_curve in exploded_curves:
        # Trim the curve using ExtendStart/ExtendEnd
        trimmed_curve = exploded_curve.ExtendStart(-start_offset_feet).ExtendEnd(-end_offset_feet)

        # Get usable length from trimmed curve (in mm)
        curve_length = trimmed_curve.Length

        # Skip if curve is too short
        if curve_length <= 0:
            continue

        # Calculate optimal spacing for this curve
        num_divs_ideal = curve_length / distance_feet
        num_divs_floor = int(math.floor(num_divs_ideal))
        num_divs_ceil = int(math.ceil(num_divs_ideal))

        spacing_floor = curve_length / num_divs_floor if num_divs_floor > 0 else curve_length
        spacing_ceil = curve_length / num_divs_ceil if num_divs_ceil > 0 else curve_length

        if spacing_floor <= distance_feet:
            num_divisions = num_divs_floor
        else:
            num_divisions = num_divs_ceil

        # ===== Divide using equal spacing (arc or chord length) =====
        if distance_measurement == 'chord_length':
            # Use PointsAtEqualChordLength for equal chord distance spacing
            points_list = trimmed_curve.PointsAtEqualChordLength(num_divisions)
            for ds_point in points_list:
                xyz_point = ds_point.ToXyz()
                # Get parameter for tangent calculation
                param = trimmed_curve.ParameterAtPoint(ds_point)
                division_points.append({
                    'point': xyz_point,
                    'param': param,
                    'polycurve': trimmed_curve
                })
        else:
            # Default: Use PointsAtEqualSegmentLength for equal arc length spacing
            points_list = trimmed_curve.PointsAtEqualSegmentLength(num_divisions)
            for ds_point in points_list:
                xyz_point = ds_point.ToXyz()
                # Get parameter for tangent calculation
                param = trimmed_curve.ParameterAtPoint(ds_point)
                division_points.append({
                    'point': xyz_point,
                    'param': param,
                    'polycurve': trimmed_curve
                })

    return division_points


def divide_fixed_each_segment(curves, distance_feet, start_offset_feet, end_offset_feet, reverse_direction=False, divide_position='start', distance_measurement='arc_length'):
    """
    COMBINATION 4: Fixed distance + Each Segment method
    divide_position: 'start' or 'middle'
    - start: Place first point at curve start, intervals, remainder at end
    - middle: Balance remainder equally on start and end
    distance_measurement: 'arc_length' or 'chord_length'
    Uses DesignScript PolyCurve for consistent curve direction.
    """
    division_points = []

    # ===== Convert Revit curves to DesignScript curves =====
    ds_curves = []
    for curve in curves:
        ds_curve = curve.ToProtoType()
        ds_curves.append(ds_curve)

    # Use DesignScript PolyCurve.ByJoinedCurves() to ensure proper ordering
    polycurve = PolyCurve.ByJoinedCurves(ds_curves, 0.01)

    # ===== Reverse the PolyCurve if needed =====
    if reverse_direction:
        polycurve = polycurve.Reverse()

    # ===== Explode the PolyCurve to get individual curves with correct direction =====
    exploded_curves = polycurve.Curves()

    # ===== Loop through each exploded curve =====
    for curve_index, exploded_curve in enumerate(exploded_curves):
        # Trim the curve using ExtendStart/ExtendEnd
        trimmed_curve = exploded_curve.ExtendStart(-start_offset_feet).ExtendEnd(-end_offset_feet)
        curve_length = trimmed_curve.Length

        # Skip if curve is too short
        if curve_length <= 0:
            continue

        # ===== MIDDLE: Balanced division algorithm =====
        if divide_position == 'middle':
            max_full = int(curve_length // distance_feet)
            best_n_full = 0
            best_end = 0.0

            # Find best balance
            for n in range(max_full, -1, -1):
                middle = n * distance_feet
                remainder = curve_length - middle
                end = remainder / 2.0
                if end <= distance_feet + 0.001:
                    if end > best_end:
                        best_end = end
                        best_n_full = n

            if best_n_full > 0:
                start_offset = (curve_length - best_n_full * distance_feet) / 2.0
                # Include point at 0, then best_n_full + 1 points for the segments, then endpoint
                distances = [0] + [start_offset + i * distance_feet for i in range(best_n_full + 1)]
                distances = [d for d in distances if d < curve_length - 0.001]

                if distance_measurement == 'chord_length':
                    # Use PointsAtChordLengthFromPoint for chord-based distance
                    start_point = trimmed_curve.StartPoint
                    points_list = trimmed_curve.PointsAtChordLengthFromPoint(start_point, distance_feet)
                    for ds_point in points_list:
                        if ds_point is not None:
                            param = trimmed_curve.ParameterAtPoint(ds_point)
                            division_points.append({
                                'point': ds_point.ToXyz(),
                                'param': param,
                                'polycurve': trimmed_curve
                            })
                else:
                    for distance in distances:
                        ds_point = trimmed_curve.PointAtSegmentLength(distance)
                        if ds_point is not None:
                            param = trimmed_curve.ParameterAtPoint(ds_point)
                            division_points.append({
                                'point': ds_point.ToXyz(),
                                'param': param,
                                'polycurve': trimmed_curve
                            })

                # Add endpoint for arc length (for chord, it's already included)
                if distance_measurement != 'chord_length':
                    ds_point = trimmed_curve.PointAtSegmentLength(curve_length)
                    if ds_point is not None:
                        division_points.append({
                            'point': ds_point.ToXyz(),
                            'param': 1.0,
                            'polycurve': trimmed_curve
                        })
            else:
                # Curve too short, add endpoint only
                ds_point = trimmed_curve.PointAtSegmentLength(curve_length) if distance_measurement != 'chord_length' else trimmed_curve.PointAtChordLength(0, 1.0, True)
                if ds_point is not None:
                    division_points.append({
                        'point': ds_point.ToXyz(),
                        'param': 1.0,
                        'polycurve': trimmed_curve
                    })

        else:
            # START: Fixed distance intervals
            if distance_measurement == 'chord_length':
                # Use PointsAtChordLengthFromPoint for chord-based distance
                start_point = trimmed_curve.StartPoint
                points_list = trimmed_curve.PointsAtChordLengthFromPoint(start_point, distance_feet)
                for ds_point in points_list:
                    if ds_point is not None:
                        param = trimmed_curve.ParameterAtPoint(ds_point)
                        division_points.append({
                            'point': ds_point.ToXyz(),
                            'param': param,
                            'polycurve': trimmed_curve
                        })
            else:
                distances = [i * distance_feet for i in range(int(curve_length / distance_feet) + 1)]

                # Remove points beyond curve length
                distances = [d for d in distances if d < curve_length - 0.001]

                # Always add endpoint
                if not distances or distances[-1] < curve_length - 1e-6:
                    distances.append(curve_length)

                for distance in distances:
                    ds_point = trimmed_curve.PointAtSegmentLength(distance)
                    if ds_point is not None:
                        param = trimmed_curve.ParameterAtPoint(ds_point)
                        division_points.append({
                            'point': ds_point.ToXyz(),
                            'param': param,
                            'polycurve': trimmed_curve
                        })

    return division_points

# ============================================================================
# FAMILY MANAGEMENT
# ============================================================================

def get_available_families():
    """Get all available families with their symbols from all categories"""
    families = []

    try:
        # Get all FamilySymbol objects (loadable family types)
        collector = FilteredElementCollector(doc).OfClass(FamilySymbol).WhereElementIsElementType()
        all_symbols = list(collector.ToElements())

        for symbol in all_symbols:
            try:
                family = symbol.Family
                if symbol is None or family is None:
                    continue

                family_name = family.Name if family.Name else "(Unnamed)"

                if not family_name:
                    continue

                # Get symbol name using ToDSType approach
                try:
                    symbol_name = symbol.ToDSType(True).Name
                except:
                    try:
                        symbol_name = symbol.Name
                    except:
                        symbol_name = "(Unnamed Symbol)"

                display_name = "{0}:{1}".format(family_name, symbol_name)

                families.append({
                    'family': family,
                    'symbol': symbol,
                    'display_name': display_name,
                    'family_name': family_name,
                    'symbol_name': symbol_name
                })
            except:
                pass

    except:
        pass

    # If no families found from Approach 1, try Approach 2
    if len(families) == 0:
        try:
            collector2 = FilteredElementCollector(doc).OfClass(Family)
            all_families = list(collector2.ToElements())

            for family in all_families:
                try:
                    symbol_ids = family.GetFamilySymbolIds()
                    family_name = family.Name if family.Name else "(Unnamed)"

                    if symbol_ids and symbol_ids.Count > 0:
                        for sym_index, symbol_id in enumerate(symbol_ids):
                            try:
                                symbol = doc.GetElement(symbol_id)
                                if symbol:
                                    try:
                                        symbol_name = symbol.ToDSType(True).Name
                                    except:
                                        try:
                                            symbol_name = symbol.Name
                                        except:
                                            symbol_name = "Type {0}".format(sym_index + 1)

                                    display_name = "{0}:{1}".format(family_name, symbol_name)
                                    families.append({
                                        'family': family,
                                        'symbol': symbol,
                                        'display_name': display_name,
                                        'family_name': family_name,
                                        'symbol_name': symbol_name
                                    })
                            except:
                                pass
                except:
                    pass
        except:
            pass

    return families

def place_family_with_rotation_polycurve(family_symbol, placement_point, polycurve, parameter, rotation_angle):
    """
    Place family instance using DesignScript PolyCurve for Total Length method.
    Gets tangent from PolyCurve.TangentAtParameter() instead of Revit curve derivatives.
    NOTE: Family symbol should be activated BEFORE calling this function (outside transaction)
    """
    # Family activation is now handled outside the transaction to avoid nested transaction conflicts

    # Get tangent vector from DesignScript PolyCurve
    try:
        tangent = polycurve.TangentAtParameter(parameter)
        # tangent is a DesignScript Vector
    except:
        # Fallback to X-axis if tangent calculation fails
        tangent = None

    if tangent is not None:
        # Get angle from tangent vector
        tangent_angle_rad = math.atan2(tangent.Y, tangent.X)
        tangent_angle_deg = math.degrees(tangent_angle_rad)
    else:
        tangent_angle_deg = 0.0

    # Add user rotation
    total_rotation_deg = tangent_angle_deg + rotation_angle

    # Place family at point using Revit API
    try:
        if Structure is not None:
            family_instance = doc.Create.NewFamilyInstance(
                placement_point,
                family_symbol,
                Structure.StructuralType.NonStructural
            )
        else:
            family_instance = doc.Create.NewFamilyInstance(
                placement_point,
                family_symbol,
                StructuralType.NonStructural
            )
    except:
        family_instance = doc.Create.NewFamilyInstance(
            placement_point,
            family_symbol
        )

    # Apply rotation based on tangent direction
    if family_instance is not None:
        try:
            up_direction = XYZ.BasisZ
            axis_of_rotation = Line.CreateUnbound(placement_point, up_direction)
            total_rotation_rad = math.radians(total_rotation_deg)
            ElementTransformUtils.RotateElement(doc, family_instance.Id, axis_of_rotation, total_rotation_rad)
        except:
            pass

    return family_instance

# ============================================================================
# TRANSACTION SAFETY (For Revit 2021 compatibility)
# ============================================================================

def close_open_transactions():
    """
    Check for and close any open transactions before starting new one.
    Prevents "Starting a new transaction is not permitted" error in Revit 2021.
    """
    try:
        # Get all open transactions and close them
        opened_txns = list(TransactionManager.Instance.CurrentDBDocument.Transactions)
        for txn in opened_txns:
            try:
                if txn.GetStatus() == TransactionStatus.Started:
                    txn.RollBack()
            except:
                pass
    except:
        # If we can't access transaction list, continue anyway
        pass

# ============================================================================
# WINDOWS FORMS UI (Modeless Pattern)
# ============================================================================

class CurveDivisionDialog(WinForms.Form):
    """Main dialog for curve division and family placement"""

    def __init__(self):
        self.selected_curves = []
        self.families_list = []
        self.InitializeComponent()

    def InitializeComponent(self):
        """Initialize form controls with Windows 11 defaults"""
        self.Text = "Curve Division with Family Placement"

        # Standard Windows 11 form size (wider for label text)
        self.Width = 680
        self.Height = 930
        self.StartPosition = WinForms.FormStartPosition.CenterScreen
        self.FormBorderStyle = WinForms.FormBorderStyle.FixedDialog
        self.MaximizeBox = False
        self.MinimizeBox = False
        self.TopMost = True

        # Standard Windows 11 fonts (9pt is default for forms)
        self.font_label = Drawing.Font("Segoe UI", 9)
        self.font_button = Drawing.Font("Segoe UI", 9)
        self.font_groupbox = Drawing.Font("Segoe UI", 9)
        self.font_radio = Drawing.Font("Segoe UI", 9)

        # Starting Y position (standard Windows 11 padding: 12px)
        y = 12

        # ---- SELECT PATH BUTTON ----
        self.btn_select = WinForms.Button()
        self.btn_select.Text = "Select Path"
        self.btn_select.Location = Drawing.Point(12, y)
        self.btn_select.Size = Drawing.Size(626, 32)
        self.btn_select.Font = self.font_button
        self.btn_select.Click += self.select_curves
        self.Controls.Add(self.btn_select)
        y += 50

        # ---- STATUS LABEL ----
        self.lbl_select_status = WinForms.Label()
        self.lbl_select_status.Text = "No curves selected"
        self.lbl_select_status.Location = Drawing.Point(12, y)
        self.lbl_select_status.Size = Drawing.Size(626, 25)
        self.lbl_select_status.Font = self.font_label
        self.lbl_select_status.ForeColor = Drawing.Color.Gray
        self.Controls.Add(self.lbl_select_status)
        y += 50

        # ---- DIVIDE DISTANCE ----
        lbl_distance = WinForms.Label()
        lbl_distance.Text = "Divide Distance (mm):"
        lbl_distance.Location = Drawing.Point(12, y)
        lbl_distance.Size = Drawing.Size(190, 25)
        lbl_distance.Font = self.font_label
        self.Controls.Add(lbl_distance)

        self.txt_distance = WinForms.TextBox()
        self.txt_distance.Location = Drawing.Point(200, y)
        self.txt_distance.Size = Drawing.Size(438, 24)
        self.txt_distance.Font = self.font_label
        self.txt_distance.Text = "1000"
        self.Controls.Add(self.txt_distance)

        y += 60

        # ---- DIVIDE METHOD GroupBox (Maximum vs Fixed Distance) ----
        gb_divide_method = WinForms.GroupBox()
        gb_divide_method.Text = "Divide Method"
        gb_divide_method.Location = Drawing.Point(12, y)
        gb_divide_method.Size = Drawing.Size(626, 75)
        gb_divide_method.Font = self.font_groupbox
        self.Controls.Add(gb_divide_method)

        self.radio_maximum = WinForms.RadioButton()
        self.radio_maximum.Text = "Maximum"
        self.radio_maximum.Location = Drawing.Point(20, 35)
        self.radio_maximum.Size = Drawing.Size(140, 26)
        self.radio_maximum.Font = self.font_radio
        self.radio_maximum.Checked = True
        gb_divide_method.Controls.Add(self.radio_maximum)

        self.radio_fixed_distance = WinForms.RadioButton()
        self.radio_fixed_distance.Text = "Fixed Distance"
        self.radio_fixed_distance.Location = Drawing.Point(340, 35)
        self.radio_fixed_distance.Size = Drawing.Size(160, 26)
        self.radio_fixed_distance.Font = self.font_radio
        self.radio_fixed_distance.CheckedChanged += self.update_divide_options_visibility
        gb_divide_method.Controls.Add(self.radio_fixed_distance)
        y += 100

        # ---- DISTANCE MEASUREMENT GroupBox (Arc Length vs Chord Length) - ALWAYS VISIBLE ----
        gb_distance_measurement = WinForms.GroupBox()
        gb_distance_measurement.Text = "Distance Measurement"
        gb_distance_measurement.Location = Drawing.Point(12, y)
        gb_distance_measurement.Size = Drawing.Size(626, 75)
        gb_distance_measurement.Font = self.font_groupbox
        self.Controls.Add(gb_distance_measurement)

        self.radio_arc_length = WinForms.RadioButton()
        self.radio_arc_length.Text = "Arc Length"
        self.radio_arc_length.Location = Drawing.Point(20, 35)
        self.radio_arc_length.Size = Drawing.Size(160, 26)
        self.radio_arc_length.Font = self.font_radio
        self.radio_arc_length.Checked = True
        gb_distance_measurement.Controls.Add(self.radio_arc_length)

        self.radio_chord_length = WinForms.RadioButton()
        self.radio_chord_length.Text = "Chord Length"
        self.radio_chord_length.Location = Drawing.Point(340, 35)
        self.radio_chord_length.Size = Drawing.Size(160, 26)
        self.radio_chord_length.Font = self.font_radio
        gb_distance_measurement.Controls.Add(self.radio_chord_length)
        y += 100

        # ---- PATH SCOPE GroupBox (Total Path vs Each Element) ----
        gb_path_scope = WinForms.GroupBox()
        gb_path_scope.Text = "Path Scope"
        gb_path_scope.Location = Drawing.Point(12, y)
        gb_path_scope.Size = Drawing.Size(626, 75)
        gb_path_scope.Font = self.font_groupbox
        self.Controls.Add(gb_path_scope)

        self.radio_total_length = WinForms.RadioButton()
        self.radio_total_length.Text = "Total Path"
        self.radio_total_length.Location = Drawing.Point(20, 35)
        self.radio_total_length.Size = Drawing.Size(160, 26)
        self.radio_total_length.Font = self.font_radio
        self.radio_total_length.Checked = True
        self.radio_total_length.CheckedChanged += self.update_divide_options_visibility
        gb_path_scope.Controls.Add(self.radio_total_length)

        self.radio_each_segment = WinForms.RadioButton()
        self.radio_each_segment.Text = "Each Element"
        self.radio_each_segment.Location = Drawing.Point(340, 35)
        self.radio_each_segment.Size = Drawing.Size(160, 26)
        self.radio_each_segment.Font = self.font_radio
        self.radio_each_segment.CheckedChanged += self.update_divide_options_visibility
        gb_path_scope.Controls.Add(self.radio_each_segment)
        y += 100

        # ---- REVERSE DIRECTION ----
        self.reverse_direction_y = y  # Store Y position for Divide Options insertion
        self.lbl_reverse = WinForms.Label()
        self.lbl_reverse.Text = "Reverse Direction:"
        self.lbl_reverse.Location = Drawing.Point(12, y)
        self.lbl_reverse.Size = Drawing.Size(190, 25)
        self.lbl_reverse.Font = self.font_label
        self.Controls.Add(self.lbl_reverse)

        self.radio_reverse_true = WinForms.RadioButton()
        self.radio_reverse_true.Text = "True"
        self.radio_reverse_true.Location = Drawing.Point(210, y)
        self.radio_reverse_true.Size = Drawing.Size(100, 24)
        self.radio_reverse_true.Font = self.font_radio
        self.Controls.Add(self.radio_reverse_true)

        self.radio_reverse_false = WinForms.RadioButton()
        self.radio_reverse_false.Text = "False"
        self.radio_reverse_false.Location = Drawing.Point(350, y)
        self.radio_reverse_false.Size = Drawing.Size(100, 24)
        self.radio_reverse_false.Font = self.font_radio
        self.radio_reverse_false.Checked = True
        self.Controls.Add(self.radio_reverse_false)
        y += 50

        # ---- START OFFSET ----
        self.lbl_start_offset = WinForms.Label()
        self.lbl_start_offset.Text = "Start Offset (mm):"
        self.lbl_start_offset.Location = Drawing.Point(12, y)
        self.lbl_start_offset.Size = Drawing.Size(190, 25)
        self.lbl_start_offset.Font = self.font_label
        self.Controls.Add(self.lbl_start_offset)

        self.txt_start_offset = WinForms.TextBox()
        self.txt_start_offset.Location = Drawing.Point(200, y)
        self.txt_start_offset.Size = Drawing.Size(438, 24)
        self.txt_start_offset.Font = self.font_label
        self.txt_start_offset.Text = "0.0"
        self.Controls.Add(self.txt_start_offset)
        y += 50

        # ---- END OFFSET ----
        self.lbl_end_offset = WinForms.Label()
        self.lbl_end_offset.Text = "End Offset (mm):"
        self.lbl_end_offset.Location = Drawing.Point(12, y)
        self.lbl_end_offset.Size = Drawing.Size(190, 25)
        self.lbl_end_offset.Font = self.font_label
        self.Controls.Add(self.lbl_end_offset)

        self.txt_end_offset = WinForms.TextBox()
        self.txt_end_offset.Location = Drawing.Point(200, y)
        self.txt_end_offset.Size = Drawing.Size(438, 24)
        self.txt_end_offset.Font = self.font_label
        self.txt_end_offset.Text = "0.0"
        self.Controls.Add(self.txt_end_offset)
        y += 50

        # ---- FAMILY TYPE ----
        self.lbl_family = WinForms.Label()
        self.lbl_family.Text = "Family Type:"
        self.lbl_family.Location = Drawing.Point(12, y)
        self.lbl_family.Size = Drawing.Size(180, 25)
        self.lbl_family.Font = self.font_label
        self.Controls.Add(self.lbl_family)

        self.cmb_family = WinForms.ComboBox()
        self.cmb_family.Location = Drawing.Point(200, y)
        self.cmb_family.Size = Drawing.Size(438, 24)
        self.cmb_family.Font = self.font_label
        self.cmb_family.DropDownStyle = WinForms.ComboBoxStyle.DropDown
        # Enable autocomplete search
        self.cmb_family.AutoCompleteMode = WinForms.AutoCompleteMode.SuggestAppend
        self.cmb_family.AutoCompleteSource = WinForms.AutoCompleteSource.ListItems

        self.families_list = get_available_families()
        # Sort by family name alphabetically
        self.families_list.sort(key=lambda x: x['family_name'])
        for fam in self.families_list:
            self.cmb_family.Items.Add(fam['display_name'])

        if self.cmb_family.Items.Count > 0:
            self.cmb_family.SelectedIndex = 0

        self.Controls.Add(self.cmb_family)

        # Status label for families
        self.lbl_family_status = WinForms.Label()
        self.lbl_family_status.Text = "Found {0} families".format(len(self.families_list))
        self.lbl_family_status.Location = Drawing.Point(200, y + 50)
        self.lbl_family_status.Size = Drawing.Size(438, 25)
        self.lbl_family_status.Font = Drawing.Font("Segoe UI", 8)
        self.lbl_family_status.ForeColor = Drawing.Color.Gray if len(self.families_list) > 0 else Drawing.Color.Red
        self.Controls.Add(self.lbl_family_status)
        y += 100

        # ---- ROTATION GroupBox ----
        gb_rotation = WinForms.GroupBox()
        gb_rotation.Text = "Rotation"
        gb_rotation.Location = Drawing.Point(12, y)
        gb_rotation.Size = Drawing.Size(626, 75)
        gb_rotation.Font = self.font_groupbox
        self.Controls.Add(gb_rotation)

        self.radio_rot_0 = WinForms.RadioButton()
        self.radio_rot_0.Text = "0°"
        self.radio_rot_0.Location = Drawing.Point(20, 35)
        self.radio_rot_0.Size = Drawing.Size(80, 26)
        self.radio_rot_0.Font = self.font_radio
        self.radio_rot_0.Checked = True
        gb_rotation.Controls.Add(self.radio_rot_0)

        self.radio_rot_90 = WinForms.RadioButton()
        self.radio_rot_90.Text = "90°"
        self.radio_rot_90.Location = Drawing.Point(160, 35)
        self.radio_rot_90.Size = Drawing.Size(80, 26)
        self.radio_rot_90.Font = self.font_radio
        gb_rotation.Controls.Add(self.radio_rot_90)

        self.radio_rot_180 = WinForms.RadioButton()
        self.radio_rot_180.Text = "180°"
        self.radio_rot_180.Location = Drawing.Point(300, 35)
        self.radio_rot_180.Size = Drawing.Size(80, 26)
        self.radio_rot_180.Font = self.font_radio
        gb_rotation.Controls.Add(self.radio_rot_180)

        self.radio_rot_270 = WinForms.RadioButton()
        self.radio_rot_270.Text = "270°"
        self.radio_rot_270.Location = Drawing.Point(440, 35)
        self.radio_rot_270.Size = Drawing.Size(80, 26)
        self.radio_rot_270.Font = self.font_radio
        gb_rotation.Controls.Add(self.radio_rot_270)
        y += 100

        # ---- BUTTONS ----
        self.btn_place = WinForms.Button()
        self.btn_place.Text = "Place Families"
        self.btn_place.Location = Drawing.Point(12, y)
        self.btn_place.Size = Drawing.Size(300, 32)
        self.btn_place.Font = self.font_button
        self.btn_place.Click += self.on_ok
        self.Controls.Add(self.btn_place)

        self.btn_cancel = WinForms.Button()
        self.btn_cancel.Text = "Cancel"
        self.btn_cancel.Location = Drawing.Point(338, y)
        self.btn_cancel.Size = Drawing.Size(300, 32)
        self.btn_cancel.Font = self.font_button
        self.btn_cancel.Click += self.on_cancel
        self.Controls.Add(self.btn_cancel)

    def update_divide_options_visibility(self, sender, args):
        """Show Divide Options GroupBox when Fixed Distance is selected"""
        is_fixed_distance = self.radio_fixed_distance.Checked
        is_each_segment = self.radio_each_segment.Checked
        is_total_length = self.radio_total_length.Checked

        # Show Divide Options if Fixed Distance AND (Each Element OR Total Path)
        should_show = is_fixed_distance and (is_each_segment or is_total_length)

        # Check if Divide Options GroupBox exists
        has_divide_options = hasattr(self, 'gb_divide_options')

        if should_show and not has_divide_options:
            # CREATE and ADD Divide Options group
            self.gb_divide_options = WinForms.GroupBox()
            self.gb_divide_options.Text = "Divide Options"
            self.gb_divide_options.Location = Drawing.Point(12, self.reverse_direction_y)
            self.gb_divide_options.Size = Drawing.Size(626, 70)
            self.gb_divide_options.Font = self.font_groupbox

            self.radio_divide_start = WinForms.RadioButton()
            self.radio_divide_start.Text = "Start"
            self.radio_divide_start.Location = Drawing.Point(20, 35)
            self.radio_divide_start.Size = Drawing.Size(140, 26)
            self.radio_divide_start.Font = self.font_radio
            self.gb_divide_options.Controls.Add(self.radio_divide_start)

            self.radio_divide_middle = WinForms.RadioButton()
            self.radio_divide_middle.Text = "Middle"
            self.radio_divide_middle.Location = Drawing.Point(340, 35)
            self.radio_divide_middle.Size = Drawing.Size(140, 26)
            self.radio_divide_middle.Font = self.font_radio
            self.radio_divide_middle.Checked = True
            self.gb_divide_options.Controls.Add(self.radio_divide_middle)

            # Add to Controls
            self.Controls.Add(self.gb_divide_options)

            # Increase form height (70px group + 30px spacing = 100px total)
            self.Height += 100

            # Move all controls below (at or after reverse_direction_y) down to avoid overlap
            for control in self.Controls:
                if control != self.gb_divide_options and control.Location.Y >= self.reverse_direction_y:
                    loc = control.Location
                    control.Location = Drawing.Point(loc.X, loc.Y + 100)

        elif not should_show and has_divide_options:
            # REMOVE Divide Options group
            self.Controls.Remove(self.gb_divide_options)
            delattr(self, 'gb_divide_options')

            # Decrease form height (70px group + 30px spacing = 100px total)
            self.Height -= 100

            # Move controls back up
            for control in self.Controls:
                if control.Location.Y > self.reverse_direction_y:
                    loc = control.Location
                    control.Location = Drawing.Point(loc.X, loc.Y - 100)

    def select_curves(self, sender, args):
        """Handle select curves button click"""
        try:
            elements = uidoc.Selection.PickElementsByRectangle("Select DetailCurves or ModelCurves (drag rectangle)")

            self.selected_curves = []
            if elements:
                for elem in elements:
                    try:
                        if isinstance(elem, (ModelCurve, DetailCurve)):
                            if hasattr(elem, 'Location'):
                                if isinstance(elem.Location, LocationCurve):
                                    self.selected_curves.append(elem)
                    except:
                        pass

            # Update status
            if self.selected_curves:
                self.lbl_select_status.Text = "{0} curve(s) selected".format(len(self.selected_curves))
                self.lbl_select_status.ForeColor = Drawing.Color.Green
            else:
                self.lbl_select_status.Text = "No curves found"
                self.lbl_select_status.ForeColor = Drawing.Color.Orange

        except Exception as ex:
            self.lbl_select_status.Text = "Selection cancelled"
            self.lbl_select_status.ForeColor = Drawing.Color.Orange

    def on_ok(self, sender, args):
        """Handle OK button click"""
        global dialog_confirmed, form_data
        try:
            distance = float(self.txt_distance.Text)
        except:
            distance = 1000.0  # Default 1000mm

        try:
            start_offset = float(self.txt_start_offset.Text)
        except:
            start_offset = 0.0

        try:
            end_offset = float(self.txt_end_offset.Text)
        except:
            end_offset = 0.0

        if self.radio_rot_90.Checked:
            rotation = 90
        elif self.radio_rot_180.Checked:
            rotation = 180
        elif self.radio_rot_270.Checked:
            rotation = 270
        else:
            rotation = 0

        # Determine divide position for Fixed Distance (Total Length or Each Segment)
        divide_position = 'start'  # default
        if hasattr(self, 'radio_divide_middle') and self.radio_divide_middle.Checked:
            divide_position = 'middle'
        elif hasattr(self, 'radio_divide_start') and self.radio_divide_start.Checked:
            divide_position = 'start'

        # Determine distance measurement method (Arc Length or Chord Length)
        distance_measurement = 'arc_length'  # default
        if self.radio_chord_length.Checked:
            distance_measurement = 'chord_length'

        form_data = {
            'curves': self.selected_curves,
            'distance': distance,
            'divide_type': 'maximum' if self.radio_maximum.Checked else 'fixed_distance',
            'segment_method': 'total_length' if self.radio_total_length.Checked else 'each_segment',
            'reverse_direction': self.radio_reverse_true.Checked,
            'start_offset': start_offset,
            'end_offset': end_offset,
            'family_index': self.cmb_family.SelectedIndex,
            'rotation': rotation,
            'divide_position': divide_position,
            'distance_measurement': distance_measurement,
            'families_list': self.families_list
        }

        dialog_confirmed = True
        self.Close()

    def on_cancel(self, sender, args):
        """Handle Cancel button click"""
        global dialog_confirmed
        dialog_confirmed = False
        self.Close()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

# Create and run the form (modeless pattern)
form = CurveDivisionDialog()
WinForms.Application.Run(form)

# Force close any lingering transactions (Revit 2021 compatibility)
try:
    TransactionManager.Instance.ForceCloseTransaction()
except:
    pass

# Process results after form is closed
if dialog_confirmed and form_data:
    try:
        curves_to_process = form_data.get('curves', [])

        if not curves_to_process:
            WinForms.MessageBox.Show("No curves selected.", "Warning")
            OUT = []
        elif form_data.get('family_index', -1) < 0 or form_data.get('family_index', -1) >= len(form_data.get('families_list', [])):
            WinForms.MessageBox.Show("No family selected.", "Error")
            OUT = []
        else:
            # Extract curves from elements
            curves = []
            for elem in curves_to_process:
                try:
                    if hasattr(elem, 'Location') and isinstance(elem.Location, LocationCurve):
                        curves.append(elem.Location.Curve)
                except:
                    pass

            if not curves:
                WinForms.MessageBox.Show("No valid curves found.", "Error")
                OUT = []
            else:
                # Get measurements in mm
                distance_mm = form_data.get('distance', 1000.0)
                start_offset_mm = form_data.get('start_offset', 0.0)
                end_offset_mm = form_data.get('end_offset', 0.0)
                reverse_direction = form_data.get('reverse_direction', False)

                # Convert to feet for Each Segment methods (Revit uses feet internally)
                distance_feet = distance_mm / 304.8
                start_offset_feet = start_offset_mm / 304.8
                end_offset_feet = end_offset_mm / 304.8

                # Initialize messages
                placed_instances = []
                error_messages = []
                debug_log = []

                # Generate division points based on segment and divide methods
                division_points = []
                segment_method = form_data.get('segment_method', 'total_length')
                divide_type = form_data.get('divide_type', 'maximum')
                distance_measurement = form_data.get('distance_measurement', 'arc_length')

                # ===== TOTAL LENGTH methods (use DesignScript, pass mm) =====
                if divide_type == 'maximum' and segment_method == 'total_length':
                    division_points = divide_max_total_length(curves, distance_mm, start_offset_mm, end_offset_mm, reverse_direction, distance_measurement)
                elif divide_type == 'fixed_distance' and segment_method == 'total_length':
                    # Get divide position from form data
                    divide_position = form_data.get('divide_position', 'start')
                    division_points = divide_fixed_total_length(curves, distance_mm, start_offset_mm, end_offset_mm, reverse_direction, divide_position, distance_measurement)
                # ===== EACH SEGMENT methods (use DesignScript, pass mm) =====
                elif divide_type == 'maximum' and segment_method == 'each_segment':
                    division_points = divide_max_each_segment(curves, distance_mm, start_offset_mm, end_offset_mm, reverse_direction, distance_measurement)
                elif divide_type == 'fixed_distance' and segment_method == 'each_segment':
                    # Get divide position from form data (already set in on_ok)
                    divide_position = form_data.get('divide_position', 'start')
                    division_points = divide_fixed_each_segment(curves, distance_mm, start_offset_mm, end_offset_mm, reverse_direction, divide_position, distance_measurement)
                else:
                    error_messages.append("ERROR: Invalid division combination")

                # Place family instances
                if division_points:
                    try:
                        family_symbol = form_data['families_list'][form_data['family_index']]['symbol']
                    except Exception as fam_ex:
                        error_messages.append("ERROR: Failed to get family symbol - {0}".format(str(fam_ex)))
                        family_symbol = None

                    if family_symbol is None:
                        error_messages.append("ERROR: Invalid or deleted family type selected. Please select a valid family.")
                    else:
                        # Activate family BEFORE transaction to avoid nested transaction conflicts
                        try:
                            if not family_symbol.IsActive:
                                family_symbol.Activate()
                        except Exception as activate_ex:
                            error_messages.append("WARNING: Could not activate family - {0}".format(str(activate_ex)))
                            # Continue anyway, family placement might still work

                        # Close any open transactions (Revit 2021 compatibility)
                        close_open_transactions()

                        # Use explicit Transaction for proper commit to document
                        t = Transaction(doc, "Place Families Along Curve")
                        t.Start()

                        try:
                            for div_index, div_point in enumerate(division_points):
                                try:
                                    # ===== Both Total Length and Each Segment now use DesignScript PolyCurve =====
                                    instance = place_family_with_rotation_polycurve(
                                        family_symbol,
                                        div_point['point'],
                                        div_point['polycurve'],
                                        div_point['param'],
                                        form_data.get('rotation', 0)
                                    )

                                    if instance is not None:
                                        placed_instances.append(instance)
                                    else:
                                        error_messages.append("Family #{0}: Failed to place (returned None)".format(div_index + 1))

                                except Exception as place_ex:
                                    error_messages.append("Family #{0}: {1}".format(div_index + 1, str(place_ex)))

                            t.Commit()

                        except Exception as tx_ex:
                            # Ensure transaction is closed
                            try:
                                if t.GetStatus() == TransactionStatus.Started:
                                    t.RollBack()
                            except:
                                pass
                            error_messages.append("Transaction error: {0}".format(str(tx_ex)))
                else:
                    error_messages.append("ERROR: No division points generated. Check curve selection and parameters.")

                # Build output message
                if error_messages:
                    error_text = "\n".join(error_messages)
                    WinForms.MessageBox.Show(error_text, "Placement Report", WinForms.MessageBoxButtons.OK, WinForms.MessageBoxIcon.Warning)

                # Return results (instances or errors)
                if placed_instances:
                    msg = "Successfully placed {0} family instances.".format(len(placed_instances))
                    WinForms.MessageBox.Show(msg, "Success", WinForms.MessageBoxButtons.OK, WinForms.MessageBoxIcon.Information)
                    OUT = placed_instances
                elif error_messages:
                    OUT = error_messages
                else:
                    OUT = ["ERROR: Unknown error occurred"]

    except Exception as ex:
        WinForms.MessageBox.Show("Error: " + str(ex), "Error", WinForms.MessageBoxButtons.OK, WinForms.MessageBoxIcon.Error)
        OUT = []
else:
    OUT = []

form.Dispose()
