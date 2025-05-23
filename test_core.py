import unittest
from core import _convert_to_sequence_path # Assuming _convert_to_sequence_path is accessible

class TestConvertToSequencePath(unittest.TestCase):

    def test_non_sequence_based_on_fields(self):
        """Test case 1: Non-sequence (based on fields)"""
        fields = {"shot": "sh001"}
        path = "file.1234.exr"
        expected = "file.1234.exr"
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_is_sequence_primary_pattern_match(self):
        """Test case 2: Is sequence, primary pattern match (.####.)"""
        fields = {"frame": 101}
        path = "anim.1234.exr"
        expected = "anim.$F4.exr"
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_is_sequence_different_padding_primary_pattern(self):
        """Test case 3: Is sequence, different padding, primary pattern"""
        fields = {"SEQ": "frames"} # Using SEQ as a sequence indicator key
        path = "render.101.tif"
        expected = "render.$F4.tif"
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_is_sequence_fallback_pattern_match(self):
        """Test case 4: Is sequence, fallback pattern match (_####_)"""
        fields = {"nf": 1} # Using nf (net frames) as a sequence indicator
        path = "comp_v01_0075_stuff.png"
        expected = "comp_v01_$F4_stuff.png"
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_is_sequence_no_clear_frame_number_in_path(self):
        """Test case 5: Is sequence, no clear frame number in path"""
        fields = {"frame": 1}
        path = "static_image.jpg"
        expected = "static_image.jpg"
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_path_is_none(self):
        """Test case 6: Path is None"""
        fields = {"frame": 1}
        path = None
        expected = None
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_path_is_empty_string(self):
        """Test case 7: Path is empty string"""
        fields = {"frame": 1}
        path = ""
        expected = ""
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_primary_pattern_with_v_version_num_frame_ext(self):
        """Test case 8: Primary pattern with 'v' like version_num.frame.ext"""
        fields = {"frame": 1001}
        path = "model_v003.1001.abc"
        expected = "model_v003.$F4.abc"
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_fallback_pattern_with_v_and_underscore_multiple_numbers(self):
        """Test case 9: Fallback pattern with 'v' and underscore, multiple numbers"""
        fields = {"frame": 1}
        path = "fx_cache_v012_particles_1234_sim.bgeo.sc"
        # The fallback re.compile(r"([._v])(\d{2,})([._])") should match _1234_ first.
        # It matches "_particles_1234_sim" -> it will take group(1)="_", group(2)="1234", group(3)="_"
        # So it should become fx_cache_v012_particles_$F4_sim.bgeo.sc
        expected = "fx_cache_v012_particles_$F4_sim.bgeo.sc"
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_is_sequence_time_key_primary_pattern(self):
        """Additional Test: 'time' as sequence key, primary pattern"""
        fields = {"time": 1}
        path = "effect.0050.exr"
        expected = "effect.$F4.exr"
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_is_sequence_fallback_dot_frame_dot_ext(self):
        """Additional Test: Fallback for path.####.ext where primary might fail (e.g. if regex was too strict)"""
        # This test assumes the primary pattern \.(\d{2,})\. is working as intended.
        # If primary fails for some reason, this test would check if fallback catches it.
        # However, the current primary pattern is quite robust for .####.
        fields = {"frame": 1}
        path = "backup.v01.0001.png" # This should be caught by primary: ".0001."
        expected = "backup.v01.$F4.png"
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_no_numeric_group_in_fallback(self):
        """Additional Test: Fallback pattern target has no numbers"""
        fields = {"frame": 1}
        path = "my_file_vXX_setup.ma"
        expected = "my_file_vXX_setup.ma" # No change expected
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)
        
    def test_short_frame_number_primary(self):
        """Additional Test: Frame number with less than 2 digits (primary should not match by default \d{2,})"""
        fields = {"frame": 1}
        path = "test.1.exr"
        expected = "test.1.exr" # \d{2,} means 2 or more digits
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)

    def test_short_frame_number_fallback(self):
        """Additional Test: Frame number with less than 2 digits (fallback should not match by default \d{2,})"""
        fields = {"frame": 1}
        path = "test_v1_f1_comp.mov"
        expected = "test_v1_f1_comp.mov" # \d{2,} means 2 or more digits
        self.assertEqual(_convert_to_sequence_path(path, fields), expected)


if __name__ == '__main__':
    unittest.main()
```
