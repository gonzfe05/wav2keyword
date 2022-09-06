# AUTOGENERATED! DO NOT EDIT! File to edit: ../03_inference.ipynb.

# %% auto 0
__all__ = ['W2KInference']

# %% ../03_inference.ipynb 4
from typing import List, Callable
from nbdev.showdoc import *
from IPython.display import display, Audio
import numpy as np
from transformers import AutoModelForAudioClassification, TrainingArguments, Trainer
from datasets import load_metric
from datasets.dataset_dict import DatasetDict
from .datasets import dataloader_pipeline
from .preprocesses import Preprocessor
import torch

# %% ../03_inference.ipynb 6
class W2KInference(object):

    def __init__(self, model_checkpoint: str, id2label: dict, label2id: dict, metric: str = 'accuracy'):
        self.model_checkpoint = model_checkpoint
        print("loading metric")
        self.metric = load_metric(metric)
        self.preprocessor = Preprocessor(self.model_checkpoint)
        self.model = self._get_model(id2label, label2id)

    def _get_model(self, id2label: dict, label2id: dict):
        num_labels = len(id2label)
        model = AutoModelForAudioClassification.from_pretrained(
            self.model_checkpoint, 
            num_labels=num_labels,
            label2id=label2id,
            id2label=id2label,
        )
        return model
    
    def predict(self, datapoint):
        encoded_dataset = self.preprocessor.FEATURE_EXTRACTOR(datapoint, return_tensors="pt")
        with torch.no_grad():
            logits = self.model(**encoded_dataset).logits
        predicted_class_ids = torch.argmax(logits, dim=-1).numpy()
        return [self.model.config.id2label[str(c)] for c in predicted_class_ids]