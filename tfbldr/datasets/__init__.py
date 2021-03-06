from .loaders import rsync_fetch
from .loaders import fetch_iamondb
from .loaders import fetch_ljspeech
from .loaders import fetch_fruitspeech
from .loaders import fetch_mnist
from .loaders import fetch_fashion_mnist
from .loaders import make_sinewaves
from .iterators import list_iterator
from .iterators import ordered_list_iterator
from .iterators import tbptt_list_iterator
from .iterators import tbptt_file_list_iterator
from .iterators import char_textfile_iterator
from .audio import soundsc
from .audio import stft

# music21 and PIL are optional deps
try:
    from .plotters import save_image_array
    from .music import pitch_and_duration_to_piano_roll
    from .music import pitches_and_durations_to_pretty_midi
    from .music import quantized_to_pretty_midi
    from .music import plot_pitches_and_durations
    from .music import music21_to_pitch_duration
    from .music import music21_to_piano_roll
    from .music import plot_piano_roll
    from .music import piano_roll_imlike_to_image_array
    from .music import midi_to_notes
    from .music import notes_to_midi
    from .music import quantized_to_pitch_duration
except ImportError:
    pass
