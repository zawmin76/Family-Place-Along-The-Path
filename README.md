# Curve Division with Family Placement - Dynamo Script for Revit 2021+

## Overview

This is a comprehensive Dynamo Python script for Revit 2021 and later that allows you to:

1. **Select and filter curves** - DetailCurves and ModelCurves from your Revit model
2. **Join curves intelligently** - Auto-order curves by connectivity to form continuous paths
3. **Divide curves flexibly** - Multiple division methods and reference points
4. **Place families at division points** - Automatically place family instances with proper orientation
5. **Apply smart rotation** - Families align with curve direction or use fixed rotation angles

## File Location

```
Place Families Along Path.py
```

## How to Use

### Step 1: Setup in Dynamo

1. Open Dynamo for Revit
2. Create a new Python Script node or open an existing one
3. Copy the contents of `Place Families Along Path.py`
4. Paste into the Python Script node
5. Click Run (or use Ctrl+Enter)

### Step 2: Use the Dialog

When you run the script, a Windows Forms dialog will appear with the following steps:

#### **Step 1: Select Curves**
- Click the **"Select Curves"** button
- The dialog will temporarily minimize
- In Revit, select DetailCurves and/or ModelCurves in your model
- Click Finish in the selection prompt
- The dialog will show how many curves were selected

#### **Step 2: Configure Division**

**Divide Distance:**
- Enter the target distance between division points
- Unit: **Millimeters** (automatically converted to Revit internal units)
- Default: 1000mm
- Example: 200mm will place families 200mm apart

**Divide Method** (Choose ONE):
- **Maximum** (default) - Smart equal spacing
  - Divides equally so spacing ≤ divide_distance
  - Uses floor/ceil algorithm to find optimal spacing
  - All points equally distributed across 0 to 1
  - Best for: Even distribution across path
- **Fixed Distance** - Exact fixed intervals
  - Places points at exact divide_distance intervals across 0 to 1
  - Last point balanced to reach endpoint
  - Best for: Consistent regular patterns

**Distance Measurement** (Choose ONE - applies to BOTH Maximum and Fixed Distance):
- **Arc Length** (default) - Measure along actual curve
  - Points spaced by the actual path distance along curve
  - Follows the curve geometry exactly
  - Best for: Technical, engineering-precise measurements
- **Chord Length** - Measure by straight-line distance
  - Points spaced by straight-line distance (visual spacing from above)
  - What people see when looking down at the path
  - Best for: Bollards, visual elements, perceived spacing
  - Example: Bollards on curved platform appear equally spaced visually

**Path Scope** (Choose ONE):
- **Total Path** (default) - Join all curves
  - All selected curves ordered by connectivity
  - Treated as ONE continuous path
  - Division applies across entire combined length
  - Best for: Curved paths, connected railings
- **Each Element** - Divide each curve individually
  - Each curve divided separately
  - Different curves may have different spacing (Maximum)
  - Useful when curves are not connected
  - Best for: Disconnected segments, independent curves

**Reverse Direction** (Controls division direction):
- **False** (default): Divide from curve start (0 → 1)
  - First point at start, proceeds toward end
- **True**: Reverse curve first, then divide (1 → 0)
  - Reverses curve direction, then divides from new start
  - Useful for: Opposite direction placement

**Divide Options** (Only appears when Fixed Distance is selected):
- **START** - Place first point at curve start
  - Points at: 0, distance, 2×distance, 3×distance, ..., endpoint
  - Best for: Starting placement from beginning of path
  - Available for: Fixed Distance + Total Length AND Fixed Distance + Each Segment
- **MIDDLE** (default) - Balance start and end spacing
  - Points at: 0, balanced_start, balanced_start+distance, ..., endpoint
  - Automatically calculates largest balanced ends (≤ target distance)
  - Best for: Even distribution with balanced spacing at ends
  - Available for: Fixed Distance + Total Length AND Fixed Distance + Each Segment
- **Note:** For end-based placement, use **Reverse Direction** checkbox combined with START mode

**Start Offset:**
- Distance to skip from curve start
- Unit: **Millimeters**
- Default: 0mm
- Example: 100mm will start placing families 100mm from beginning

**End Offset:**
- Distance to skip from curve end
- Unit: **Millimeters**
- Default: 0mm
- Example: 50mm will stop placing families 50mm before endpoint

#### **Step 3: Select Family Type**
- Choose a family type from the dropdown
- Families are shown as `FamilyName:FamilyTypeName`
- **Autocomplete Search**: Type to filter families in real-time
- **Alphabetically Sorted**: Families sorted by family name for easy navigation
- Only loaded family types that can be instantiated are shown
- Status shows number of available families

#### **Rotation Options:**
- **0°** (default): Families align with curve direction
  - Family X-axis aligns with curve tangent
  - Useful for elements that should follow the curve
- **90°, 180°, 270°**: Additional rotation in degrees
  - Rotates from the base tangent direction
  - Useful for specific orientations

**Rotation Note:** The rotation is applied as an additional angle on top of the curve tangent alignment. So 0° means "follow the curve exactly," and 90° means "follow the curve plus 90 degrees."

#### **Step 4: Place Families**
- Click **"Place Families"** to execute
- A success message shows how many families were placed
- Families appear in your Revit model

### Selection Dialog Behavior

The script uses an intelligent two-stage selection process:

**Stage 1 (Preferred):** Filtered selection
- Shows only ModelCurves and DetailCurves
- Uses ISelectionFilter for compatibility with most Dynamo versions
- If this works, skip to curve selection in Revit

**Stage 2 (Fallback):** Unfiltered selection
- If filtered selection fails, automatically tries unfiltered selection
- You can select any elements; script filters for curves automatically
- More compatible with non-standard Dynamo installations

If you see **"Selection failed - check console"**:
1. Open **View → Show Console** in Dynamo (Ctrl+~)
2. Look for error message in console output
3. See **Debugging with Console Output** section below for solutions

## Features in Detail

### Curve Joining (Auto-Ordering)

When "Total Length" is selected:
- The script automatically orders curves by connecting endpoints
- Curves are reversed as needed to form a continuous path
- Uses tolerance-based matching (0.01 units) to find endpoints
- Result is a single path that can be divided evenly

### Division Logic: 4 Complete Combinations

The script combines **Divide Method** (Maximum/Fixed Distance) with **Segment Method** (Total Length/Each Segment) to create 4 distinct behaviors.

**Simplified Logic:**
- After reducing curve by offsets, all division happens from **0 → 1** of the reduced curve
- **Reverse Direction** handles backward division (reverses curve, then divides 0 → 1)
- No Start/Middle/End reference points needed

#### **Combination 1: Maximum + Total Length**
**Join all curves → Reduce by offsets → Equal spacing**

```
Example: 3 curves (1000mm, 2000mm, 800mm) = 3800mm total
Start Offset: 100mm | Divide Distance: 200mm

1. Join all curves → 3800mm total length
2. Reduce by offsets → 3800 - 100 = 3700mm usable
3. Calculate optimal divisions:
   - Ideal: 3700 / 200 = 18.5 divisions
   - Try floor (18): spacing = 3700 / 18 = 205.6mm (❌ > 200mm, reject)
   - Try ceil (19): spacing = 3700 / 19 = 194.7mm (✅ ≤ 200mm, accept)
4. Result: 19 points at EQUAL 194.7mm spacing
```

**Key behavior:** All curves treated as ONE continuous path. Equal spacing across entire path.

#### **Combination 2: Maximum + Each Segment**
**Reduce each curve individually → Equal spacing per curve**

```
Example: 3 curves (1000mm, 2000mm, 800mm)
Start Offset: 100mm | Divide Distance: 200mm

Curve 1 (1000mm):
  - Reduce: 1000 - 100 = 900mm usable
  - Optimal: 900 / 200 = 4.5 divisions
  - Try: 4 divs → 225mm ❌, Try: 5 divs → 180mm ✅
  - Result: Spacing = 180mm

Curve 2 (2000mm):
  - Reduce: 2000 - 100 = 1900mm usable
  - Optimal: 1900 / 200 = 9.5 divisions
  - Try: 9 divs → 211mm ❌, Try: 10 divs → 190mm ✅
  - Result: Spacing = 190mm

Curve 3 (800mm):
  - Reduce: 800 - 100 = 700mm usable
  - Optimal: 700 / 200 = 3.5 divisions
  - Try: 3 divs → 233mm ❌, Try: 4 divs → 175mm ✅
  - Result: Spacing = 175mm

Final: Each curve has equal spacing WITHIN itself (180, 190, 175)
```

**Key behavior:** Each curve divided independently. Different curves = different spacing.

#### **Combination 3: Fixed Distance + Total Length**
**Join all curves → Reduce by offsets → Exact fixed intervals with START or MIDDLE positioning**

```
Example: 3 curves (1000mm, 2000mm, 800mm) = 3800mm total
Start Offset: 100mm | Divide Distance: 200mm | Divide Options: START

1. Join all curves → 3800mm
2. Reduce by offset → 3700mm usable
3. Divide Option = START: Place at EXACT fixed intervals from start
   - Point 1: 0mm (curve start)
   - Point 2: 200mm
   - Point 3: 400mm
   - Point 4: 600mm
   - ...continuing at 200mm intervals...
   - Point 19: 3600mm
   - Point 20: 3700mm (endpoint)

Total: 20 points at exactly 200mm spacing from start

---

Alternative with MIDDLE:
Divide Option = MIDDLE: Balance remainder on both ends
   - Fit 18 full segments: 18 × 200 = 3600mm
   - Remainder: 3700 - 3600 = 100mm
   - Balance: 50mm start + 50mm end
   - Points: [0, 50, 250, 450, 650, ..., 3650, 3700]

Total: 20 points with balanced 50mm at both ends
```

**Key behavior:** Exact fixed intervals across entire path. START places from beginning (0), MIDDLE balances ends. No END option for Total Length (use Reverse Direction if needed).

#### **Combination 4: Fixed Distance + Each Segment**
**Reduce each curve individually → Exact fixed intervals with START or MIDDLE positioning**

```
Example: 3 curves (1000mm, 2000mm, 800mm)
Start Offset: 100mm | Divide Distance: 200mm | Divide Options: START

Curve 1 (1000mm):
  - Reduce: 1000 - 100 = 900mm usable
  - START: Points at [0, 200, 400, 600, 800, 900]
  - Result: 6 points with balanced 100mm at end

Curve 2 (2000mm):
  - Reduce: 2000 - 100 = 1900mm usable
  - START: Points at [0, 200, 400, ..., 1800, 1900]
  - Result: 10 points equally spaced

Curve 3 (800mm):
  - Reduce: 800 - 100 = 700mm usable
  - START: Points at [0, 200, 400, 600, 700]
  - Result: 5 points with balanced 100mm at end

---

Alternative with MIDDLE (Curve 1 example):
  - Fit 4 full segments: 4 × 200 = 800mm
  - Remainder: 900 - 800 = 100mm
  - Balance: 50mm start + 50mm end
  - MIDDLE: Points at [0, 50, 250, 450, 650, 900]
  - Result: 6 points with balanced 50mm at both ends

---

To place from curve end, use Reverse Direction checkbox with START mode:
  - Enable "Reverse Direction" → Reverses curve first
  - START on reversed: Points placed from what is now the start (was the end)
  - Result: First point 100mm from original end, intervals from end
```

**Key behavior:** Each curve divided independently at fixed intervals. START places from curve beginning (0), MIDDLE balances ends. For end-based placement, use Reverse Direction + START.

### Offset Behavior

**Start Offset & End Offset:**
- Applied BEFORE division (reduces usable length)
- For Total Length: Applied to combined path length
- For Each Segment: Applied to each individual curve

```
Example: Curve 500mm, Start Offset 50mm, End Offset 75mm
Usable length: 500 - 50 - 75 = 375mm
Division starts at 50mm, ends before 425mm
```

### Spacing Algorithm (Maximum Method)

The Maximum method uses intelligent floor/ceil comparison:

```
Algorithm:
1. Reduce curve by offsets (calculate usable_length)
2. Calculate ideal divisions: usable_length / divide_distance
3. Try floor(divisions) and ceil(divisions)
4. For each, calculate actual spacing: usable_length / num_divisions
5. Accept spacing that is:
   - ≤ divide_distance (never exceed target)
   - Closest to divide_distance (best fit)
6. Divide reduced curve from 0 → 1 (or 1 → 0 if reversed)
7. Place points at equal intervals using selected spacing
```

This ensures:
- Spacing never exceeds the target distance
- Spacing is as close as possible to the target
- All points are equally spaced from 0 to 1
- Reverse Direction reverses the curve first, then applies same logic

## UI Design & Accessibility

### Windows 11 Default Form Design
The dialog uses clean Windows 11 default styling with standard Segoe UI 9pt font:

| Aspect | Value | Notes |
|---|---|---|
| **Form Size** | 680×930px | Fixed size, Windows 11 standard |
| **Font** | Segoe UI 9pt | Windows 11 default, clean appearance |
| **Style** | FixedDialog | Non-resizable, user cannot change size |
| **Appearance** | Standard Windows | No custom themes or colors |
| **Control Spacing** | 100px (groups) | Consistent vertical spacing between major sections |

All controls scale proportionally using a scaling factor (form_width / 800), ensuring:
- ✅ No text cutoff on smaller screens
- ✅ No overlapping buttons or controls
- ✅ Readable font sizes across all resolutions
- ✅ Consistent spacing and alignment

### Dialog Layout
- **Form Size**: 680px wide × 930px tall (Windows 11 default, fixed)
- **Vertical Spacing**: 100px between major sections (consistent, 70px group + 30px gap)
- **Vertical Section Order**:
  1. Select Path button (50px)
  2. Status label (50px)
  3. Divide Distance input (60px)
  4. Divide Method GroupBox (100px)
  5. Distance Measurement GroupBox (100px) - NEW, always visible
  6. Path Scope GroupBox (100px)
  7. Reverse Direction label/radio (50px)
  8. Start Offset input (50px)
  9. End Offset input (50px)
  10. Family Type dropdown + status (100px)
  11. Rotation GroupBox (100px)
  12. Place Families & Cancel buttons (32px)
  13. Divide Options GroupBox (100px) - appears when Fixed Distance selected
- **Label Position**: All labels start at x=12px, width 190px
- **Input Controls Alignment**: All textboxes, dropdowns, and radio buttons aligned at x=200px
- **Control Width**: Input fields and dropdowns 438px
- **Font**: Segoe UI 9pt throughout
- **Consistent Alignment**:
  - Divide Distance, Start Offset, End Offset textboxes all at x=200px
  - Family Type dropdown at x=200px
  - Reverse Direction radio buttons aligned with inputs for visual consistency
  - Distance Measurement always visible between Divide Method and Path Scope

### Font Compatibility
- **Primary**: Segoe UI (modern, clean)
- **Fallback 1**: Arial (widely available)
- **Fallback 2**: Generic Sans Serif (system default)
- Automatically uses best available font for maximum compatibility

### Accessibility Features
- Larger, readable fonts (11pt instead of 8-9pt)
- Increased control heights (28-45px)
- Clear visual separation between sections
- Status indicators with color coding
- Searchable family dropdown with autocomplete

### Rotation Alignment

- **Rotation = 0°**: Families orient along curve tangent
  - Family "forward" direction follows curve direction
  - Tangent is calculated using binary search on curve arc length
  - Angle = atan2(tangent.Y, tangent.X) from X-axis

- **Rotation = 90°, 180°, 270°**: Additional rotation applied
  - Total rotation = tangent_angle + user_rotation_degrees
  - All rotations around Z-axis (vertical in typical Revit views)
  - Applied using ElementTransformUtils.RotateElement()

### Mathematical Formulas

**Maximum Method (Smart Equal Spacing):**
```
1. usable_length = curve_length - start_offset - end_offset
2. ideal_divisions = usable_length / divide_distance
3. num_divs_floor = floor(ideal_divisions)
4. num_divs_ceil = ceil(ideal_divisions)
5. spacing_floor = usable_length / num_divs_floor
6. spacing_ceil = usable_length / num_divs_ceil
7. IF spacing_floor ≤ divide_distance:
       use spacing_floor
   ELSE:
       use spacing_ceil
8. Divide reduced curve from 0 → 1 at calculated spacing
9. IF Reverse Direction = True: reverse curve first, then apply 0 → 1
```

**Fixed Distance Method (Exact Intervals):**
```
1. usable_length = curve_length - start_offset - end_offset
2. Divide reduced curve from 0 → 1 at exact divide_distance intervals
3. positions = [0, divide_distance, 2×divide_distance, ..., usable_length]
4. Last point placed at endpoint (balanced spacing)
5. IF Reverse Direction = True: reverse curve first, then apply
```

**Binary Search (Distance → Parameter):**
```
target_distance = position on curve
param_low = 0.0, param_high = 1.0

WHILE iterations < 50:
    param_mid = (param_low + param_high) / 2
    arc_length = calculate_arc_length(0, param_mid)

    IF abs(arc_length - target_distance) < 0.01:
        return param_mid
    ELSE IF arc_length < target_distance:
        param_low = param_mid
    ELSE:
        param_high = param_mid

return (param_low + param_high) / 2
```

### Division Functions Architecture

The script uses 4 specialized functions to handle all division combinations. Each function is optimized for its specific combination:

#### **divide_max_total_length()**
- **Combination:** Maximum + Total Length
- **Approach:**
  1. Convert all Revit curves to DesignScript curves
  2. Create PolyCurve.ByJoinedCurves() to join all curves in order
  3. Reverse the PolyCurve if needed (before trimming)
  4. Trim with ExtendStart/ExtendEnd (offset trimming in mm)
  5. Calculate total length and usable length (after offsets)
  6. Use floor/ceil algorithm to find optimal spacing
  7. Divide trimmed PolyCurve using distance_measurement:
     - **Arc Length**: PointsAtEqualSegmentLength() - equal spacing along actual curve
     - **Chord Length**: PointsAtEqualChordLength() - equal straight-line spacing
  8. Get parameter for each point for tangent calculation
- **Result:** All curves treated as ONE path with equal spacing (arc or chord based)

#### **divide_fixed_total_length()**
- **Combination:** Fixed Distance + Total Length
- **Approach:**
  1. Convert all Revit curves to DesignScript curves
  2. Create PolyCurve.ByJoinedCurves() to ensure proper ordering
  3. Reverse the PolyCurve if needed (before trimming)
  4. Trim with ExtendStart/ExtendEnd (offset trimming in mm)
  5. Based on distance_measurement parameter:
     - **Arc Length**: Calculate arc-length distances [0, distance, 2×distance, ...]
     - **Chord Length**: Use PointsAtChordLengthFromPoint() to find all points at equal chord intervals
  6. For Arc Length: Based on divide_position parameter:
     - **START**: Place at distances [0, distance, 2×distance, ...]
     - **MIDDLE**: Calculate balanced start_offset, then [0, start_offset, start_offset+distance, ...]
  7. For Chord Length: Use PointsAtChordLengthFromPoint() which handles iteration internally
  8. Always add endpoint as last position (balanced for arc length)
- **Result:** All curves as ONE path with exact fixed intervals (arc or chord based)

#### **divide_max_each_segment()**
- **Combination:** Maximum + Each Segment
- **Approach:**
  1. Convert all Revit curves to DesignScript curves
  2. Create PolyCurve.ByJoinedCurves() to ensure proper ordering and direction
  3. Reverse the PolyCurve if needed (before trimming)
  4. Explode PolyCurve using .Curves() to get individual curves (now in correct order/direction)
  5. For EACH exploded curve individually:
     - Trim with ExtendStart/ExtendEnd (offset trimming in mm)
     - Calculate optimal spacing using floor/ceil algorithm
     - Divide trimmed curve using distance_measurement:
       - **Arc Length**: PointsAtEqualSegmentLength() - equal spacing along curve
       - **Chord Length**: PointsAtEqualChordLength() - equal straight-line spacing
     - Get parameter for each point for tangent calculation
  6. Collect all division points
- **Result:** Each curve divided independently with equal spacing (arc or chord based). Different curves may have different spacing

#### **divide_fixed_each_segment()**
- **Combination:** Fixed Distance + Each Segment
- **Approach:**
  1. Convert all Revit curves to DesignScript curves
  2. Create PolyCurve.ByJoinedCurves() to ensure proper ordering and direction
  3. Reverse the PolyCurve if needed (before trimming)
  4. Explode PolyCurve using .Curves() to get individual curves (now in correct order/direction)
  5. For EACH exploded curve individually:
     - Trim with ExtendStart/ExtendEnd (offset trimming in mm)
     - Based on distance_measurement parameter:
       - **Arc Length**: Generate arc-length distances and use PointAtSegmentLength
       - **Chord Length**: Use PointsAtChordLengthFromPoint() to find all points at equal chord intervals
     - For Arc Length, based on divide_position parameter:
       - **START**: Generate distances [0, distance, 2×distance, ...]
       - **MIDDLE**: Calculate balanced start_offset, then [0, start_offset, start_offset+distance, ...]
     - For Chord Length: Use PointsAtChordLengthFromPoint() which handles iteration internally
     - Always add endpoint as last position
  6. Collect all division points
- **Result:** Each curve has fixed interval spacing with endpoint balanced (arc or chord based). Two positioning options: START from beginning, MIDDLE with balanced ends

**Offset Calculation (Per Curve):**
```
usable_length = curve_length - start_offset - end_offset
IF usable_length ≤ 0:
    skip this curve (too short)
```

**Unit Conversion:**
```
distance_mm = user_input
distance_feet = distance_mm / 304.8  // Revit internal unit
```

## Technical Details

### Core Functions

#### Division Functions (4 Combinations)

| Function | Purpose |
|----------|---------|
| `divide_max_total_length()` | **Combination 1:** Maximum spacing + Total Length (join all, divide equally) |
| `divide_fixed_total_length()` | **Combination 3:** Fixed distance + Total Length (join all, exact intervals) |
| `divide_max_each_segment()` | **Combination 2:** Maximum spacing + Each Segment (divide each independently) |
| `divide_fixed_each_segment()` | **Combination 4:** Fixed distance + Each Segment (divide each at fixed intervals) |

#### Family & Placement Functions

| Function | Purpose |
|----------|---------|
| `get_available_families()` | Collect all loadable family types from document |
| `place_family_with_rotation_polycurve()` | Place family instance with curve-aligned rotation using DesignScript PolyCurve |

### Revit API Methods Used

- `FilteredElementCollector` - Collect families
- `LocationCurve.Curve` - Extract geometry
- `Curve.Evaluate()` - Get points at parameters
- `Curve.ComputeDerivatives()` - Get tangent vectors
- `doc.Create.NewFamilyInstance()` - Place families
- `ElementTransformUtils.RotateElement()` - Apply rotation
- `ISelectionFilter` - Custom selection filtering

## Error Handling

The script includes robust error handling for:

### Selection Phase
- No curves selected
- User cancels selection
- ISelectionFilter failures (uses fallback)
- Invalid element types (auto-filtered)
- Multiple selection attempts with fallback mechanism

### Curve Processing
- Empty curves (zero length)
- Curve parameter evaluation failures
- Invalid endpoint detection
- Curve joining/reversal failures

### Family Placement
- Invalid distance values (defaults to 1.0)
- No family types available
- Family instance creation failures
- Rotation transformation errors
- Missing or inactive families

### Transaction Management
- Failed transactions are rolled back
- Individual family placement failures don't stop others
- Successful placements are collected and returned

Failed operations are skipped, and successful ones are reported.

## Output

The script returns:

```python
OUT = [placed_family_instance_1, placed_family_instance_2, ...]
```

A list of successfully placed FamilyInstance objects that can be:
- Further modified in Dynamo nodes
- Analyzed or filtered
- Used in downstream operations

## Examples

### Example 1: Pillar Placement Along Curved Wall (Combination 3)
**Maximum + Total Length + Fixed Distance**

1. Select: One ModelCurve (curved wall centerline, 50m)
2. Divide Method: **Fixed Distance**
3. Segment: **Total Length**
4. Divide Distance: 5000mm (5m pillar spacing)
5. Start Offset: 500mm (skip first 0.5m)
6. Family: Pillar 24x24
7. Rotation: 0° (pillars follow wall curve)

**Result:** Pillars placed at exact 5m intervals starting at 500mm from beginning, last spacing balanced

### Example 2: Fence Posts on Disconnected Segments (Combination 4)
**Fixed Distance + Each Segment**

1. Select: 3 DetailCurves (fence segments, unconnected, each 100-200m)
2. Divide Method: **Fixed Distance**
3. Segment: **Each Segment**
4. Divide Distance: 2000mm (2m post spacing)
5. Start Offset: 0mm
6. Family: Fence Post
7. Rotation: 90° (posts perpendicular to fence)

**Result:** Each fence segment divided independently with 2m spacing. Last post on each segment balanced to reach endpoint

### Example 3: Lights Along Connected Path (Combination 1)
**Maximum + Total Length**

1. Select: 2 ModelCurves (corridor path joined end-to-end, 300m total)
2. Divide Method: **Maximum**
3. Segment: **Total Length**
4. Divide Distance: 6000mm (6m target spacing)
5. Start Offset: 1000mm, End Offset: 500mm (balanced endpoints)
6. Family: Light Fixture 2x2
7. Rotation: 0° (lights follow corridor)

**Result:** Lights evenly spaced across entire 298m usable path (300m - offsets). All spacing equal, no larger than 6m

### Example 4: Posts on Multiple Unconnected Curves (Combination 2)
**Maximum + Each Segment**

1. Select: 4 Arc curves (building perimeter, separate segments, 50-100m each)
2. Divide Method: **Maximum**
3. Segment: **Each Segment**
4. Divide Distance: 3000mm (3m target spacing)
5. Start Offset: 0mm
6. Family: Post
7. Rotation: 0° (posts follow curve)

**Result:** Each arc divided to fit target 3m spacing. Different arcs may have different actual spacing based on their individual lengths

## Tips & Tricks

### Understanding the 4 Combinations

All combinations divide from **0 → 1** of the reduced curve (0 → 1 reversed if Reverse Direction = True).

| Divide Method | Segment | Division | Positioning | Best For |
|---|---|---|---|---|
| **Maximum** | **Total Length** | Equal spacing across entire joined path | N/A | Curved paths, connected elements |
| **Maximum** | **Each Segment** | Equal spacing per curve (may differ) | N/A | Individual curves, allow different spacing |
| **Fixed Distance** | **Total Length** | Exact intervals across entire path | START / **MIDDLE** (default) | Consistent spacing, connected paths |
| **Fixed Distance** | **Each Segment** | Exact intervals per curve | START / **MIDDLE** (default) | Per-curve control, disconnected elements |

### Divide Options (Fixed Distance Only)

When using **Fixed Distance** method, two positioning options appear:

| Option | Start Point | Behavior | Best For | Default |
|---|---|---|---|---|
| **START** | At curve start (0) | [0, distance, 2×distance, ...] | Placement from beginning | - |
| **MIDDLE** | Balanced offset | [0, offset, offset+distance, ...] | Even distribution, balanced ends | ✓ |

**For end-based placement:** Use **Reverse Direction** checkbox with START mode
- Reverse Direction reverses the curve, then START naturally places from the end
- Available for both Total Length and Each Segment

### Arc Length vs Chord Length

**Understanding the Difference:**

Both Distance Measurement options apply to BOTH Maximum and Fixed Distance methods.

```
Example: Curved path (like a bollard line on a platform)

Arc Length (measure along the actual curve):
    ╭─● ← spacing = 1000mm arc distance
    │  ╰─● ← spacing = 1000mm arc distance
    │     ╰─● ← spacing = 1000mm arc distance
    Technically precise, follows curve path exactly

Chord Length (measure straight-line distance):
    ╭───● ← spacing = 1000mm straight line
    │   ╭─● ← spacing = 1000mm straight line
    │   │╭─● ← spacing = 1000mm straight line
    Visually equal when viewed from above
```

**When to use Arc Length:**
- Technical/engineering precision required
- Measuring actual traveled distance along path
- Internal engineering documents
- Tangent/derivative calculations for rotation

**When to use Chord Length:**
- Visual/aesthetic elements (bollards, lights, posts)
- What people see from above
- Bollard placement on curved platforms
- Consistent visual appearance is priority
- Real-world perception (nobody measures arc length visually)

**Real-world Example (Bollard Placement):**
- A curved platform edge is 5000mm arc length but only 4800mm straight-line (chord)
- **Arc Length + Fixed 1000mm**: Places bollards at arc intervals, visually unequal
- **Chord Length + Fixed 1000mm**: Places bollards at straight-line intervals, visually equal

### Maximum Method Algorithm

The Maximum method uses smart floor/ceil comparison:
```
If usable_length / divide_distance = 4.5:
  - Try 4 divisions: spacing = 112.5% of target ❌ (exceeds)
  - Try 5 divisions: spacing = 90% of target ✅ (accept)
  Result: 5 equal points
```

Always picks spacing ≤ target distance, closest possible.

### Offset Behavior

**Start Offset:** Reduces length from beginning
**End Offset:** Reduces length from end

```
Curve: 1000mm | Start 100mm | End 50mm
Usable: 1000 - 100 - 50 = 850mm
First family at: 100mm
Last family at: 950mm (before 950+50=1000 endpoint)
```

### When to Use Each Combination

**Choose Total Path when:**
- Curves form one continuous path (railing, fence line)
- Want equal spacing across entire path
- Curves are connected or should be treated as connected

**Choose Each Element when:**
- Curves are separate/unconnected (individual elements)
- OK with different spacing per curve
- Each element is independent

**Choose Maximum when:**
- Want flexible, smart spacing
- Equal distribution more important than exact distance
- Spacing is optimized to ≤ divide_distance

**Choose Fixed Distance when:**
- Need exact regular intervals
- Consistent spacing is critical
- Last point balanced to reach endpoint

**Choose Arc Length when:**
- Technical/engineering precision required
- Measuring actual traveled distance along the curve
- Internal engineering documents
- Tangent calculations for proper rotation

**Choose Chord Length when:**
- Placing visual elements (bollards, lights, posts)
- What people see from above matters most
- Consistent visual appearance is priority
- Real-world placement (nobody measures arc length visually)

**Use Reverse Direction when:**
- Want division to proceed from curve end to start
- Need families placed in opposite direction
- Reverses curve, then divides from new start

### Curve Selection
- Hold Ctrl to select multiple curves
- The filter only allows DetailCurves and ModelCurves (no Reference Lines)
- Lines created in Revit's Sketch mode will not appear

### Joining Curves
- For **Total Length**: Ensure curves are reasonably close at endpoints
- The script uses 0.01 unit tolerance for endpoint matching
- If curves don't join properly, use **Each Segment** instead

### Distance Measurement (Arc vs Chord)

**Arc Length (default):**
- Measures along the actual curve path
- Always ≥ chord length (curve is longer than straight line)
- Best for: Technical precision, engineering, internal calculations
- Real-world: How far you'd travel if walking the curve

**Chord Length:**
- Measures straight-line distance between points
- How it looks from above (visual perception)
- Best for: Bollards, lights, visible elements
- Real-world: What people see when looking down at the element placement

**Choosing:**
- **Bollards on curved platform**: Use Chord Length (visually equal)
- **Technical engineering document**: Use Arc Length (precise)
- **Lights along curved path**: Use Chord Length (visually balanced)
- **Internal survey/measurement**: Use Arc Length (actual distance)

**Note:** The difference is noticeable on highly curved paths (tight curves). On straight paths, arc length ≈ chord length.

### Division Distance
- Use **Millimeters** for all distances (including offsets)
- Automatic conversion to Revit internal units (feet)
- For Maximum: Actual spacing ≤ divide_distance (smart fit)
- For Fixed Distance: Exact spacing intervals, last point balanced
- Very small distances (< 100mm) may create many points
- Distance measurement (Arc vs Chord) applies to both Maximum and Fixed Distance

### Offsets
- **Start Offset:** Removes distance from beginning of path
- **End Offset:** Removes distance from end of path
- Applied BEFORE division (reduces usable length)
- Useful for: Corners, joints, clearances

### Family Selection
- Only active families in the document are shown
- Family must be loadable (not external references)
- Symbol types within a family are separated in the dropdown
- Check family is placed correctly before running on many curves

### Rotation
- **0°** (default): Families align with curve direction (most common)
- **90°, 180°, 270°**: Additional rotation from curve direction
- Rotation is around Z-axis (vertical)
- For perpendicular placement, use 90° or 270°
- Test with one curve first to verify orientation

## Debugging with Console Output

The script includes detailed console logging to help troubleshoot issues. To view debug output:

1. **Open Dynamo Console**: Go to **View → Show Console** (or press `Ctrl+~`)
2. **Run the script** and look for output like:
   - `"Select button clicked"` → Button click detected
   - `"Dialog hidden, ready for selection"` → Dialog ready for selection
   - `"Selection filter error: ..."` → Error with curve filter
   - `"Trying fallback selection without filter..."` → Using alternative selection method
   - `"Fallback selection error: ..."` → Even fallback failed

### Console Error Messages

**"Selection filter error: ISelectionFilter not supported"**
- ISelectionFilter may not work in your Dynamo version
- Script will automatically use fallback selection method
- Select any curves in Revit; script filters them automatically

**"Fallback selection error: ..."**
- Both selection methods failed
- Check that uidoc.Selection is properly initialized
- Verify Revit is active and responsive

**"Parameter is not valid" (Font error)**
- Usually occurs during dialog initialization
- Script uses try-except to recover
- Dialog should still display without custom fonts

## Troubleshooting

### Dialog doesn't appear
- Check if Python is enabled in Dynamo
- Verify all imports are correct
- Look for error messages in the console (View → Show Console)
- Check that you're using Revit 2023 or later

### "Selection failed - check console" message
- Open **Dynamo Console** (View → Show Console)
- Look for error message that starts with "Fallback selection error:"
- This tells you what went wrong
- Common fixes:
  - Close and reopen Dynamo
  - Make sure Revit window is active/focused
  - Try running script again with Revit in foreground

### No curves selected message
- Make sure to click the "Select Curves" button
- When prompted, select ModelCurves or DetailCurves in Revit
- Hold Ctrl to select multiple curves
- Press Enter or click "Finish" when done selecting
- Only ModelCurves and DetailCurves are allowed (no Reference Lines)

### "Selection cancelled by user"
- You clicked Escape or clicked outside selection window
- Click "Select Curves" button again to retry

### Families don't place
- Verify family type is selected in dropdown
- Check if family is activated in the document
- Ensure placement points are valid in 3D space
- Check console for "NewFamilyInstance failed" errors

### Rotation looks wrong
- Remember: 0° means "follow the curve"
- Try 90°, 180°, or 270° for different orientations
- Rotation is in degrees, around Z-axis

### Curves don't join properly
- Enable "Divide individually" instead
- Check for gaps between curve endpoints
- Verify curve direction with Revit's curve display
- Script uses 0.01 unit tolerance for endpoint matching

## Known Issues

### None Currently
**Status:** ✅ All 8 combinations are working correctly (4 methods × 2 distance measurements)

**Recent Fixes (February 2025):**
- ✅ Fixed family activation error - moved inside transaction
- ✅ Fixed missing endpoints with Fixed Distance + Chord Length methods
- ✅ Chord Length support added to all 4 division functions
- ✅ Maximum methods now support both Arc Length (PointsAtEqualSegmentLength) and Chord Length (PointsAtEqualChordLength)
- ✅ Fixed Distance methods now support both Arc Length (PointAtSegmentLength) and Chord Length (PointsAtChordLengthFromPoint)
- ✅ Distance Measurement option added to UI (always visible, applies to both Maximum and Fixed Distance)
- ✅ Chord length uses PointsAtChordLengthFromPoint() for automatic iteration (avoids out-of-range errors)
- ✅ All division functions accept distance_measurement parameter
- ✅ Fixed spacing control after Divide Options group (100px including 30px gap)
- ✅ All methods now use DesignScript PolyCurve.ByJoinedCurves()
- ✅ Total Length: Creates PolyCurve, trims, reverses, divides entire joined path
- ✅ Each Segment: Creates PolyCurve for proper ordering, explodes to individual curves, trims each, divides independently
- ✅ Offset trimming uses ExtendStart/ExtendEnd for accurate curve reduction
- ✅ Reverse direction applied before offset trimming
- ✅ Unit handling: All calculations in mm (DesignScript native), converted to XYZ only at placement

## System Requirements

- **Revit 2021** or later (with transaction safety for 2021)
- **Dynamo for Revit** (compatible versions with Python 3 support)
- **Python 3** support enabled in Dynamo
- **Windows Forms** support (Windows only, not Mac)
- **.NET Framework** 4.x or higher (usually included with Revit)

### Known Compatibility

- ✅ Revit 2021 (with ForceCloseTransaction() for transaction safety)
- ✅ Revit 2022
- ✅ Revit 2023
- ✅ Revit 2024
- ✅ Revit 2025 (with Dynamo Python 3)
- ⚠️ Mac versions of Revit cannot use Windows Forms dialog

### Revit 2021 Notes

For Revit 2021 users, the script includes:
- **ForceCloseTransaction()** at startup to clear stuck transactions
- **Transaction safety checks** before starting new transactions
- **Graceful error handling** for transaction state issues
- Automatically handles nested transaction conflicts

### Import Configuration

The script uses clean, minimal imports:

1. **StructuralType** - Direct import from `Autodesk.Revit.DB.Structure`
2. **Revit API** - Wildcard import from `Autodesk.Revit.DB` (covers all needed classes)
3. **Font Creation** - Uses try-except blocks for Arial font; falls back to default if unavailable
4. **Button Styling** - Wraps color/style changes in try-except to prevent rendering errors

## Performance Notes

- Script performance depends on:
  - Number of selected curves
  - Number of division points
  - Complexity of family geometry

- Large operations (100+ families) may take a few seconds
- Transactions are grouped for efficiency

## Output in Dynamo

After execution, you can:
- Connect output to other Dynamo nodes for further processing
- Use output in downstream operations
- Verify placement in Revit viewport

## Version History

- **v2.9** (February 2025): Bug Fixes - Family Activation & Chord Length Endpoints
  - **Fixed Family Activation Error**:
    - **Issue**: `FamilySymbol.Activate()` called outside transaction, causing "Attempt to modify model outside of transaction" error
    - **Solution**: Moved family activation INSIDE transaction (after `t.Start()`)
    - **Result**: ✅ Families now activate without warnings
  - **Fixed Missing Endpoints with Chord Length**:
    - **Issue**: Fixed Distance + Chord Length methods didn't place families at curve endpoint
    - **Root Cause**: `PointsAtChordLengthFromPoint()` only returns chord intervals, not endpoint
    - **Solution**: Explicitly add endpoint for both `divide_fixed_total_length()` and `divide_fixed_each_segment()` with chord_length measurement
    - **Affected Combinations**:
      - Fixed Distance + Total Length + Chord Length
      - Fixed Distance + Each Segment + Chord Length (both START and MIDDLE modes)
    - **Result**: ✅ Families now place at both start and end of curves with chord length measurement
  - **Status**: ✅ All 8 combinations fully working (4 divide methods × 2 distance measurements) with proper endpoint coverage

- **v2.8** (February 2025): Chord Length Support for All Division Methods
  - **New Feature: Distance Measurement option**:
    - Applies to BOTH Maximum and Fixed Distance methods
    - Choose: Arc Length (default) or Chord Length
    - Always visible between Divide Method and Path Scope groups
  - **Implementation Details**:
    - **Maximum + Arc Length**: Uses `PointsAtEqualSegmentLength()` - equal arc distance spacing
    - **Maximum + Chord Length**: Uses `PointsAtEqualChordLength()` - equal straight-line spacing
    - **Fixed Distance + Arc Length**: Uses `PointAtSegmentLength()` - arc-based fixed intervals
    - **Fixed Distance + Chord Length**: Uses `PointsAtChordLengthFromPoint()` - chord-based fixed intervals
  - **Use Cases**:
    - Arc Length: Technical/engineering precision, actual path measurement
    - Chord Length: Visual elements (bollards, lights), perceived spacing from above
    - Real-world example: Bollard placement on curved platform benefits from chord length
  - **Technical Notes**:
    - All 4 division functions updated with distance_measurement parameter
    - Chord length methods use PointsAtChordLengthFromPoint() for automatic iteration (avoids out-of-range errors)
    - Parameter tracking maintained for all methods for proper tangent rotation calculation
  - **Status**: ✅ All 8 combinations working (4 divide methods × 2 distance measurements)

- **v2.7** (February 2025): UI Control Alignment & Label Spacing
  - **Improved Label Display**:
    - Divide Distance label width increased to 230px to prevent text cutoff
    - All labels properly display without overlapping input controls
  - **Consistent Control Alignment**:
    - All input controls (textboxes, dropdown, radio buttons) aligned at x=260px
    - Divide Distance, Start Offset, End Offset textboxes all use x=260px, width 480px
    - Family Type dropdown positioned at x=260px, width 480px
    - Reverse Direction radio buttons aligned with input controls (True: x=260px, False: x=420px)
    - Family status label positioned below dropdown at matching x=260px
  - **Result**: Clean, professional layout with no text cutoff and perfect vertical alignment
  - **Status**: ✅ UI layout refinement complete

- **v2.6** (February 2025): Screen-Resolution-Aware UI Scaling
  - **Automatic Screen Detection**:
    - Detects primary monitor resolution at startup
    - Sets form size dynamically:
      - 4K (3840x2160): 800×1150px, 11pt font
      - 1440p (2560x1440): 760×1050px, 10.5pt font
      - 1080p (1920x1080): 720×950px, 10pt font
      - 720p (1280x720): 680×880px, 9.5pt font
    - Fallback to 750×1000px if detection fails
  - **Proportional Control Scaling**:
    - **scale() method** as class method for accessibility across all methods
    - **scale_factor** calculated as: form_width / 800 (reference base)
    - **All controls scale proportionally**:
      - Button and textbox sizes: width, height, position, spacing all scaled
      - Font sizes adjusted based on screen resolution for consistency
      - GroupBox dimensions and internal layouts scale proportionally
      - Divide Options group scaling and repositioning on visibility toggle
    - Ensures no overlapping or cramping on smaller screens
    - No UI text cutoff on any supported resolution
  - **Result**: UI perfectly fits 3840×2160 down to 1280×720 without manual resizing
  - **Status**: ✅ Multi-resolution support (4K, 1440p, 1080p, 720p)

- **v2.5** (February 2025): UI Enhancements & Revit 2021 Support
  - **Improved UI Layout**:
    - Form width increased from 650px to 800px
    - Form height increased from 720px to 1150px
    - Vertical spacing between sections increased (55-150px gaps)
    - Font sizes increased: Labels/Controls 11pt, Buttons 11pt Bold, GroupBox titles 11pt Bold
    - Font fallback chain: Segoe UI → Arial → Generic Sans Serif (for compatibility)
  - **Better Readability**:
    - All input fields and dropdowns widened to 520px
    - Control heights increased for better visibility
    - Status labels and unit indicators integrated into labels
    - Cleaner, less cramped dialog layout
  - **Autocomplete Search**:
    - Family Type dropdown now supports search/autocomplete
    - Type to filter family list in real-time
    - Families sorted alphabetically by name for easier navigation
    - AutoCompleteMode: SuggestAppend for instant suggestions
  - **Revit 2021 Compatibility**:
    - **ForceCloseTransaction()** at script start to clear stuck transactions
    - **close_open_transactions()** function for pre-transaction cleanup
    - **Enhanced error handling** with transaction status checks
    - Prevents "Starting a new transaction is not permitted" errors
    - Graceful fallback if transaction operations fail
  - **Status**: ✅ Full Revit 2021+ support with improved UI/UX

- **v2.4** (February 2025): Code cleanup and optimization
  - **Removed unused functions**: Deleted 9 helper functions that were no longer used
    - Removed: `flatten()`, `toList()`, `seqRange()`, `apply_reverse_if_needed()`, `join_curves_ordered()`, `find_parameter_for_distance()`, `get_arc_length_at_parameter()`, `get_curve_position_info()`, `place_family_with_rotation()`
  - **Simplified division logic**: All 4 combinations now use DesignScript PolyCurve directly
  - **Removed END option**: Only START and MIDDLE divide options remain (END was never implemented)
  - **Default to MIDDLE**: Divide Options now defaults to MIDDLE instead of START
  - **Cleaned imports**: Simplified Revit API imports, removed redundant explicit imports, removed try-except for StructuralType
  - **Status**: ✅ Cleaner, leaner code with same functionality

- **v2.3** (February 2025): Divide Options for Fixed Distance methods
  - **Fixed Distance + Total Length**: Now supports START and MIDDLE positioning
  - **Fixed Distance + Each Segment**: Now supports START and MIDDLE positioning
  - **UI Update**: Divide Options group appears for all Fixed Distance selections (Total Length or Each Segment)
  - **START Mode**: Places first point at curve start (0, distance, 2×distance, ...)
  - **MIDDLE Mode**: Balances start and end spacing with fixed intervals in middle
  - **For End-Based Placement**: Use Reverse Direction checkbox combined with START mode
  - **Status**: ✅ START and MIDDLE options implemented and working correctly

- **v2.2** (February 2025): All 4 combinations now use DesignScript PolyCurve
  - **Each Segment Methods**: Now use PolyCurve.ByJoinedCurves() → explode → trim → divide pattern
  - **Proper Curve Ordering**: PolyCurve ensures consistent direction for all segment methods
  - **Unified Approach**: All 4 combinations use DesignScript with consistent offset/reverse/divide flow
  - **PolyCurve.Curves()**: Explode method to get individual curves with proper direction
  - **Consistent Placement**: All methods use place_family_with_rotation_polycurve()
  - **Status**: ✅ All 4 combinations (Combinations 1, 2, 3, 4) fully working

- **v2.1** (February 2025): Total Length methods fixed with DesignScript PolyCurve
  - **DesignScript PolyCurve**: Total Length methods (Combinations 1 & 3) now use PolyCurve.ByJoinedCurves()
  - **Proper Offset Trimming**: ExtendStart/ExtendEnd for accurate curve reduction (replaces length subtraction)
  - **Reverse Direction**: Properly sequenced - reverse BEFORE offset trimming
  - **Unit Consistency**: All DesignScript calculations in mm with proper unit handling
  - **Tangent Calculations**: Total Length uses PolyCurve.TangentAtParameter() for accurate rotation
  - **Status**: ✅ Combinations 1 & 3 (both Total Length methods) fully working

- **v2.0** (February 2025): Complete rewrite with 4-combination logic
  - **New UI**: Separate controls for Divide Method and Segment grouping
  - **4 Combinations**: Maximum/Fixed Distance × Total Length/Each Segment
  - **Simplified Division**: All combinations divide from 0 → 1 of reduced curve
  - **Reverse Direction**: Controls division direction (reverses curve before dividing)
  - **No Reference Points**: Removed Start/Middle/End - direction handled by Reverse Direction toggle
  - **Maximum Method**: Smart floor/ceil algorithm for optimal equal spacing
  - **Fixed Distance**: Exact intervals with balanced last point
  - **Binary Search**: Accurate distance-based division for all curve types (lines, arcs, splines)
  - **MakeBound**: Uses Revit's native curve reduction API
  - **Millimeter Units**: All distances in mm (automatic conversion to internal units)
  - **Offset Logic**: Applied BEFORE division (reduces usable length)
  - **Improved Rotation**: Binary search for tangent calculation, proper axis rotation
  - **Better Error Handling**: Detailed error messages, graceful failure modes

- **v1.1** (January 2025): Bug fixes and debugging enhancements
  - Fixed StructuralType import from Autodesk.Revit.DB.Structure namespace
  - Fixed Font creation errors (now uses Arial with try-except fallback)
  - Added debug console output to selection process
  - Improved selection error handling with fallback mechanism
  - Better error messages and status feedback

- **v1.0** (January 2025): Initial release
  - Complete curve division system
  - Family placement with rotation
  - Windows Forms UI
  - Auto-ordering by connectivity
  - Multiple division methods

## Support & Customization

### Extending the Script

To customize, modify:

- **Division tolerance**: Change `tolerance=0.01` in `join_curves_ordered()`
- **Family filtering**: Edit `get_available_families()` to filter specific families
- **Rotation axis**: Change Z-axis to other directions in `place_family_with_rotation()`
- **UI layout**: Adjust font sizes, colors, and positions in `CurveDivisionDialog`

### Common Modifications

See commented sections in the script for guidance on:
- Changing dialog appearance
- Adding new division methods
- Implementing custom filtering
- Modifying rotation behavior

## License & Notes

This script is provided as-is for use with Autodesk Revit.

- Compatible with Revit 2023 and later
- Requires Python 3 in Dynamo
- Windows only (Windows Forms)
- No external dependencies beyond Revit API
