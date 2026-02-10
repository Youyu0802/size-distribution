"""
Tests for measurement grouping feature.

The grouping feature allows users to draw rectangles on the image to define
groups. Measurements whose midpoints fall within a group rectangle are assigned
to that group. CSV export includes group info for each measurement and
per-group statistics.
"""

import csv
import io
import math
import sys
import os

import numpy as np
import pytest

# Add parent directory to path so we can import nano_measurer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nano_measurer import Measurement, STRINGS


# ---------------------------------------------------------------------------
# Helper: build a Group object
# ---------------------------------------------------------------------------

def _make_measurement(x1, y1, x2, y2, scale=1.0):
    return Measurement(x1, y1, x2, y2, scale)


# ---------------------------------------------------------------------------
# Test Group data class
# ---------------------------------------------------------------------------

class TestGroupDataClass:
    """Test the MeasurementGroup data structure."""

    def test_group_creation(self):
        from nano_measurer import MeasurementGroup
        g = MeasurementGroup("Group 1", 10, 20, 100, 200)
        assert g.name == "Group 1"
        assert g.x1 == 10
        assert g.y1 == 20
        assert g.x2 == 100
        assert g.y2 == 200

    def test_group_contains_midpoint_inside(self):
        from nano_measurer import MeasurementGroup
        g = MeasurementGroup("G1", 0, 0, 100, 100)
        # Measurement with midpoint at (50, 50) — inside
        m = _make_measurement(40, 40, 60, 60)
        assert g.contains_measurement(m) is True

    def test_group_contains_midpoint_outside(self):
        from nano_measurer import MeasurementGroup
        g = MeasurementGroup("G1", 0, 0, 100, 100)
        # Measurement with midpoint at (150, 150) — outside
        m = _make_measurement(140, 140, 160, 160)
        assert g.contains_measurement(m) is False

    def test_group_contains_midpoint_on_boundary(self):
        from nano_measurer import MeasurementGroup
        g = MeasurementGroup("G1", 0, 0, 100, 100)
        # Measurement with midpoint at (100, 50) — on boundary, should be included
        m = _make_measurement(100, 40, 100, 60)
        assert g.contains_measurement(m) is True

    def test_group_with_inverted_coordinates(self):
        """Group defined with x2 < x1 or y2 < y1 should still work."""
        from nano_measurer import MeasurementGroup
        g = MeasurementGroup("G1", 100, 100, 0, 0)
        m = _make_measurement(40, 40, 60, 60)  # midpoint (50, 50)
        assert g.contains_measurement(m) is True

    def test_group_contains_partial_overlap(self):
        """Measurement line crosses group boundary, but midpoint is inside."""
        from nano_measurer import MeasurementGroup
        g = MeasurementGroup("G1", 40, 40, 80, 80)
        # Midpoint at (50, 50) — inside, but endpoints span outside
        m = _make_measurement(10, 50, 90, 50)
        assert g.contains_measurement(m) is True

    def test_group_midpoint_outside_despite_endpoint_inside(self):
        """One endpoint inside group, but midpoint outside."""
        from nano_measurer import MeasurementGroup
        g = MeasurementGroup("G1", 0, 0, 30, 30)
        # midpoint at (40, 15), x1=10 is inside but midpoint is not
        m = _make_measurement(10, 15, 70, 15)
        assert g.contains_measurement(m) is False


# ---------------------------------------------------------------------------
# Test group assignment logic
# ---------------------------------------------------------------------------

class TestGroupAssignment:
    """Test assigning measurements to groups."""

    def test_assign_measurement_to_single_group(self):
        from nano_measurer import MeasurementGroup, assign_groups
        groups = [MeasurementGroup("G1", 0, 0, 100, 100)]
        measurements = [_make_measurement(40, 40, 60, 60)]
        result = assign_groups(measurements, groups)
        assert result == ["G1"]

    def test_measurement_in_no_group(self):
        from nano_measurer import MeasurementGroup, assign_groups
        groups = [MeasurementGroup("G1", 0, 0, 50, 50)]
        measurements = [_make_measurement(80, 80, 90, 90)]
        result = assign_groups(measurements, groups)
        assert result == [""]

    def test_multiple_groups(self):
        from nano_measurer import MeasurementGroup, assign_groups
        groups = [
            MeasurementGroup("G1", 0, 0, 100, 100),
            MeasurementGroup("G2", 200, 200, 300, 300),
        ]
        m1 = _make_measurement(40, 40, 60, 60)   # midpoint (50, 50) -> G1
        m2 = _make_measurement(240, 240, 260, 260)  # midpoint (250, 250) -> G2
        m3 = _make_measurement(150, 150, 170, 170)  # midpoint (160, 160) -> none
        result = assign_groups([m1, m2, m3], groups)
        assert result == ["G1", "G2", ""]

    def test_measurement_in_overlapping_groups(self):
        """When a measurement falls in multiple groups, it gets the first match."""
        from nano_measurer import MeasurementGroup, assign_groups
        groups = [
            MeasurementGroup("G1", 0, 0, 100, 100),
            MeasurementGroup("G2", 50, 50, 150, 150),
        ]
        m = _make_measurement(70, 70, 80, 80)  # midpoint (75, 75) -> in both
        result = assign_groups([m], groups)
        assert result == ["G1"]  # first match

    def test_empty_measurements_list(self):
        from nano_measurer import MeasurementGroup, assign_groups
        groups = [MeasurementGroup("G1", 0, 0, 100, 100)]
        result = assign_groups([], groups)
        assert result == []

    def test_empty_groups_list(self):
        from nano_measurer import assign_groups
        measurements = [_make_measurement(40, 40, 60, 60)]
        result = assign_groups(measurements, [])
        assert result == [""]

    def test_many_measurements_many_groups(self):
        from nano_measurer import MeasurementGroup, assign_groups
        groups = [
            MeasurementGroup("A", 0, 0, 50, 50),
            MeasurementGroup("B", 60, 60, 110, 110),
            MeasurementGroup("C", 120, 120, 170, 170),
        ]
        measurements = [
            _make_measurement(20, 20, 30, 30),   # midpoint (25, 25) -> A
            _make_measurement(70, 70, 80, 80),   # midpoint (75, 75) -> B
            _make_measurement(130, 130, 140, 140),  # midpoint (135, 135) -> C
            _make_measurement(200, 200, 210, 210),  # midpoint (205, 205) -> none
        ]
        result = assign_groups(measurements, groups)
        assert result == ["A", "B", "C", ""]


# ---------------------------------------------------------------------------
# Test CSV export with group information
# ---------------------------------------------------------------------------

class TestCSVExportWithGroups:
    """Test that CSV export includes group information."""

    def _build_csv_rows(self, measurements, groups, scale=1.0):
        """Helper to generate CSV rows using the export logic."""
        from nano_measurer import assign_groups, write_csv_with_groups
        group_labels = assign_groups(measurements, groups)
        output = io.StringIO()
        writer = csv.writer(output)
        write_csv_with_groups(writer, measurements, groups, group_labels,
                              scale=scale, lang="en")
        output.seek(0)
        return list(csv.reader(output))

    def test_csv_has_group_column(self):
        from nano_measurer import MeasurementGroup
        groups = [MeasurementGroup("G1", 0, 0, 100, 100)]
        measurements = [_make_measurement(40, 40, 60, 60)]
        rows = self._build_csv_rows(measurements, groups)
        header = rows[0]
        assert "Group" in header

    def test_csv_group_label_present(self):
        from nano_measurer import MeasurementGroup
        groups = [MeasurementGroup("G1", 0, 0, 100, 100)]
        measurements = [_make_measurement(40, 40, 60, 60)]
        rows = self._build_csv_rows(measurements, groups)
        # First data row (row index 1)
        data_row = rows[1]
        assert "G1" in data_row

    def test_csv_ungrouped_measurement(self):
        from nano_measurer import MeasurementGroup
        groups = [MeasurementGroup("G1", 0, 0, 50, 50)]
        measurements = [_make_measurement(80, 80, 90, 90)]
        rows = self._build_csv_rows(measurements, groups)
        data_row = rows[1]
        group_col_idx = rows[0].index("Group")
        assert data_row[group_col_idx] == ""

    def test_csv_multiple_groups_statistics(self):
        """CSV should have per-group statistics sections."""
        from nano_measurer import MeasurementGroup
        groups = [
            MeasurementGroup("G1", 0, 0, 100, 100),
            MeasurementGroup("G2", 200, 200, 300, 300),
        ]
        measurements = [
            _make_measurement(40, 40, 60, 60),
            _make_measurement(45, 45, 65, 65),
            _make_measurement(240, 240, 260, 260),
        ]
        rows = self._build_csv_rows(measurements, groups)
        flat = [cell for row in rows for cell in row]
        assert "G1" in flat
        assert "G2" in flat

    def test_csv_no_groups_still_works(self):
        """When no groups are defined, CSV should still export normally."""
        measurements = [_make_measurement(40, 40, 60, 60)]
        rows = self._build_csv_rows(measurements, [], scale=1.0)
        assert len(rows) > 1  # At least header + 1 data row

    def test_csv_group_statistics_values(self):
        """Group statistics should have correct count."""
        from nano_measurer import MeasurementGroup
        groups = [MeasurementGroup("G1", 0, 0, 100, 100)]
        measurements = [
            _make_measurement(20, 20, 30, 30),
            _make_measurement(40, 40, 50, 50),
            _make_measurement(60, 60, 70, 70),
        ]
        rows = self._build_csv_rows(measurements, groups)
        flat = [cell for row in rows for cell in row]
        # All 3 measurements are in G1
        assert "3" in flat


# ---------------------------------------------------------------------------
# Test i18n strings for grouping
# ---------------------------------------------------------------------------

class TestGroupI18n:
    """Test that grouping i18n strings exist in both languages."""

    def test_group_strings_exist(self):
        required_keys = [
            "group_select", "group_name_prompt", "group_hint",
            "csv_group",
        ]
        for key in required_keys:
            assert key in STRINGS, f"Missing i18n key: {key}"
            assert "zh" in STRINGS[key], f"Missing zh for: {key}"
            assert "en" in STRINGS[key], f"Missing en for: {key}"
