import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_grafana_dashboard_has_panels_for_all_trackb_metrics():
    dashboard = json.loads(
        (ROOT / 'services/trackb/grafana/dashboards/trackb-streaming.json').read_text(encoding='utf-8')
    )
    queries = [target['expr'] for panel in dashboard['panels'] for target in panel['targets']]
    required = (
        'trackb_messages_processed_total',
        'trackb_alerts_total',
        'trackb_e2e_latency_seconds_bucket',
        'trackb_consumer_lag',
        'trackb_rule_engine_errors_total',
    )
    assert all(any(metric in query for query in queries) for metric in required)
    assert all('event_id' not in query and 'reservoir_key' not in query for query in queries)
    assert dashboard['uid'] == 'twinguard-trackb-streaming'


def test_provisioning_is_credential_free_and_mount_sources_exist():
    datasource = ROOT / 'services/trackb/grafana/provisioning/datasources/trackb.yml'
    dashboards = ROOT / 'services/trackb/grafana/provisioning/dashboards/trackb.yml'
    prometheus = ROOT / 'services/trackb/prometheus.yml'
    for path in (datasource, dashboards, prometheus):
        assert path.is_file()
        body = path.read_text(encoding='utf-8').lower()
        assert 'password' not in body
        assert 'secret' not in body
    assert 'url: http://trackb-prometheus:9090' in datasource.read_text(encoding='utf-8')
    assert 'path: /var/lib/grafana/dashboards' in dashboards.read_text(encoding='utf-8')
    assert 'host.docker.internal:8000' in prometheus.read_text(encoding='utf-8')
