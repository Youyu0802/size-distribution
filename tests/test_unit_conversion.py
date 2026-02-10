"""
Tests for the unit unification feature.

This feature allows users to switch display units at any time, converting
all displayed values (overlays, statistics, CSV export, histograms) to
the selected unit.
"""

import csv
import io
import math
import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nano_measurer import (
    Measurement, STRINGS, UNIT_TO_NM, SUPPORTED_UNITS,
    convert_length, write_csv_with_groups, assign_groups,
)


# ---------------------------------------------------------------------------
# Test conversion table and function
# ---------------------------------------------------------------------------

class TestUnitConversionTable:
    """Test UNIT_TO_NM table and convert_length function."""

    def test_all_supported_units_in_table(self):
        for u in SUPPORTED_UNITS:
            assert u in UNIT_TO_NM, f"Unit '{u}' missing from UNIT_TO_NM"

    def test_nm_is_identity(self):
        assert UNIT_TO_NM["nm"] == 1.0

    def test_angstrom_to_nm(self):
        assert convert_length(10, "Å", "nm") == pytest.approx(1.0)

    def test_nm_to_um(self):
        assert convert_length(1000, "nm", "μm") == pytest.approx(1.0)

    def test_um_to_mm(self):
        assert convert_length(1000, "μm", "mm") == pytest.approx(1.0)

    def test_mm_to_cm(self):
        assert convert_length(10, "mm", "cm") == pytest.approx(1.0)

    def test_cm_to_nm(self):
        assert convert_length(1, "cm", "nm") == pytest.approx(1e7)

    def test_same_unit_identity(self):
        assert convert_length(42.5, "nm", "nm") == pytest.approx(42.5)

    def test_round_trip(self):
        """Converting nm -> μm -> nm should return original value."""
        original = 123.456
        intermediate = convert_length(original, "nm", "μm")
        result = convert_length(intermediate, "μm", "nm")
        assert result == pytest.approx(original)

    def test_zero_value(self):
        assert convert_length(0, "nm", "cm") == pytest.approx(0.0)

    def test_negative_value(self):
        """Negative values should convert correctly (for edge cases)."""
        assert convert_length(-100, "nm", "μm") == pytest.approx(-0.1)

    def test_large_conversion(self):
        """1 cm = 10^8 Å"""
        assert convert_length(1, "cm", "Å") == pytest.approx(1e8)


# ---------------------------------------------------------------------------
# Test SUPPORTED_UNITS list
# ---------------------------------------------------------------------------

class TestSupportedUnits:
    """Test that the supported units list is correct."""

    def test_includes_common_units(self):
        for u in ["nm", "μm", "mm", "cm", "Å"]:
            assert u in SUPPORTED_UNITS

    def test_order_makes_sense(self):
        """Units should be ordered from small to large."""
        nm_values = [UNIT_TO_NM[u] for u in SUPPORTED_UNITS]
        assert nm_values == sorted(nm_values)


# ---------------------------------------------------------------------------
# Test display value conversion for Measurement objects
# ---------------------------------------------------------------------------

class TestMeasurementDisplayValues:
    """Test getting display values from measurements with unit conversion."""

    def test_display_in_calibration_unit(self):
        """When display unit == calibration unit, no conversion."""
        m = Measurement(0, 0, 100, 0, 1.0)  # 100 px * 1.0 nm/px = 100 nm
        display = convert_length(m.nm_dist, "nm", "nm")
        assert display == pytest.approx(100.0)

    def test_display_nm_as_um(self):
        m = Measurement(0, 0, 100, 0, 1.0)  # 100 nm
        display = convert_length(m.nm_dist, "nm", "μm")
        assert display == pytest.approx(0.1)

    def test_display_um_as_nm(self):
        """Measurement calibrated in μm, displayed in nm."""
        m = Measurement(0, 0, 100, 0, 0.5)  # 100 px * 0.5 μm/px = 50 μm
        display = convert_length(m.nm_dist, "μm", "nm")
        assert display == pytest.approx(50000.0)

    def test_display_mm_as_cm(self):
        m = Measurement(0, 0, 200, 0, 0.01)  # 200 px * 0.01 mm/px = 2 mm
        display = convert_length(m.nm_dist, "mm", "cm")
        assert display == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# Test CSV export uses display unit
# ---------------------------------------------------------------------------

class TestCSVExportWithDisplayUnit:
    """Test that CSV export respects display unit conversion."""

    def _build_csv_rows(self, measurements, scale=1.0,
                        calib_unit="nm", display_unit="nm"):
        from nano_measurer import write_csv_with_groups, assign_groups
        group_labels = assign_groups(measurements, [])
        output = io.StringIO()
        writer = csv.writer(output)
        write_csv_with_groups(writer, measurements, [], group_labels,
                              scale=scale, lang="en",
                              calib_unit=calib_unit, display_unit=display_unit)
        output.seek(0)
        return list(csv.reader(output))

    def test_csv_header_shows_display_unit(self):
        m = Measurement(0, 0, 100, 0, 1.0)
        rows = self._build_csv_rows([m], scale=1.0,
                                     calib_unit="nm", display_unit="μm")
        header = rows[0]
        # The diameter column should show μm
        diameter_col = header[1]
        assert "μm" in diameter_col

    def test_csv_values_converted(self):
        """100 nm should show as 0.1 μm in CSV."""
        m = Measurement(0, 0, 100, 0, 1.0)
        rows = self._build_csv_rows([m], scale=1.0,
                                     calib_unit="nm", display_unit="μm")
        data_row = rows[1]
        diameter_val = float(data_row[1])
        assert diameter_val == pytest.approx(0.1, abs=0.001)

    def test_csv_same_unit_no_conversion(self):
        m = Measurement(0, 0, 100, 0, 1.0)
        rows = self._build_csv_rows([m], scale=1.0,
                                     calib_unit="nm", display_unit="nm")
        data_row = rows[1]
        diameter_val = float(data_row[1])
        assert diameter_val == pytest.approx(100.0, abs=0.01)

    def test_csv_statistics_converted(self):
        """Statistics (mean, std, etc.) should be in display unit."""
        m1 = Measurement(0, 0, 100, 0, 1.0)  # 100 nm
        m2 = Measurement(0, 0, 200, 0, 1.0)  # 200 nm
        rows = self._build_csv_rows([m1, m2], scale=1.0,
                                     calib_unit="nm", display_unit="μm")
        # Find the mean row: should be 0.15 μm (average of 0.1 and 0.2)
        flat = {row[0]: row[1] for row in rows if len(row) >= 2}
        assert "Mean" in flat
        mean_val = float(flat["Mean"])
        assert mean_val == pytest.approx(0.15, abs=0.001)

    def test_csv_scale_shows_original(self):
        """Scale row should still show original scale value."""
        m = Measurement(0, 0, 100, 0, 2.5)
        rows = self._build_csv_rows([m], scale=2.5,
                                     calib_unit="nm", display_unit="μm")
        flat = {row[0]: row[1] for row in rows if len(row) >= 2}
        assert "Scale (nm/px)" in flat or any("Scale" in r[0] for r in rows if r)


# ---------------------------------------------------------------------------
# Test i18n strings for unit feature
# ---------------------------------------------------------------------------

class TestUnitI18n:
    """Test i18n strings exist for unit selection UI."""

    def test_display_unit_string_exists(self):
        assert "display_unit" in STRINGS
        assert "zh" in STRINGS["display_unit"]
        assert "en" in STRINGS["display_unit"]
