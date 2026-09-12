"""Export stored evidence for unreviewed real candidates; links are unverified search aids."""
import argparse
from pathlib import Path
import json
from urllib.parse import urlencode

from app import ml
from app.intelligence import sensor_evidence
from app.database import Detection, Session
from review_common import read_csv
from review_event_summary import load_event, render_summary

OUTPUT = ml.ROOT / 'data' / 'review_packets'


def render_packet(event, detections):
    lat, lon = event['latitude'], event['longitude']
    start = event['start_time'][:10]
    end = event['last_seen_time'][:10]
    sensors = sorted({f"{d.get('source', 'Unavailable')} / {d.get('satellite', 'Unavailable')} / {d.get('instrument', 'Unavailable')}" for d in detections})
    queries = [d.get('acquisition_query') for d in detections if d.get('acquisition_query')]
    terms = f'{lat:.4f} {lon:.4f} fire {start}'
    # Explicit whitelist prevents classification outputs and human labels from entering packets.
    evidence = {**sensor_evidence(detections), 'raw_observations': detections, 'detection_ids': event.get('detection_ids'), 'source_sensors': sensors,
                'provider_queries': queries, 'history': event.get('history'),
                'abnormality': (event.get('risk') or {}).get('abnormality'),
                'osm_satellite_context': event.get('context')}
    return ('# Review evidence: ' + event['id'] + '\n\n```text\n' + render_summary(event)
            + '\n```\n\n## Stored source and detailed context\n\n```json\n'
            + json.dumps(evidence, indent=2, ensure_ascii=False) + '\n```\n\n'
            + '## Potential evidence to verify manually\n\n'
            + 'These links and search terms are search aids, NOT verified incident evidence. '
              'A reviewer must inspect relevance, date, location, and source reliability.\n\n'
            + f'- Coordinates: {lat:.6f}, {lon:.6f}\n'
            + f'- [NASA FIRMS map](https://firms.modaps.eosdis.nasa.gov/map/#d:{start}..{end};@{lon},{lat},12z)\n'
            + f'- [OpenStreetMap location](https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=14/{lat}/{lon})\n'
            + '- [External incident/news search](https://www.google.com/search?' + urlencode({'q': terms}) + ')\n'
            + f'- Search terms: `{terms}`; optionally add a stored nearby facility name.\n')


def export_packets(candidates=ml.CANDIDATES, output=OUTPUT, session_factory=Session):
    _, rows, _ = read_csv(candidates)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    with session_factory() as db:
        for row in rows:
            if row.get('reviewed', '').strip().lower() != 'false':
                continue
            event = load_event(row['event_id'], db)
            detections = []
            for detection_id in event.get('detection_ids', []):
                item = db.get(Detection, detection_id)
                if item is None or item.is_demo or item.payload.get('is_demo') is not False:
                    raise ValueError('Missing or demo detection in event evidence: ' + event['id'])
                detections.append(item.payload)
            path = output / (event['id'] + '.md')
            content = render_packet(event, detections)
            if not path.exists() or path.read_text() != content:
                path.write_text(content)
            paths.append(path)
    # A manifest defines the current unreviewed set. Existing files are not deleted
    # because a human may have annotated them; old files are excluded from this index.
    (output / 'index.json').write_text(json.dumps({'unreviewed_packets': [p.name for p in paths],
                                                 'count': len(paths)}, indent=2))
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, default=ml.CANDIDATES)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    print(f'Exported {len(export_packets(args.candidates, args.output))} unreviewed evidence packets to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
