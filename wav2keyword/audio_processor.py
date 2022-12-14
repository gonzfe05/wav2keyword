# AUTOGENERATED! DO NOT EDIT! File to edit: ../07_audio_processor.ipynb.

# %% auto 0
__all__ = ['model_checkpoint', 'audio_processor', 'files', 'file', 'chunk_audio', 'export_audio', 'chunk_selected_audios',
           'align_force_align', 'parse_textgrid_items', 'parse_textgrid', 'AudioArray', 'AudioProcessor']

# %% ../07_audio_processor.ipynb 3
from glob import glob
import os
from joblib import Parallel, delayed
from pathlib import Path
from typing import List
from pydub import AudioSegment
import numpy as np
import subprocess
from praatio import textgrid, audio

def chunk_audio(audio: AudioSegment, increment_mills: int = 300, windows: int = 1000) -> List[AudioSegment]:
    sample_rate = audio.frame_count(ms=1000)
    seconds = audio.frame_count()/sample_rate
    def get_segment(e, window):
        return audio[e-windows:e]
    audio_segments = Parallel(n_jobs=4)(delayed(get_segment)(e, windows) for e in np.arange(windows, seconds*1000, increment_mills))
    return audio_segments

def export_audio(segment: AudioSegment, path: str):
    return segment.export(f'{path}.wav', format="wav")

def chunk_selected_audios(audios: List[str], output_path: str) -> None:
    Path(output_path).mkdir(parents=True, exist_ok=True)
    for file in audios:
        audio = AudioSegment.from_wav(file)
        for ix, segment in enumerate(chunk_audio(audio)):
            path = os.path.join(output_path, f"{Path(file).stem}_{ix}.wav")
            export_audio(segment, path)

def align_force_align(corpus_directory: str, output_directory: str):
    dictionary = 'english_us_arpa'
    acoustic_model = 'english_us_arpa'
    return subprocess.run(["mfa", "align", corpus_directory, dictionary, acoustic_model, output_directory], capture_output=True)

def parse_textgrid_items(items: List[tuple], duration_seconds):
    for ix, (k, v) in enumerate(items):
        if 'phones' in k:
            continue
        for s, e, t in v.entryList:
            start = max(s-0.1, 0)*1000
            end = min(e+0.1, duration_seconds)*1000
            yield start, end, t 

def parse_textgrid(corpus_directory: str, output_directory: str):
    grids = glob(os.path.join(output_directory, '*.TextGrid'))
    assert len(grids) == 1, f"{grids}"
    grid = grids[0]
    name = Path(grid).stem
    tg = textgrid.openTextgrid(grid, includeEmptyIntervals=False)
    audio = AudioSegment.from_wav(os.path.join(corpus_directory, f"{name}.wav"))
    parsed = [(s, e, t) for s, e, t in parse_textgrid_items(tg.tierDict.items(), audio.duration_seconds)]
    audios = [audio[start:end] for start, end, _ in parsed]
    transcriptions = [trans for _, _, trans in parsed]
    return audios, transcriptions

# %% ../07_audio_processor.ipynb 5
import shutil
from typing import List
from collections import Counter
from transformers import AutoFeatureExtractor
from transformers import Wav2Vec2ForXVector, TrainingArguments, Trainer
from datasets import load_dataset, load_metric
import pandas as pd
from pathlib import Path
import torch
from numpy.typing import NDArray
from pydantic import BaseModel
from io import BytesIO
from glob import glob
from random import choices

class AudioArray(BaseModel):
    array: np.ndarray
    class Config:
        arbitrary_types_allowed = True

class AudioProcessor(object):

    def __init__(self, model_checkpoint: str) -> None:
        self.model_checkpoint = model_checkpoint
        self.feature_extractor = AutoFeatureExtractor.from_pretrained(self.model_checkpoint)
    
    def preprocess_function(self, audio_arrays: List[AudioArray], max_duration: float = 1.0):
        arrays = [a.array for a in audio_arrays]
        inputs = self.feature_extractor(
            arrays,
            sampling_rate=self.feature_extractor.sampling_rate, 
            max_length=int(self.feature_extractor.sampling_rate * max_duration),
            truncation=True,
            return_tensors="pt",
            padding=True
            )
        return inputs
    
    def parse_raw_audio(self, raw_data: bytes, sample_width: int, channels: int, frame_rate: int) -> List[AudioSegment]:
        audio = AudioSegment.from_raw(
            BytesIO(raw_data), 
            sample_width=sample_width,
            channels=channels,
            frame_rate=frame_rate
        )
        return [segment for segment in chunk_audio(audio)]
    
    def encode_raw_audio(self, raw_data: bytes, sample_width: int, channels: int, frame_rate: int):
        parsed = self.parse_raw_audio(raw_data, sample_width, channels, frame_rate)
        parsed = [{'array': np.array(p.get_array_of_samples(), dtype=float)} for p in parsed]
        parsed = [AudioArray.parse_obj(p) for p in parsed]
        return self.preprocess_function(parsed)
    
    def parse_aligned_audio(self, corpus_directory: str):
        output_directory = os.path.join(Path.home(), '.cache/mfa/')
        mfa_output = align_force_align(corpus_directory, output_directory)
        audios, transcriptions = parse_textgrid(corpus_directory, output_directory)
        return audios, transcriptions
    
    def encode_aligned_audio(self, corpus_directory: str):
        parsed, self.transcriptions = self.parse_aligned_audio(corpus_directory)
        parsed = [{'array': np.array(p.get_array_of_samples(), dtype=float)} for p in parsed]
        parsed = [AudioArray.parse_obj(p) for p in parsed]
        return self.preprocess_function(parsed)
    



model_checkpoint = 'data/panda/wav2vec2-base-finetuned-xvector/best_checkpoint/'
audio_processor = AudioProcessor(model_checkpoint)

files = glob(f'{Path.home()}/.cache/panda/audios/*.wav')
file = choices(files, k=1)[0]

AudioSegment.from_wav(file)
