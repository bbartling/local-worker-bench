"""Export synthetic draft/grade evidence without executing any candidate.

Raw high-frequency samples remain local; hashes identify the original receipts.
Publication never turns an unreviewed candidate into a coding success.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_worker_bench.project_bench import TASKS,digest_files,SUITE_VERSION,suite_sha256,SUITE_V1_TOTALS,SUITE_V3_TOTALS


def publish(folder):
    state=json.loads((folder/'campaign.json').read_text())
    result={'published_epoch':time.time(),'campaign':state,'trials':{},'summary':{},
        'limitations':['Synthetic projects inspired by Open-FDD; no real application patch.',
            'Fixed public tests withheld from prompts; not contamination resistant.',
            'One trial per model/task; no randomized repeats or cold-cache reset.',
            'Individual cases are correlated; full-task acceptance is the primary measure.',
            'No hosted cost/effort baseline measured; no cloud-cost savings claim.']}
    for key,record in state['trials'].items():
        trial=folder/key;item={'record':record,'grade':None,'accepted':False,
            'supervisor_cancelled':record.get('error')=='Campaign stopped/deadline'}
        item['packet']=json.loads((trial/'packet.json').read_text())
        item['prompt']=(trial/'prompt.txt').read_text()
        if hashlib.sha256(item['prompt'].encode()).hexdigest()!=record['prompt_sha256']:
            raise ValueError('Prompt changed after claim')
        candidate_path=trial/'candidate.json'
        if candidate_path.exists():
            candidate=json.loads(candidate_path.read_text());item['candidate']=candidate
            rid=candidate.get('resource_receipt')
            if rid:
                receipts=folder/'api-receipts'/rid
                raw=receipts/'receipt.json'
                if raw.exists():
                    receipt=json.loads(raw.read_text());receipt.pop('samples',None)
                    item['resource_receipt']=receipt
                    item['raw_receipt_sha256']=hashlib.sha256(raw.read_bytes()).hexdigest()
                if (receipts/'partial.txt').exists():item['captured_content']=(receipts/'partial.txt').read_text()
            grade_path=trial/'grade.json'
            if grade_path.exists():
                grade=json.loads(grade_path.read_text());files=candidate.get('answer',{}).get('files')
                if not isinstance(files,dict) or digest_files(files)!=record.get('source_sha256') or grade.get('source_sha256')!=record['source_sha256']:
                    raise ValueError('Candidate/grade bundle mismatch')
                if 'suite_version' in grade:
                    if grade['suite_version']==SUITE_VERSION:
                        if grade.get('suite_sha256')!=suite_sha256(SUITE_VERSION):
                            raise ValueError('Grade suite hash mismatch')
                        expected=state.get('suite_version',SUITE_VERSION)
                        if grade['suite_version']!=expected:
                            raise ValueError('Grade suite version mismatch')
                        if grade.get('total')!=SUITE_V3_TOTALS.get(record['task']):
                            raise ValueError('Suite 3 grade total mismatch')
                    elif grade['suite_version']!=1:
                        raise ValueError('Unknown suite version in grade')
                    elif grade.get('total')!=SUITE_V1_TOTALS.get(record['task']):
                        raise ValueError('Frozen v1 grade total mismatch')
                disk={name:(trial/'candidate'/name).read_bytes().decode('utf-8') for name in TASKS[record['task']]['files']}
                if disk!=files:raise ValueError('Saved source differs from model response')
                if item['packet']['base_revision']!=record['base_revision'] or digest_files(TASKS[record['task']]['files'])!=record['base_revision']:
                    raise ValueError('Fixture revision changed')
                item['grade']=grade
                review_path=trial/'review.json'
                if review_path.exists():
                    review=json.loads(review_path.read_text())
                    if review.get('source_sha256')!=record['source_sha256']:
                        raise ValueError('Supervisor review hash mismatch')
                    item['review']=review
                    item['accepted']=(not item['supervisor_cancelled'] and review.get('decision')=='accept' and grade.get('code_executed') is True
                        and grade['passed']==grade['total'] and grade['total']>0)
        result['trials'][key]=item
        summary=result['summary'].setdefault(record['model'],{'accepted_tasks':0,'graded_tasks':0,'attempted_tasks':0,'cancelled_tasks':0,'claimed_tasks':0,'coding_seconds':0})
        summary['claimed_tasks']+=1
        if item['supervisor_cancelled']:summary['cancelled_tasks']+=1
        else:summary['attempted_tasks']+=1
        if item['grade'] is not None:summary['graded_tasks']+=1
        if item['accepted']:summary['accepted_tasks']+=1
        summary['coding_seconds']+=item.get('candidate',{}).get('seconds',0)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();result=publish(args.folder)
    # Synthetic tracebacks can contain workspace paths; remove host/user paths.
    text=json.dumps(result,indent=2)
    for path,label in [(str(ROOT),'<repo>'),(str(ROOT).replace('\\','/'),'<repo>'),(str(Path.home()),'<home>')]:
        text=text.replace(json.dumps(path)[1:-1],label)
    args.output.write_text(text+'\n',encoding='utf-8')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
