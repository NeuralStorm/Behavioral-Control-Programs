
import argparse
from pathlib import Path

from behavioral_classifiers.helpers import generate_template_main

from config import GameConfig

def parse_args(args):
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--config', required=True,
        help="")
    parser.add_argument('--events', required=True, type=Path,
        help="")
    parser.add_argument('--template-out', required=True, type=Path,
        help="")
    
    return parser.parse_args(args=args)

def gen_templates_main(args):
    args = parse_args(args)
    
    config = GameConfig(config_path=args.config, load_images=False)
    
    generate_template_main(
        config = config.classifier_config(),
        events_file = args.events,
        template_out = args.template_out,
    )
