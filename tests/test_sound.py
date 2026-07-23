from unittest.mock import MagicMock, patch

from src.utils.sound import play_sound


class TestPlaySound:
    def _capture_target_and_mock_ctypes(self, sound_path):
        with patch("src.utils.sound.threading.Thread") as mock_thread:
            play_sound(sound_path)
            _, kwargs = mock_thread.call_args
            target = kwargs["target"]
        mock_ctypes = MagicMock()
        mock_mci = mock_ctypes.windll.winmm.mciSendStringW
        return target, mock_mci, mock_ctypes

    def test_play_wav_opens_without_sequencer(self):
        target, mock_mci, mock_ctypes = self._capture_target_and_mock_ctypes("C:\\sound.wav")
        with patch("src.utils.sound.ctypes.windll", mock_ctypes.windll):
            target()
        calls = [c[0][0] for c in mock_mci.call_args_list]
        assert any('open "C:\\sound.wav" alias sound' in c for c in calls)
        assert not any("type sequencer" in c for c in calls)

    def test_play_mid_uses_sequencer(self):
        target, mock_mci, mock_ctypes = self._capture_target_and_mock_ctypes("C:\\sound.mid")
        with patch("src.utils.sound.ctypes.windll", mock_ctypes.windll):
            target()
        calls = [c[0][0] for c in mock_mci.call_args_list]
        assert any("type sequencer" in c for c in calls)
        assert any('open "C:\\sound.mid" alias sound type sequencer' in c for c in calls)

    def test_play_always_closes_sound(self):
        target, mock_mci, mock_ctypes = self._capture_target_and_mock_ctypes("C:\\any.wav")
        with patch("src.utils.sound.ctypes.windll", mock_ctypes.windll):
            target()
        calls = [c[0][0] for c in mock_mci.call_args_list]
        assert any(c == "close all" for c in calls)
        assert any(c == "close sound" for c in calls)

    def test_play_finally_closes_on_error(self):
        target, mock_mci, mock_ctypes = self._capture_target_and_mock_ctypes("C:\\error.wav")
        mock_mci.side_effect = RuntimeError("mci failed")
        with patch("src.utils.sound.ctypes.windll", mock_ctypes.windll):
            try:
                target()
            except RuntimeError:
                pass
        close_calls = [c for c in mock_mci.call_args_list if c[0][0] == "close sound"]
        assert len(close_calls) >= 1
