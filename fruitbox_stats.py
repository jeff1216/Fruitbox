import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fruitbox_stats.json")
_DEFAULT = {"wins": 0, "losses": 0, "ties": 0}


def load():
    try:
        with open(_PATH) as f:
            data = json.load(f)
        return {k: data.get(k, 0) for k in _DEFAULT}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULT)


def record(result):
    """result: 'win', 'loss', or 'tie'. Returns updated stats dict."""
    stats = load()
    stats[{"win": "wins", "loss": "losses", "tie": "ties"}[result]] += 1
    with open(_PATH, "w") as f:
        json.dump(stats, f)
    return stats
