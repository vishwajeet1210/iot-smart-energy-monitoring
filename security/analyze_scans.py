import json

def analyze(path, label):
    print(f"=== {label} ({path}) ===")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    results = data.get('Results', [])
    total_findings = 0
    severity_counts = {}
    for r in results:
        target = r.get('Target')
        rtype = r.get('Type')
        vulns = r.get('Vulnerabilities', [])
        print(f"\nTarget: {target} | Type: {rtype} | Class: {r.get('Class')} | Findings: {len(vulns)}")
        total_findings += len(vulns)
        for v in vulns:
            sev = v.get('Severity')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            pkg = v.get('PkgName')
            inst = v.get('InstalledVersion')
            fix = v.get('FixedVersion')
            vid = v.get('VulnerabilityID')
            status = v.get('Status')
            datasource = v.get('DataSource', {}).get('Name')
            pkg_path = v.get('PkgPath')
            print(f"  [{sev}] {pkg} ({inst}) -> Fixed: {fix} | ID: {vid} | Status: {status} | Source: {datasource} | Path: {pkg_path}")
    print(f"\nSummary for {label}: Total={total_findings}, By Severity={severity_counts}\n")

if __name__ == '__main__':
    analyze('security/trivy-image-full-report.json', 'FULL SCAN')
    analyze('security/trivy-image-actionable-report.json', 'ACTIONABLE SCAN (--ignore-unfixed)')
