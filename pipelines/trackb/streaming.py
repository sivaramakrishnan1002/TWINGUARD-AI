"""Kafka/Redis replay streaming primitives for Track B.

Only the four versioned Track B event schemas are accepted. Malformed events are
sent to a metadata-only dead-letter topic; raw payloads and credentials are
never logged or copied to logs.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo
import json
import time as clock

import pandas as pd
from .analysis import RuleThresholds, load_observations, rule_alert
from .metrics import TrackBMetrics

SOURCE_VALUES={'replay','live','simulated'}
TOPIC_BY_SCHEMA={
    'trackb.rain_update.v1':'trackb.rain.v1',
    'trackb.reservoir_update.v1':'trackb.reservoir.v1',
    'trackb.twin_update.v1':'trackb.twin.v1',
    'trackb.alert.v1':'trackb.alerts.v1',
}
PRIMARY_TOPICS=tuple(TOPIC_BY_SCHEMA.values())
DEAD_LETTER_TOPIC='trackb.deadletter.v1'

@dataclass(frozen=True)
class TopicSpec:
    name:str
    partitions:int
    retention_days:int

TOPIC_SPECS=(
    TopicSpec('trackb.rain.v1',3,30),
    TopicSpec('trackb.reservoir.v1',3,90),
    TopicSpec('trackb.twin.v1',1,30),
    TopicSpec('trackb.alerts.v1',1,365),
    TopicSpec(DEAD_LETTER_TOPIC,1,7),
)

class InvalidEvent(ValueError):
    def __init__(self,kind:str,message:str):
        super().__init__(message); self.kind=kind


def validate_event(event:dict[str,Any])->None:
    if not isinstance(event,dict): raise InvalidEvent('not_object','event must be a JSON object')
    schema=event.get('schema')
    if schema not in TOPIC_BY_SCHEMA: raise InvalidEvent('unknown_schema','unsupported schema')
    if event.get('source') not in SOURCE_VALUES: raise InvalidEvent('invalid_source','source is not allowed')
    for key in ('event_id','observed_at','received_at','provenance'):
        if key not in event: raise InvalidEvent('missing_common_field',f'missing {key}')
    try:
        observed=datetime.fromisoformat(str(event['observed_at']).replace('Z','+00:00'))
        received=datetime.fromisoformat(str(event['received_at']).replace('Z','+00:00'))
    except (ValueError,TypeError) as exc: raise InvalidEvent('invalid_timestamp','timestamps must be ISO-8601') from exc
    if observed.tzinfo is None or received.tzinfo is None:
        raise InvalidEvent('invalid_timestamp','timestamps must include a timezone')
    if not isinstance(event.get('event_id'),str) or not event['event_id'].strip():
        raise InvalidEvent('invalid_event_id','event_id must be a non-empty string')
    if not isinstance(event.get('provenance'),dict):
        raise InvalidEvent('invalid_provenance','provenance must be an object')
    required={
        'trackb.rain_update.v1':('location_key','value','unit','period_seconds','qc_flags'),
        'trackb.reservoir_update.v1':('reservoir_key','storage_value','storage_unit','capacity_value','capacity_unit','release_value','release_unit','qc_flags'),
        'trackb.twin_update.v1':('run_id','state_ref','recompute_marker_key'),
        'trackb.alert.v1':('reservoir_key','level','confidence','valid_from','valid_to','rule_version','trigger_inputs','target'),
    }[schema]
    missing=[key for key in required if key not in event]
    if missing: raise InvalidEvent('missing_payload_field','required payload field absent')
    try:
        if schema=='trackb.alert.v1':
            if event['level'] not in {'Normal','Watch','Warning','Critical'}:
                raise InvalidEvent('invalid_alert_level','alert level is invalid')
            confidence=float(event['confidence'])
            if not 0<=confidence<=1: raise InvalidEvent('invalid_confidence','confidence must be between 0 and 1')
            valid_from=datetime.fromisoformat(str(event['valid_from']).replace('Z','+00:00'))
            valid_to=datetime.fromisoformat(str(event['valid_to']).replace('Z','+00:00'))
            if valid_from.tzinfo is None or valid_to.tzinfo is None or valid_to<=valid_from:
                raise InvalidEvent('invalid_validity','alert validity interval must be timezone-aware and increasing')
            if not isinstance(event['trigger_inputs'],dict) or not isinstance(event['target'],dict):
                raise InvalidEvent('invalid_alert_payload','trigger_inputs and target must be objects')
        elif schema=='trackb.rain_update.v1':
            if event['value'] is not None and (not _finite_number(event['value']) or float(event['value'])<0):
                raise InvalidEvent('invalid_rain','rainfall must be a finite non-negative number or null')
            if not isinstance(event['unit'],str) or not _finite_number(event['period_seconds']) or float(event['period_seconds'])<=0:
                raise InvalidEvent('invalid_rain_metadata','rainfall unit and positive period_seconds are required')
            if not isinstance(event['qc_flags'],list): raise InvalidEvent('invalid_qc_flags','qc_flags must be an array')
        elif schema=='trackb.reservoir_update.v1':
            if not _finite_number(event['storage_value']) or float(event['storage_value'])<0:
                raise InvalidEvent('invalid_storage','storage must be a finite non-negative number')
            for name in ('capacity_value','release_value','rainfall_mm','rain_3d_mm','rise_1d_pct','rise_3d_pct'):
                if event.get(name) is not None and not _finite_number(event[name]):
                    raise InvalidEvent('invalid_reservoir_value',f'{name} must be finite or null')
            if event['capacity_value'] is not None and float(event['capacity_value'])<=0:
                raise InvalidEvent('invalid_capacity','capacity must be positive or null')
            if not isinstance(event['qc_flags'],list): raise InvalidEvent('invalid_qc_flags','qc_flags must be an array')
        elif schema=='trackb.twin_update.v1':
            if not all(isinstance(event[name],str) and event[name].strip() for name in ('run_id','state_ref','recompute_marker_key')):
                raise InvalidEvent('invalid_twin_reference','twin references must be non-empty strings')
    except (ValueError,TypeError,OverflowError) as exc:
        raise InvalidEvent('invalid_numeric_field','numeric event fields must be finite numbers') from exc


def _finite_number(value:Any)->bool:
    try:
        return pd.notna(value) and float(value)==float(value) and abs(float(value))!=float('inf')
    except (ValueError,TypeError,OverflowError):
        return False


def event_key(event:dict[str,Any])->str:
    for key in ('reservoir_key','location_key','run_id'):
        if event.get(key) is not None:return str(event[key])
    return str(event['event_id'])


def topic_for_event(event:dict[str,Any])->str:
    validate_event(event)
    return TOPIC_BY_SCHEMA[event['schema']]


def ensure_topics(admin:Any,timeout:float=15)->None:
    """Create the declared topics idempotently; reject incompatible existing layouts."""
    from confluent_kafka.admin import NewTopic, ConfigResource, ResourceType
    metadata=admin.list_topics(timeout=timeout)
    existing=metadata.topics
    missing=[spec for spec in TOPIC_SPECS if spec.name not in existing]
    if missing:
        futures=admin.create_topics([NewTopic(spec.name,num_partitions=spec.partitions,replication_factor=1,
            config={'retention.ms':str(spec.retention_days*86400*1000)}) for spec in missing],operation_timeout=timeout)
        for name,future in futures.items():
            try: future.result()
            except Exception as exc:
                # Concurrent startup can race topic creation. Re-list and validate below.
                latest=admin.list_topics(timeout=timeout).topics
                if name not in latest: raise RuntimeError(f'Kafka topic creation failed: {name}') from exc
    metadata=admin.list_topics(timeout=timeout); existing=metadata.topics
    for spec in TOPIC_SPECS:
        if spec.name not in existing: raise RuntimeError(f'Kafka topic missing after creation: {spec.name}')
        if len(existing[spec.name].partitions)!=spec.partitions:
            raise RuntimeError(f'Kafka topic has unexpected partition count: {spec.name}')
    resources=[ConfigResource(ResourceType.TOPIC,s.name) for s in TOPIC_SPECS]
    described=admin.describe_configs(resources,request_timeout=timeout)
    by_name={resource.name:future.result() for resource,future in described.items()}
    for spec in TOPIC_SPECS:
        config=by_name[spec.name]
        configured=config.get('retention.ms')
        value=getattr(configured,'value',configured)
        if str(value)!=str(spec.retention_days*86400*1000):
            raise RuntimeError(f'Kafka topic has unexpected retention: {spec.name}')


class KafkaJSONProducer:
    def __init__(self,producer:Any):
        self.producer=producer; self._delivery_errors=[]; self.delivered_count=0
    def send(self,event:dict[str,Any])->None:
        self.send_payload(topic_for_event(event),event,event_key(event))
    def send_payload(self,topic:str,event:dict[str,Any],key:str|bytes)->None:
        payload=json.dumps(event,separators=(',',':'),allow_nan=False).encode('utf-8')
        key=key.encode('utf-8') if isinstance(key,str) else key
        def delivered(error:Any,_message:Any)->None:
            if error is not None:self._delivery_errors.append(True)
            else:self.delivered_count+=1
        while True:
            try:
                self.producer.produce(topic,key=key,value=payload,on_delivery=delivered)
                break
            except BufferError:
                self.producer.poll(1)
        self.producer.poll(0)
    def flush(self,timeout:float=30)->int:
        remaining=self.producer.flush(timeout)
        if remaining:raise TimeoutError(f'{remaining} Kafka messages were not delivered')
        if self._delivery_errors:
            self._delivery_errors.clear()
            raise RuntimeError('Kafka delivery failed')
        return remaining


class TrackBPersistenceAdapter:
    """Opt-in adapter for an explicitly supplied, migration-ready connection.

    No database connection is created by the default consumer. Supply a
    connection to a dedicated test database only after migration 100 is applied.
    """
    def __init__(self,connection:Any,run_id:int):
        self.connection=connection; self.run_id=run_id
    def write_alert(self,event:dict)->Any:
        from .persistence import write_alert
        return write_alert(self.connection,event)
    def write_state(self,event:dict)->Any:
        from .persistence import write_reservoir_state
        return write_reservoir_state(self.connection,self.run_id,event)


def make_replay_events(repo_root:Path,start:str,end:str,run_id:str|None=None)->Iterable[dict[str,Any]]:
    """Yield source-backed replay messages in reservoir-key/event-time order."""
    if end<start:raise ValueError('end must not precede start')
    df,_,_=load_observations(repo_root)
    archive=repo_root/'data/raw/reservoirs/kaggle_chennai_water_management/archive.zip'
    digest=sha256(archive.read_bytes()).hexdigest()
    subset=df[(df.date>=start)&(df.date<=end)].sort_values(['date','reservoir'])
    received=datetime.now().astimezone().isoformat()
    for row in subset.itertuples(index=False):
        observed=datetime.combine(pd.Timestamp(row.date).date(),time.min,tzinfo=ZoneInfo('Asia/Kolkata')).isoformat()
        provenance={'source_id':'Kaggle Chennai Water Management','source_file':'data/raw/reservoirs/kaggle_chennai_water_management/archive.zip',
                    'source_sha256':digest,'date_timezone':'Asia/Kolkata','timezone_status':'DEFAULT, to confirm',
                    'rainfall_unit_status':'INFERRED; original unit unspecified'}
        if run_id is not None:provenance['replay_run_id']=run_id
        reservoir=row.reservoir.upper()
        suffix=f':run:{run_id}' if run_id is not None else ''
        yield {'schema':'trackb.rain_update.v1','event_id':f'replay:{reservoir}:rain:{row.date:%Y-%m-%d}{suffix}',
               'observed_at':observed,'received_at':received,'source':'replay','provenance':provenance,
               'location_key':reservoir,'value':float(row.rain_kaggle_raw),'unit':'mm/day','period_seconds':86400,'qc_flags':[]}
        yield {'schema':'trackb.reservoir_update.v1','event_id':f'replay:{reservoir}:storage:{row.date:%Y-%m-%d}{suffix}',
               'observed_at':observed,'received_at':received,'source':'replay','provenance':provenance,
               'reservoir_key':reservoir,'storage_value':float(row.storage_mcft),'storage_unit':'mcft',
               'capacity_value':float(row.capacity_mcft),'capacity_unit':'mcft','release_value':None,'release_unit':'cusecs',
               'rainfall_mm':float(row.rain_kaggle_raw),'rain_3d_mm':None if pd.isna(row.rain_3d_mm) else float(row.rain_3d_mm),
               'rise_1d_pct':None if pd.isna(row.rise_1d_pct) else float(row.rise_1d_pct),
               'rise_3d_pct':None if pd.isna(row.rise_3d_pct) else float(row.rise_3d_pct),'qc_flags':[]}


def _redis_json(client:Any,key:str)->Any:
    raw=client.get(key)
    if raw is None:return None
    if isinstance(raw,bytes):raw=raw.decode('utf-8')
    return json.loads(raw)


def _series_upsert(client:Any,key:str,entry:dict,max_entries:int=8)->list[dict]:
    values=_redis_json(client,key) or []
    date=entry['date']
    values=[row for row in values if row.get('date')!=date]
    values.append(entry); values.sort(key=lambda row:row['date']); values=values[-max_entries:]
    client.set(key,json.dumps(values,separators=(',',':')),ex=14*86400)
    return values


def _delta_on_date(history:list[dict],target_date:str)->float|None:
    matches=[row for row in history if row['date']==target_date]
    return float(matches[-1]['storage_pct']) if matches else None


class TrackBEventProcessor:
    def __init__(self,redis_client:Any,producer:KafkaJSONProducer,thresholds:dict[str,dict],metrics:TrackBMetrics,
                 alert_writer:Callable[[dict],Any]|None=None,state_writer:Callable[[dict],Any]|None=None):
        self.redis=redis_client; self.producer=producer; self.thresholds=thresholds; self.metrics=metrics
        self.alert_writer=alert_writer; self.state_writer=state_writer

    def process(self,event:dict[str,Any])->bool:
        validate_event(event)
        dedupe=f"trackb:processed:{event['event_id']}"
        if self.redis.exists(dedupe):return False
        schema=event['schema']
        if schema=='trackb.rain_update.v1':self._rain(event)
        elif schema=='trackb.reservoir_update.v1':self._reservoir(event)
        elif schema=='trackb.alert.v1':self._alert(event)
        elif schema=='trackb.twin_update.v1':self.redis.set(f"trackb:twin:{event['run_id']}",json.dumps(event),ex=14*86400)
        self.redis.set(dedupe,'1',ex=30*86400)
        return True

    def _rain(self,event:dict[str,Any])->None:
        key=event['location_key'].upper(); day=event['observed_at'][:10]
        history=_series_upsert(self.redis,f'trackb:rain_history:{key}',{'date':day,'value':event['value'],'source':event['source']})
        self.redis.set(f'trackb:rain:{key}:latest',json.dumps({'observed_at':event['observed_at'],'value':event['value'],'unit':event['unit'],'source':event['source']}),ex=14*86400)

    def _reservoir(self,event:dict[str,Any])->None:
        key=event['reservoir_key'].upper(); observed=event['observed_at']; day=observed[:10]
        capacity=event['capacity_value']; storage=float(event['storage_value'])
        if capacity is None or float(capacity)<=0:
            storage_pct=None
        else:storage_pct=100*storage/float(capacity)
        rain_value=event.get('rainfall_mm')
        if rain_value is not None:
            rain_history=_series_upsert(self.redis,f'trackb:rain_history:{key}',{'date':day,'value':float(rain_value),'source':event['source']})
        else:rain_history=_redis_json(self.redis,f'trackb:rain_history:{key}') or []
        state_history=_redis_json(self.redis,f'trackb:storage_history:{key}') or []
        state_history=[r for r in state_history if r['date']!=day]
        if storage_pct is not None:state_history.append({'date':day,'storage_pct':storage_pct,'storage_mcft':storage,'source':event['source']})
        state_history.sort(key=lambda row:row['date']); state_history=state_history[-8:]
        self.redis.set(f'trackb:storage_history:{key}',json.dumps(state_history,separators=(',',':')),ex=14*86400)
        prior_day=(pd.Timestamp(day)-pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        prior_3day=(pd.Timestamp(day)-pd.Timedelta(days=3)).strftime('%Y-%m-%d')
        current=_delta_on_date(state_history,day)
        one=_delta_on_date(state_history,prior_day)
        three=_delta_on_date(state_history,prior_3day)
        rise1=float(event['rise_1d_pct']) if event.get('rise_1d_pct') is not None else (current-one if current is not None and one is not None else 0.)
        rise3=float(event['rise_3d_pct']) if event.get('rise_3d_pct') is not None else (current-three if current is not None and three is not None else 0.)
        rainfall_rows={r['date']:r.get('value') for r in rain_history}
        recent_days=[(pd.Timestamp(day)-pd.Timedelta(days=i)).strftime('%Y-%m-%d') for i in (2,1,0)]
        rain3=sum(float(rainfall_rows[d]) for d in recent_days if rainfall_rows.get(d) is not None)
        if event.get('rain_3d_mm') is not None:rain3=float(event['rain_3d_mm'])
        state={'event_id':event['event_id'],'observed_at':observed,'source':event['source'],
               'storage_value':storage,'storage_unit':event['storage_unit'],'capacity_value':capacity,
               'capacity_unit':event['capacity_unit'],'storage_pct':storage_pct,'rainfall_mm':rain_value,
               'rise_1d_pct':rise1,'rise_3d_pct':rise3,'rain_3d_mm':rain3,
               'release_value':event.get('release_value'),'qc_flags':event.get('qc_flags',[]),'provenance':event['provenance']}
        if self.state_writer is not None:self.state_writer(event)
        self.redis.set(f'trackb:reservoir:{key}:state',json.dumps(state,separators=(',',':')),ex=14*86400)
        alert={'schema':'trackb.alert.v1','event_id':f"alert:{key}:{observed}:trackb-rule-v1",'observed_at':observed,
               'received_at':datetime.now().astimezone().isoformat(),'source':event['source'],'provenance':event['provenance'],
               'reservoir_key':key,'level':'Normal','confidence':0.0,'valid_from':observed,
               'valid_to':(datetime.fromisoformat(observed.replace('Z','+00:00'))+timedelta(days=1)).isoformat(),
               'rule_version':'trackb-rule-v1','trigger_inputs':{'storage_pct':storage_pct,'rise_1d_pct':rise1,'rise_3d_pct':rise3,'rain_3d_mm':rain3},
               'target':{'horizon_days':7,'capacity_fraction':0.8,'status':'DEFAULT, to confirm'}}
        if storage_pct is not None and key in self.thresholds:
            frame=pd.DataFrame([{'storage_pct':storage_pct,'rise_1d_pct':rise1,'rise_3d_pct':rise3,'rain_3d_mm':rain3}])
            fired,level,confidence=rule_alert(frame,RuleThresholds(**self.thresholds[key]))
            alert['level']=('Normal','Watch','Warning','Critical')[int(level[0])]
            alert['confidence']=float(confidence[0])
        self.redis.set(f'trackb:alert:{key}:current',json.dumps({'level':alert['level'],'source':event['source'],'observed_at':observed}),ex=14*86400)
        if alert['level']!='Normal':
            if self.alert_writer is not None:self.alert_writer(alert)
            self.producer.send(alert)

    def _alert(self,event:dict[str,Any])->None:
        key=event['reservoir_key'].upper()
        self.redis.set(f'trackb:alert:{key}:current',json.dumps({'level':event['level'],'source':event['source'],'observed_at':event['observed_at'],'event_id':event['event_id']}),ex=14*86400)
        self.metrics.record_alert(event['level'],event['source'])
        if self.alert_writer is not None:self.alert_writer(event)


def process_message(message:Any,consumer:Any,producer:KafkaJSONProducer,processor:TrackBEventProcessor,metrics:TrackBMetrics,group_id:str='trackb-rule-engine')->bool:
    """Process one Kafka record, commit only success or a metadata-only DLQ record."""
    from confluent_kafka import KafkaError
    if message.error():
        if message.error().code()==KafkaError._PARTITION_EOF:return False
        metrics.record_rule_error('kafka_read'); raise RuntimeError('Kafka read failed')
    raw=message.value()
    if raw is None:raw=b''
    if not isinstance(raw,(bytes,bytearray)):raw=str(raw).encode('utf-8','replace')
    raw=bytes(raw)
    try:
        event=json.loads(raw.decode('utf-8'))
        if topic_for_event(event)!=message.topic():raise InvalidEvent('topic_schema_mismatch','event schema does not match Kafka topic')
        processed=processor.process(event)
    except (UnicodeDecodeError,json.JSONDecodeError,InvalidEvent) as exc:
        kind=exc.kind if isinstance(exc,InvalidEvent) else 'invalid_json'
        metrics.record_rule_error(kind)
        dead={'schema':'trackb.deadletter.v1','source':'unknown','original_topic':message.topic(),
              'event_id':None,'error_kind':kind,'payload_sha256':sha256(raw).hexdigest(),
              'received_at':datetime.now().astimezone().isoformat()}
        # The raw payload is intentionally omitted from the DLQ.
        producer.send_payload(DEAD_LETTER_TOPIC,dead,message.key() or b'unknown')
        producer.flush()
        consumer.commit(message=message,asynchronous=False)
        return False
    except Exception:
        metrics.record_rule_error('processing')
        raise
    if processed:
        metrics.record_message(message.topic(),event['source'])
        try:
            received=datetime.fromisoformat(event['received_at'].replace('Z','+00:00'))
            latency=max(0.,(datetime.now(received.tzinfo)-received).total_seconds())
            metrics.observe_latency(event['source'],latency)
        except (ValueError,TypeError):metrics.record_rule_error('invalid_received_at')
    # Producer output (notably generated alerts) must be acknowledged before the
    # source offset is committed, otherwise a crash could lose the alert.
    try:
        producer.flush()
    except Exception:
        # Redis state updates are idempotent; remove the event marker so a
        # Kafka redelivery can retry an alert whose broker delivery failed.
        processor.redis.delete(f"trackb:processed:{event['event_id']}")
        metrics.record_rule_error('delivery')
        raise
    consumer.commit(message=message,asynchronous=False)
    return processed


def update_consumer_lag(consumer:Any,metrics:TrackBMetrics,group_id:str='trackb-rule-engine')->None:
    for assignment in consumer.assignment():
        try:
            # Cached watermarks are refreshed as the consumer fetches records.
            # Broker queries here would block once per partition between polls,
            # starving the consumer on multi-partition topics.
            watermarks=consumer.get_watermark_offsets(assignment,cached=True)
            if watermarks is None:continue
            _,high=watermarks
            position=consumer.position([assignment])[0].offset
            if position<0 or high<0:continue
            # Keep the Prometheus group label fixed even when a one-off replay
            # uses a fresh Kafka group to avoid consuming pre-existing offsets.
            metrics.set_consumer_lag('trackb-rule-engine',assignment.topic,max(0,high-position))
        except Exception:metrics.record_rule_error('lag_probe')


def run_replay(start:str,end:str,bootstrap:str='localhost:9092',repo_root:Path|None=None,run_id:str|None=None)->dict[str,int]:
    from confluent_kafka import Producer
    root=repo_root or Path(__file__).resolve().parents[2]
    producer=KafkaJSONProducer(Producer({'bootstrap.servers':bootstrap,'enable.idempotence':True,'acks':'all'}))
    count=0
    for event in make_replay_events(root,start,end,run_id):
        event['received_at']=datetime.now().astimezone().isoformat()
        producer.send(event); count+=1
    producer.flush()
    if producer.delivered_count!=count:
        raise RuntimeError(f'Kafka delivery count mismatch: produced={count}, acknowledged={producer.delivered_count}')
    return {'produced':count,'acknowledged':producer.delivered_count}


def consumer_config(bootstrap:str,group_id:str='trackb-rule-engine',auto_offset_reset:str='earliest')->dict[str,Any]:
    if not isinstance(group_id,str) or not group_id.strip():raise ValueError('consumer group id must be non-empty')
    if auto_offset_reset not in {'earliest','latest','error'}:raise ValueError('unsupported auto_offset_reset policy')
    return {'bootstrap.servers':bootstrap,'group.id':group_id,'enable.auto.commit':False,
            'auto.offset.reset':auto_offset_reset}


def consume_forever(bootstrap:str='localhost:9092',redis_url:str='redis://127.0.0.1:6380/0',metrics_port:int=8000,
                    group_id:str='trackb-rule-engine',auto_offset_reset:str='earliest')->None:
    from confluent_kafka import Consumer,Producer
    from confluent_kafka.admin import AdminClient
    import redis
    root=Path(__file__).resolve().parents[2]
    admin=AdminClient({'bootstrap.servers':bootstrap}); ensure_topics(admin)
    producer=KafkaJSONProducer(Producer({'bootstrap.servers':bootstrap,'enable.idempotence':True,'acks':'all'}))
    redis_client=redis.Redis.from_url(redis_url,decode_responses=False)
    redis_client.ping()
    results=json.loads((root/'docs/trackb/BACKTEST_RESULTS.json').read_text(encoding='utf-8'))
    thresholds={key:value['rule_thresholds'] for key,value in results['per_reservoir'].items()}
    metrics=TrackBMetrics(); metrics.serve(metrics_port,'127.0.0.1')
    processor=TrackBEventProcessor(redis_client,producer,thresholds,metrics)
    consumer=Consumer(consumer_config(bootstrap,group_id,auto_offset_reset))
    consumer.subscribe(list(PRIMARY_TOPICS))
    try:
        while True:
            message=consumer.poll(.5)
            if message is not None:process_message(message,consumer,producer,processor,metrics,group_id)
            update_consumer_lag(consumer,metrics,group_id)
    except KeyboardInterrupt:pass
    finally:
        consumer.close(); producer.flush()


def main()->None:
    import argparse,os
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('topics')
    replay=sub.add_parser('replay'); replay.add_argument('--start',required=True); replay.add_argument('--end',required=True); replay.add_argument('--run-id')
    consumer=sub.add_parser('consume'); consumer.add_argument('--metrics-port',type=int,default=8000)
    args=parser.parse_args(); bootstrap=os.getenv('TRACKB_KAFKA_BOOTSTRAP_SERVERS','localhost:9092')
    if args.command=='topics':
        from confluent_kafka.admin import AdminClient
        ensure_topics(AdminClient({'bootstrap.servers':bootstrap})); print('Track B topics verified/created')
    elif args.command=='replay':
        result=run_replay(args.start,args.end,bootstrap,run_id=args.run_id)
        print(f"events produced: {result['produced']}; acknowledged: {result['acknowledged']}; source=replay; run_id={args.run_id or 'stable'}")
    elif args.command=='consume':consume_forever(
        bootstrap,os.getenv('TRACKB_REDIS_URL','redis://127.0.0.1:6380/0'),args.metrics_port,
        os.getenv('TRACKB_CONSUMER_GROUP','trackb-rule-engine'),os.getenv('TRACKB_AUTO_OFFSET_RESET','earliest'))

if __name__=='__main__':main()
