"""Extract cached LUT-DEMAND v1.1 continent electricity demand (read-only)."""
from pathlib import Path
import argparse, hashlib, json, re, zipfile
import xml.etree.ElementTree as ET
import pandas as pd

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
SHEET='Export power ESD,FED GCML'
CONTINENTS=('Africa','Asia','Australia / Oceania','Europe','Americas')
class ExtractionError(ValueError): pass

def _source_rows(path):
    with zipfile.ZipFile(path) as z:
        book=ET.fromstring(z.read('xl/workbook.xml'))
        rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        targets={r.attrib['Id']:r.attrib['Target'] for r in rels}
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(t.text or '' for t in si.iter('{%s}t'%NS['m']))
                    for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS)]
        for sh in book.findall('m:sheets/m:sheet',NS):
            if sh.attrib['name']!=SHEET: continue
            target=targets[sh.attrib['{%s}id'%NS['r']]]
            xml=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            root=ET.fromstring(z.read(xml))
            rows={}
            for row in root.findall('m:sheetData/m:row',NS):
                cells={}
                for c in row.findall('m:c',NS):
                    v=c.find('m:v',NS)
                    if v is None or v.text is None: continue
                    cells[c.attrib['r']]=shared[int(v.text)] if c.attrib.get('t')=='s' else v.text
                rows[int(row.attrib['r'])]=cells
            return rows
    raise ExtractionError('Required worksheet not found: '+SHEET)

def extract_continent_demand(path, years=range(2020,2051,5)):
    rows=_source_rows(path)
    if rows[8].get('C8')!='Energy service demand - power sector - electricity' or rows[9].get('C9')!='TWhel':
        raise ExtractionError('Unexpected parameter or unit')
    wanted=set(map(int,years)); columns={}
    for cell,value in rows[10].items():
        if re.fullmatch('[A-Z]+10',cell) and str(value).isdigit() and int(value) in wanted:
            columns[int(value)]=re.match('[A-Z]+',cell).group()
    if set(columns)!=wanted: raise ExtractionError('Requested years not found')
    records=[]
    for i,region in enumerate(CONTINENTS,11):
        if rows[i].get(f'B{i}')!=region: raise ExtractionError('Region label mismatch')
        for year,col in sorted(columns.items()):
            address=f'{col}{i}'
            try: value=float(rows[i][address])
            except (KeyError,ValueError) as e: raise ExtractionError('Missing cached value '+address) from e
            if not 0<=value<float('inf'): raise ExtractionError('Invalid value '+address)
            records.append(dict(source_sheet=SHEET,source_cell=address,region=region,year=year,
                                sector='power',carrier='electricity',
                                quantity_kind='annual_energy_service_demand',value_twh=value,annual_mwh=value*1e6))
    data=pd.DataFrame(records); checks=[]
    for year,col in sorted(columns.items()):
        global_twh=float(rows[5][f'{col}5'])
        total=data.loc[data.year==year,'value_twh'].sum()
        delta=total-global_twh
        if abs(delta)>max(1e-5,abs(global_twh)*1e-9): raise ExtractionError('Global mismatch '+str(year))
        checks.append(dict(year=year,global_twh=global_twh,continents_twh=total,
                           difference_twh=delta,global_source_cell=f'{col}5'))
    return data,pd.DataFrame(checks)

def export(path,output,years=range(2020,2051,5)):
    path=Path(path);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    data,checks=extract_continent_demand(path,years)
    data.to_csv(output/'lut_continent_electricity_annual.csv',index=False)
    checks.to_csv(output/'global_reconciliation.csv',index=False)
    meta=dict(source_file=path.name,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              source_sheet=SHEET,source_unit='TWhel',cached_formula_values=True,
              formula_recalculation_performed=False,years=sorted(data.year.unique().tolist()),
              interpretation='Annual electricity energy service demand, not hourly measured load',
              hourly_profiles_supplied=False,pypsa_optimization_performed=False)
    (output/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
    return data,checks

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('workbook');parser.add_argument('--output',default='outputs/lut')
    args=parser.parse_args()
    data,checks=export(args.workbook,args.output)
    print('Records:',len(data),'Max reconciliation error (TWh):',checks.difference_twh.abs().max())
