
from .classifier import Classifier
from .psth_new import EuclClassifier
from .random_classifier import RandomClassifier

classifier_map = {
    'eucl': EuclClassifier,
    'psth': EuclClassifier,
    'random': RandomClassifier,
}
