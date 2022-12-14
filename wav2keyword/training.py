# AUTOGENERATED! DO NOT EDIT! File to edit: ../02_training.ipynb.

# %% auto 0
__all__ = ['TRAINING_ARGS', 'W2KTrainer']

# %% ../02_training.ipynb 4
from typing import List, Callable
from nbdev.showdoc import *
from IPython.display import display,SVG
import numpy as np
from transformers import AutoModelForAudioClassification, TrainingArguments, Trainer
from datasets import load_metric
from datasets.dataset_dict import DatasetDict
from .datasets_tools import dataloader_pipeline
from .preprocesses import Preprocessor

# %% ../02_training.ipynb 6
TRAINING_ARGS = {
        'evaluation_strategy': "epoch",
        'save_strategy': "epoch",
        'learning_rate': 3e-5,
        'per_device_train_batch_size': 32,
        'gradient_accumulation_steps': 4,
        'per_device_eval_batch_size': 32,
        'num_train_epochs': 5,
        'warmup_ratio': 0.1,
        'logging_steps': 10,
        'load_best_model_at_end': True,
        'metric_for_best_model': "accuracy",
        'push_to_hub': False}

class W2KTrainer(object):

    def __init__(self, model_checkpoint: str = "facebook/wav2vec2-base", metric: str = 'accuracy'):
        self.model_checkpoint = model_checkpoint
        self.model_name = model_checkpoint.split("/")[-1]
        self.training_args = TRAINING_ARGS
        self.training_args['output_dir'] = f"{self.model_name}-finetuned-ks"
        print("loading metric")
        self.metric = load_metric(metric)
        self.preprocessor = Preprocessor(self.model_checkpoint)

    def _get_model(self, id2label: dict, label2id: dict):
        num_labels = len(id2label)
        model = AutoModelForAudioClassification.from_pretrained(
            self.model_checkpoint, 
            num_labels=num_labels,
            label2id=label2id,
            id2label=id2label,
        )
        return model

    def get_training_args(self, training_kwargs = None):
        training_args = self.training_args.copy()
        if training_kwargs:
            for k, v in training_kwargs.items():
                training_args[k] = v

        args = TrainingArguments(
            **training_args
        )
        return args

    def _compute_metrics(self, eval_pred):
        """Computes accuracy on a batch of predictions"""
        predictions = np.argmax(eval_pred.predictions, axis=1)
        return self.metric.compute(predictions=predictions, references=eval_pred.label_ids)

    def build_trainer(self, dataset, id2label, label2id, args = None, preprocess_kwargs: dict = {'max_duration': 1.0}):
        encoded_dataset = self.preprocessor.preprocess(dataset, fn_kwargs = preprocess_kwargs)
        trainer = Trainer(
            self._get_model(id2label, label2id),
            self.get_training_args(args),
            train_dataset=encoded_dataset["train"],
            eval_dataset=encoded_dataset["validation"],
            tokenizer=self.preprocessor.FEATURE_EXTRACTOR,
            compute_metrics=self._compute_metrics
        )
        return trainer
