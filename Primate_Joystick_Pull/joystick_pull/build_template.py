
from pathlib import Path

import behavioral_classifiers
from behavioral_classifiers import Classifier, EventsFileWriter

outp = Path('./output')
classifier_events_path = outp / 'test_classifier_events.json'
template_out_path = outp / 'test_templates.json'
event_class = 'homezone_enter'


behavioral_classifiers.eucl_classifier.build_templates_from_new_events_file(
    events_path = classifier_events_path,
    template_path = template_out_path,
    event_class = event_class,
    post_time = 200,
    bin_size = 20,
)
