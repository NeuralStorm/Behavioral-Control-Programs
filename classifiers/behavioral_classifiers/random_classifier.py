
from typing import List
from random import choice

from .classifier import Classifier

class RandomClassifier(Classifier):
    def __init__(self, choices: List[str]):
        self.choices = choices
    
    def classify(self) -> str:
        return choice(self.choices)
