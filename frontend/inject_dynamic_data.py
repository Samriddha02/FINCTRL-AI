import re

def process_file(filepath, imports, pre_return, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Inject imports
    import_match = re.search(r"import React[^;]*;", content)
    if import_match:
        content = content[:import_match.end()] + "\n" + imports + content[import_match.end():]
    
    # Inject pre_return hooks
    return_match = re.search(r"return\s*\(", content)
    if return_match:
        content = content[:return_match.start()] + pre_return + "\n  " + content[return_match.start():]
        
    # Replace static values
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# 1. Dashboard
dashboard_imports = """
import { useQuery } from '@tanstack/react-query';
import { getReconciliationCases, getReviews, getTaxMatches, getCashForecast } from '../services/api';
"""
dashboard_pre = """
  const { data: recData } = useQuery({ queryKey: ['reconciliation'], queryFn: getReconciliationCases });
  const { data: revData } = useQuery({ queryKey: ['reviews'], queryFn: getReviews });
  const { data: taxData } = useQuery({ queryKey: ['taxMatches'], queryFn: getTaxMatches });
  
  const recCases = recData?.cases || [];
  const requiresInvestigation = recData?.status_breakdown?.['REQUIRES_INVESTIGATION'] || 0;
  const exactMatches = recData?.status_breakdown?.['EXACT_MATCH'] || 0;
  const totalCases = recData?.total_cases || 0;
  const pendingReviews = revData?.filter(r => r.status === 'PENDING').length || 0;
  const taxMismatches = taxData?.rate_mismatches || 0; // Simplified for demo
"""
dashboard_replacements = [
    ('53 matched, 47 attn', '{exactMatches} matched, {requiresInvestigation} attn'),
    ('47</div>', '{requiresInvestigation}</div>'),
    ('47</span>', '{requiresInvestigation}</span>'),
    ('Pending controller review', 'Pending review'),
    ('95 exact matches', '{exactMatches} exact matches'),
    ('95</div>', '{exactMatches}</div>'),
    ('47 PENDING', '{pendingReviews} PENDING'),
    ('All 47 Items', 'All {requiresInvestigation} Items')
]

process_file('src/pages/Dashboard.tsx', dashboard_imports, dashboard_pre, dashboard_replacements)

# 2. Reconciliation
rec_imports = """
import { useQuery } from '@tanstack/react-query';
import { getReconciliationCases } from '../services/api';
import { Link } from 'react-router-dom';
"""
rec_pre = """
  const { data: recData, isLoading } = useQuery({ queryKey: ['reconciliation'], queryFn: getReconciliationCases });
  const cases = recData?.cases || [];
"""
rec_replacements = [
    # Very basic injection to render table rows based on cases
    # We will replace the table body
]
# For tables, it's easier to just replace the entire <tbody> manually later or via regex.
