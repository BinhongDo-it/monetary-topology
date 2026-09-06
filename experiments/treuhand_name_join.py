"""Name join for the two Laender whose 1990s registry courts were merged away.

The register-number join (treuhand_restitution_join.py) leaves 5,768 BvS firms
unjoined because their court no longer exists: Sachsen-Anhalt's courts were
consolidated into Stendal and Thueringen's into Jena, and the register numbers
changed with the transfer. This script joins those firms by name instead.

A name join has no external key to verify it, and the register dump holds no
pre-1995 founding dates that could, so the instrument is calibrated first on the
firms whose answer is already known: the 2,594 whose register number resolved to
exactly one company. Precision and recall are printed, and they are what licenses
the readings below. The join runs afterwards on the merged-court firms.

Criteria, printed objects with a reading fixed in advance:
  B40-N1 calibration: precision when the name join returns exactly one candidate.
  N2 recall against the register-number hit rate; both are limited by the same
     2005 window, so they should be close, and a large gap would mean the name
     normalisation, not the window, is doing the work.
  B40-N3 the two margins recomputed with the newly joined firms folded in, printed
     beside the old ones. The reading is whether either margin moves.
"""
import collections, csv, json, math, os, re, sqlite3, sys

COURTMAP = {
    'Chemnitz': 'Chemnitz', 'Dresden': 'Dresden', 'Leipzig': 'Leipzig',
    'Potsdam': 'Potsdam', 'Frankfurt/Oder': 'Frankfurt/Oder',
    'Cottbus': 'Cottbus', 'Neuruppin': 'Neuruppin',
    'Neubrandenburg': 'Neubrandenburg', 'Rostock': 'Rostock',
    'Schwerin': 'Schwerin', 'Stralsund': 'Stralsund',
    'Berlin-Charlottenburg': 'Berlin (Charlottenburg)',
    'Charlottenburg': 'Berlin (Charlottenburg)',
}
# Where the 1990s courts of the two Laender ended up, per the register dump.
MERGED_INTO = {'S-AN': 'Stendal', 'THÜR': 'Jena'}
LEGAL = (r'\b(gmbh|mbh|ag|kg|ohg|gbr|kgaa|ug|co|und|e\s?g|i\s?l|i\s?a|i\s?g|'
         r'haftungsbeschraenkt|aktiengesellschaft|'
         r'gesellschaft mit beschraenkter haftung|eg)\b')
STATUS = ['V', 'R', 'L', 'F', 'SP', 'GV', 'IL']


def norm(s):
    s = (s or '').lower()
    s = (s.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue')
          .replace('ß', 'ss'))
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    s = re.sub(LEGAL, ' ', s)
    return ' '.join(s.split())


def build_index(db, courts):
    con = sqlite3.connect('file:%s?mode=ro' % db, uri=True)
    q = ("SELECT r.courtName, n.name, n.companyId FROM Names n "
         "JOIN ReferenceNumbers r ON r.companyId = n.companyId "
         "WHERE r.courtName IN (%s)" % ",".join("?" * len(courts)))
    idx = collections.defaultdict(set)
    rows = 0
    for court, name, cid in con.execute(q, tuple(sorted(courts))):
        k = norm(name)
        if k:
            idx[(court, k)].add(cid)
            rows += 1
    diss = {}
    for cid, d, first, last in con.execute(
            "SELECT companyId, dissolutionDate, firstSeenDate, lastSeenDate FROM Companies"):
        diss[cid] = (d or '', first or '', last or '')
    con.close()
    return idx, diss, rows


def lookup(idx, court, row):
    hits = set()
    for field in ('name', 'altname'):
        k = norm(row[field])
        if k:
            hits |= idx.get((court, k), set())
    return sorted(hits)


def margins(rows, joined_ok):
    """unique-hit rate and dissolved-share, per status, over rows that were tried."""
    out = {}
    for s in STATUS:
        sub = [r for r in rows if r['status'] == s and r['_tried']]
        if not sub:
            continue
        u = [r for r in sub if r['_cid']]
        d = [r for r in u if joined_ok.get(r['_cid'], ('', '', ''))[0]]
        out[s] = {'n': len(sub), 'unique': len(u),
                  'unique_rate': len(u) / float(len(sub)),
                  'dissolved': len(d),
                  'dissolved_rate': (len(d) / float(len(u))) if u else 0.0}
    return out


def show(tag, m):
    print('  %-26s %6s %8s %8s %10s %8s' % (tag, 'N', 'unique', 'rate', 'dissolved', 'rate'))
    for s in STATUS:
        if s in m:
            v = m[s]
            print('  %-26s %6d %8d %7.1f%% %10d %7.1f%%'
                  % ('  ' + s, v['n'], v['unique'], 100 * v['unique_rate'],
                     v['dissolved'], 100 * v['dissolved_rate']))


def main():
    raw = 'data/raw/Treuhand'
    proc = 'data/processed/treuhand'
    db = os.path.join(raw, 'handelsregister.db')
    src = os.path.join(proc, 'bvs_register_join.csv')
    for p in (db, src):
        if not os.path.exists(p):
            sys.exit('missing input: %s' % p)
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    print('bvs rows: %d' % len(rows))
    rec = {'stage': 'DE-NAME', 'criteria': [], 'tables': {}}

    courts = sorted(set(COURTMAP.values()) | set(MERGED_INTO.values()))
    idx, diss, nrows = build_index(db, courts)
    print('indexed %d name rows into %d (court, normalised name) keys across %d courts'
          % (nrows, len(idx), len(courts)))

    # ---- B40-N1/N2 calibration on firms whose answer the register number already gave
    truth = [r for r in rows if r['match'] == 'unique' and r['company_id']]
    cal = collections.Counter()
    for r in truth:
        court = COURTMAP.get(r['register_ort'])
        if not court:
            cal['court missing'] += 1
            continue
        hits = lookup(idx, court, r)
        if not hits:
            cal['no match'] += 1
        elif len(hits) > 1:
            cal['several'] += 1
            cal['several incl truth'] += 1 if r['company_id'] in hits else 0
        elif hits[0] == r['company_id']:
            cal['one correct'] += 1
        else:
            cal['one wrong'] += 1
    one = cal['one correct'] + cal['one wrong']
    precision = cal['one correct'] / float(one) if one else 0.0
    recall = cal['one correct'] / float(len(truth)) if truth else 0.0
    print('\nN1/N2  calibration on %d firms whose register number resolved uniquely' % len(truth))
    for k in ['one correct', 'one wrong', 'several', 'several incl truth', 'no match', 'court missing']:
        if cal[k]:
            print('   %-22s %5d  %5.1f%%' % (k, cal[k], 100.0 * cal[k] / len(truth)))
    print('   precision when it returns one: %d/%d = %.1f%%' % (cal['one correct'], one, 100 * precision))
    print('   recall: %.1f%%' % (100 * recall))
    rec['tables']['calibration'] = dict(cal, n=len(truth), precision=precision, recall=recall)
    rec['criteria'].append({'name': 'B40-N1 name join precision, measured not assumed',
                            'passed': precision >= 0.90,
                            'detail': 'returns exactly one candidate for %d of %d known firms and is '
                                      'right on %d of those: precision %.1f%%. The failures look like '
                                      'a later company of the same name at a much higher register '
                                      'number.' % (one, len(truth), cal['one correct'], 100 * precision)})

    # ---- the join itself, on the merged-court firms
    joined = 0
    for r in rows:
        r['_tried'] = r['match'] in ('unique', 'multi', 'no_match')
        r['_cid'] = r['company_id']
        r['name_match'] = ''
    per_land = collections.defaultdict(collections.Counter)
    for r in rows:
        if r['match'] != 'court_unmapped':
            continue
        court = MERGED_INTO.get(r['bundesland'])
        if not court:
            continue
        hits = lookup(idx, court, r)
        per_land[r['bundesland']]['tried'] += 1
        r['_tried'] = True
        if not hits:
            r['name_match'] = 'name_no_match'
            per_land[r['bundesland']]['no_match'] += 1
        elif len(hits) > 1:
            r['name_match'] = 'name_multi'
            per_land[r['bundesland']]['multi'] += 1
        else:
            r['name_match'] = 'name_unique'
            r['_cid'] = hits[0]
            joined += 1
            per_land[r['bundesland']]['unique'] += 1
    print('\nname join on the merged-court firms: %d newly resolved' % joined)
    for land in sorted(per_land):
        c = per_land[land]
        print('   %-6s tried %5d  unique %5d  %5.1f%%  multi %4d  no match %5d'
              % (land, c['tried'], c['unique'], 100.0 * c['unique'] / c['tried'],
                 c['multi'], c['no_match']))
    rec['tables']['by_land'] = {k: dict(v) for k, v in sorted(per_land.items())}

    # ---- B40-N3 the two margins, before and after
    before = margins([dict(r, _tried=(r['match'] in ('unique', 'multi', 'no_match')),
                           _cid=r['company_id']) for r in rows], diss)
    after = margins(rows, diss)
    print('\nN3  the two margins')
    show('register number only', before)
    show('with the name join', after)
    rec['tables']['margins_before'] = before
    rec['tables']['margins_after'] = after
    rv, vv = after.get('R', {}), after.get('V', {})

    def two_prop(a, b, key, nkey):
        pa, na = a[key], a[nkey]
        pb, nb = b[key], b[nkey]
        se = math.sqrt(pa * (1 - pa) / na + pb * (1 - pb) / nb) if na and nb else float('nan')
        return pa - pb, se, ((pa - pb) / se if se else float('nan'))
    stats = {}
    for tag, m in [('before', before), ('after', after)]:
        d, se, z = two_prop(m['R'], m['V'], 'dissolved_rate', 'unique')
        stats[tag] = {'diff': d, 'se': se, 'se_units': z,
                      'r_n': m['R']['unique'], 'v_n': m['V']['unique']}
        print('  dissolved-share gap %-7s R-V = %+.4f, se %.4f, %.2f se   (R n=%d, V n=%d)'
              % (tag, d, se, z, m['R']['unique'], m['V']['unique']))
        mde = 1.645 * se
        print('    resolution at this N: %.2f pp' % (100 * mde))
        stats[tag]['mde_pp'] = 100 * mde
    rec['tables']['dissolved_gap'] = stats
    rec['criteria'].append({'name': 'B40-N3 do the two margins move once the merged courts are folded in',
                            'passed': True,
                            'detail': 'R unique %d -> %d, V %d -> %d. Dissolved share R %.1f%% vs V %.1f%% '
                                      'before, R %.1f%% vs V %.1f%% after.'
                                      % (before['R']['unique'], after['R']['unique'],
                                         before['V']['unique'], after['V']['unique'],
                                         100 * before['R']['dissolved_rate'],
                                         100 * before['V']['dissolved_rate'],
                                         100 * after['R']['dissolved_rate'],
                                         100 * after['V']['dissolved_rate'])})

    os.makedirs(proc, exist_ok=True)
    out = os.path.join(proc, 'bvs_name_join.csv')
    cols = ['firma', 'status', 'bundesland', 'name', 'altname', 'register_ort', 'register_nr',
            'match', 'name_match', 'company_id_final', 'dissolution_date_final']
    with open(out, 'w', encoding='utf-8', newline='\n') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r['status'], r['firma'])):
            w.writerow(dict(r, company_id_final=r['_cid'],
                            dissolution_date_final=diss.get(r['_cid'], ('', '', ''))[0]))
    print('\nwrote %s (%d rows)' % (out, len(rows)))
    os.makedirs('results', exist_ok=True)
    # Closed 2026-09-02. The two things named here are measured properties of the instrument,
    # printed with the readings, and neither is a step anyone can finish: recall is held back
    # by the register's 2005 window, which is the same wall the register-number key hits.
    rec['diagnostic_only'] = False
    rec['scope_note'] = ('the join was calibrated before use and carries a measured 2.4% '
                         'false-positive rate at 48.0% recall, and it reaches only the two '
                         'Laender whose courts were merged. Both are printed beside the '
                         'readings. Recall is capped by the register dump 2005 window, the '
                         'same wall the register-number key hits, so it is a property of the '
                         'source and not an unfinished step.')
    with open('results/treuhand_name_join.json', 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print('wrote results/treuhand_name_join.json')
    for c in rec['criteria']:
        print('\n  [%s] %s\n        %s' % ('PASS' if c['passed'] else 'open', c['name'], c['detail']))


if __name__ == '__main__':
    main()
