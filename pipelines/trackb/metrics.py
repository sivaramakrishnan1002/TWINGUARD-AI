"""Bounded-cardinality Prometheus metrics for Track B streaming."""
from __future__ import annotations
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST, start_http_server
import math

METRIC_TOPICS=frozenset({'trackb.rain.v1','trackb.reservoir.v1','trackb.twin.v1','trackb.alerts.v1'})
METRIC_SOURCES=frozenset({'replay','live','simulated'})
METRIC_ALERT_LEVELS=frozenset({'Normal','Watch','Warning','Critical'})
METRIC_GROUPS=frozenset({'trackb-rule-engine'})
METRIC_ERROR_KINDS=frozenset({
    'not_object','unknown_schema','invalid_source','missing_common_field','invalid_timestamp',
    'invalid_event_id','invalid_provenance','missing_payload_field','invalid_alert_level',
    'invalid_confidence','invalid_validity','invalid_alert_payload','invalid_rain',
    'invalid_rain_metadata','invalid_qc_flags','invalid_storage','invalid_reservoir_value',
    'invalid_capacity','invalid_twin_reference','invalid_numeric_field','topic_schema_mismatch',
    'kafka_read','processing','invalid_received_at','lag_probe','invalid_json','other',
})

class TrackBMetrics:
    def __init__(self, registry:CollectorRegistry|None=None):
        self.registry=registry or CollectorRegistry(auto_describe=True)
        self.messages=Counter('trackb_messages_processed','Successfully processed messages',['topic','source'],registry=self.registry)
        self.alerts=Counter('trackb_alerts','Alert events by severity and source',['level','source'],registry=self.registry)
        self.latency=Histogram('trackb_e2e_latency_seconds','Time from event received_at to consumer processing',['source'],registry=self.registry,buckets=(.005,.01,.025,.05,.1,.25,.5,1,2.5,5,10))
        self.consumer_lag=Gauge('trackb_consumer_lag','Kafka records behind high watermark',['group','topic'],registry=self.registry)
        self.rule_errors=Counter('trackb_rule_engine_errors','Rule and message processing errors',['kind'],registry=self.registry)

    def exposition(self)->bytes:
        return generate_latest(self.registry)

    @staticmethod
    def _require(value:str,allowed:frozenset[str],name:str)->str:
        if not isinstance(value,str) or value not in allowed:raise ValueError(f'unsupported {name} metric label')
        return value

    def record_message(self,topic:str,source:str)->None:
        self.messages.labels(topic=self._require(topic,METRIC_TOPICS,'topic'),
                             source=self._require(source,METRIC_SOURCES,'source')).inc()

    def record_alert(self,level:str,source:str)->None:
        self.alerts.labels(level=self._require(level,METRIC_ALERT_LEVELS,'level'),
                           source=self._require(source,METRIC_SOURCES,'source')).inc()

    def observe_latency(self,source:str,seconds:float)->None:
        source=self._require(source,METRIC_SOURCES,'source')
        seconds=float(seconds)
        if not math.isfinite(seconds) or seconds<0:raise ValueError('latency must be finite and non-negative')
        self.latency.labels(source=source).observe(seconds)

    def set_consumer_lag(self,group:str,topic:str,lag:float)->None:
        group=self._require(group,METRIC_GROUPS,'group')
        topic=self._require(topic,METRIC_TOPICS,'topic')
        lag=float(lag)
        if not math.isfinite(lag) or lag<0:raise ValueError('consumer lag must be finite and non-negative')
        self.consumer_lag.labels(group=group,topic=topic).set(lag)

    def record_rule_error(self,kind:str)->None:
        # Unknown internal exception names collapse into one bounded bucket.
        bounded=kind if isinstance(kind,str) and kind in METRIC_ERROR_KINDS else 'other'
        self.rule_errors.labels(kind=bounded).inc()

    @property
    def content_type(self)->str:
        return CONTENT_TYPE_LATEST

    def serve(self,port:int=8000,address:str='127.0.0.1'):
        """Expose metrics on loopback by default; return server and thread."""
        if address!='127.0.0.1':
            raise ValueError('Track B metrics may only bind to loopback')
        return start_http_server(port,addr=address,registry=self.registry)
