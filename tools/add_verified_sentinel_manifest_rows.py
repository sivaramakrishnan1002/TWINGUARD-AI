"""Add newly verified Sentinel archive rows without replacing existing manifest entries."""
import csv
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/DATA_MANIFEST.csv'
REPORT=ROOT/'docs/SENTINEL_VERIFICATION.md'
RAW=ROOT/'data/raw/satellite/senitnel1'
FIELDS=['dataset','category','source name','source URL','retrieval date','time period covered','spatial resolution','temporal resolution','CRS','coverage of CMA','size','licence','status','filename','sha256','verification']

def main():
    with MANIFEST.open('r',encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream); rows=list(reader)
    text=REPORT.read_text(encoding='utf-8')
    verified_names={line.split('|')[1].strip().strip('`') for line in text.splitlines() if line.startswith('| `S1') and '.zip`' in line}
    # Remove only the malformed duplicate rows created by an earlier version of
    # this helper in this task; the real raw paths include the existing typo folder.
    rows=[r for r in rows if not (r.get('category')=='satellite' and re.fullmatch(r'satellite/20\d\d/S1[^/]+\.zip',r.get('filename','').replace('\\','/')) and Path(r.get('filename','')).name in verified_names)]
    known={r.get('filename','').replace('\\','/') for r in rows}
    missing=[]
    for line in text.splitlines():
        if not line.startswith('| `S1') or '.zip`' not in line: continue
        cells=[part.strip() for part in line.strip().strip('|').split('|')]
        if len(cells)<12 or cells[3]!='PASS' or cells[11]!='yes': continue
        name=cells[0].strip('`'); rel=(Path('satellite')/'senitnel1'/name.split('_')[4][:4]/name).as_posix()
        if rel in known: continue
        path=RAW/name.split('_')[4][:4]/name
        if not path.is_file(): raise FileNotFoundError(path)
        date=datetime.strptime(name.split('_')[4][:8],'%Y%m%d').date().isoformat()
        mtime=datetime.fromtimestamp(path.stat().st_mtime,ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S Asia/Kolkata')
        missing.append({'dataset':'Sentinel-1 ASF GRD-HD scene','category':'satellite','source name':'NASA ASF Vertex','source URL':'https://search.asf.alaska.edu/','retrieval date':mtime,'time period covered':date,'spatial resolution':'scene footprint; see verification report','temporal resolution':'single acquisition','CRS':'WGS84 source footprint; coverage computed in EPSG:32644','coverage of CMA':cells[10],'size':cells[1].replace(',',''),'licence':'TO CONFIRM from ASF and Copernicus terms','status':'collected','filename':rel,'sha256':cells[2].strip('`'),'verification':'SAFE metadata/name match; ZIP testzip PASS; see docs/SENTINEL_VERIFICATION.md'})
    rows.extend(missing)
    if missing:
        with MANIFEST.open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    print(f'Added {len(missing)} newly verified Sentinel rows; preserved {len(rows)-len(missing)} existing rows.')

if __name__=='__main__':main()
