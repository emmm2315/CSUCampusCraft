"""External response privacy scanner. Synthetic regression output contains booleans/counts only."""
import re
PATTERN=re.compile(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}')
def contains_bcrypt(text):return PATTERN.search(text) is not None
def run_regression(old_pattern=None):
    positives=['$2'+prefix+'$10$'+('A'*53) for prefix in 'aby']
    positives+=['prefix '+positives[1]+' suffix']
    negatives=['','ordinary public text','$2x$10$'+('A'*53),'$2a$1$'+('A'*53),'$2a$10$'+('A'*52)]
    checks={**{'positive-prefix-or-context-'+str(i):contains_bcrypt(s) for i,s in enumerate(positives)},**{'negative-'+str(i):not contains_bcrypt(s) for i,s in enumerate(negatives)}}
    return dict(overall='PASS' if all(checks.values()) else 'FAIL',checks=checks,positive_cases=len(positives),negative_cases=len(negatives),new_positive_hits=sum(contains_bcrypt(s) for s in positives),old_positive_hits=sum(bool(re.search(old_pattern,s)) for s in positives) if old_pattern is not None else None,synthetic_hash_values_recorded=False)
