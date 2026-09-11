"""Read-only evidence summary; never infer or recommend a class label."""
import argparse
import re
import sys

from sqlalchemy.exc import SQLAlchemyError
from app.database import Event, Session

CHECKLIST = (
    'Industrial facility context checked',
    'Historical persistence checked',
    'Agricultural/vegetation context checked',
    'Natural thermal explanation checked',
    'Possible false-positive explanation checked',
    'External source/reference collected',
    'Final class selected by reviewer',
)


def load_event(event_id, db=None):
    if not re.fullmatch(r'TG-[A-Za-z0-9_-]{1,120}', event_id):
        raise ValueError('Invalid event ID; expected an existing TG- event identifier')
    if db is None:
        with Session() as session:
            return load_event(event_id, session)
    item = db.get(Event, event_id)
    if item is None:
        raise ValueError(f'Event not found: {event_id}; it may have been reclustered')
    if item.is_demo or item.payload.get('is_demo') is not False:
        raise ValueError('Human training review requires a confirmed non-demo event')
    return item.payload


def display(value):
    if value is None or value == '':
        return 'Unavailable'
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    # Keep provider text from controlling terminal formatting.
    return ''.join(char if char.isprintable() else ' ' for char in str(value))


def render_summary(event):
    context = event.get('context') or {}
    history = event.get('history') or {}
    risk = event.get('risk') or {}
    abnormality = risk.get('abnormality') or {}
    lines = ['THERMAGUARD — HUMAN REVIEW EVIDENCE',
             'Stored evidence only. No class is suggested; the final label belongs to the reviewer.']

    def section(title, fields, source):
        lines.extend(['', title])
        lines.extend(f'  {key}: {display(source.get(key))}' for key in fields)

    section('Identity and observation aggregates (FRP: MW; brightness: K; duration: hours)',
            ['event_id', 'is_demo', 'latitude', 'longitude', 'start_time', 'last_seen_time',
             'detection_count', 'mean_frp', 'max_frp', 'mean_brightness', 'max_brightness',
             'persistence_days', 'duration_hours', 'night_fraction'],
            {**event, 'event_id': event.get('id')})
    section('Derived historical context',
            ['recurrence_count', 'historical_baseline_available', 'historical_mean_frp'], history)
    section('Historical abnormality — interpretation, not a class label',
            ['abnormality_score', 'abnormality_status', 'baseline_available'], abnormality)
    section('OSM context (distances: metres; missing tags do not establish absence)',
            ['osm_context_available', 'distance_to_industrial_m', 'distance_to_refinery_m',
             'distance_to_powerplant_m', 'distance_to_factory_m', 'distance_to_forest_m',
             'distance_to_farmland_m', 'distance_to_residential_m', 'nearby_industrial_count',
             'nearby_facility_count', 'landuse_class'], context)
    facilities = context.get('facilities') or []
    names = sorted({display(f['name']) for f in facilities if f.get('name')})
    lines.append('  nearby_facility_names: ' + ('; '.join(names) if names else 'Unavailable (no stored names)'))
    section('Satellite context (check acquisition time against event time)',
            ['satellite_context_available', 'ndvi', 'acquisition_date', 'land_cover'], context)
    section('Decision-support risk — not classification confidence', ['risk_score', 'risk_level'], risk)
    lines.extend(['', 'Evidence checklist:'] + [f'[ ] {item}' for item in CHECKLIST])
    lines.append('No checklist completion or review approval has been recorded by this summary.')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event_id')
    args = parser.parse_args(argv)
    try:
        print(render_summary(load_event(args.event_id)))
        return 0
    except ValueError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
    except SQLAlchemyError:
        print('ERROR: Unable to read the configured event database; check local configuration.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
