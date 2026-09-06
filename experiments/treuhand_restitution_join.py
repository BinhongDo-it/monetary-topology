"""Treuhand disposition x German commercial register: the restitution arm.

Reads the BvS FOI file (firm-level Treuhand disposition, public) and joins it to
the OffeneRegister 2022 SQLite dump on (court, register type, register number).
Writes one row per BvS firm with its match status and, where matched uniquely,
the register company id and dissolution date.

Data (both public, in data/raw/Treuhand/):
  THU_Status_BvS.xlsx   FOI response from BvS, via github.com/AAoritz/Treuhand
  handelsregister.db    daten.offeneregister.de, 2022-10-21, 3.72 GB SQLite

Known walls, measured (see the working notes, sections 107-109):
  - the register db starts ~2005; firms dissolved in the 1990s are absent, so a
    non-match conflates "died early" with "no post-2005 announcement".
  - Sachsen-Anhalt and Thueringen courts were consolidated into Stendal and Jena;
    their 1990s court names do not exist in the db, so those firms need a name
    join and are reported here as court_unmapped.
"""
import argparse, collections, csv, os, re, sqlite3, sys
import openpyxl

STATUS = ['V', 'R', 'L', 'F', 'SP', 'GV', 'IL']
STATUS_LABEL = {'V': 'verkauft', 'R': 'rueckuebertragen', 'L': 'liquidiert',
                'F': 'fusioniert', 'SP': 'Spaltung', 'GV': 'Gesamtvollstreckung',
                'IL': 'IL'}
# BvS court name -> register-db court name. Only the four Laender whose courts
# survived consolidation under the same name.
COURTMAP = {
    'Chemnitz': 'Chemnitz', 'Dresden': 'Dresden', 'Leipzig': 'Leipzig',
    'Potsdam': 'Potsdam', 'Frankfurt/Oder': 'Frankfurt/Oder',
    'Cottbus': 'Cottbus', 'Neuruppin': 'Neuruppin',
    'Neubrandenburg': 'Neubrandenburg', 'Rostock': 'Rostock',
    'Schwerin': 'Schwerin', 'Stralsund': 'Stralsund',
    'Berlin-Charlottenburg': 'Berlin (Charlottenburg)',
    'Charlottenburg': 'Berlin (Charlottenburg)',
}
EAST_LAENDER = ['SACH', 'S-AN', 'THUER', 'BRAN', 'ME-V', 'BLNO']
NR_RE = re.compile(r'^\s*(HRB|HRA|HRC|GNR|HR)\s*\.?\s*0*(\d+)')
NAT_RE = re.compile(r'\b(HRB|HRA|HRC|GnR)\s*([0-9]+)', re.I)


def parse_nr(nr):
    m = NR_RE.match((nr or '').upper().strip())
    return (m.group(1), int(m.group(2))) if m else None


def read_bvs(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for sheet in STATUS:
        ws = wb[sheet]
        it = ws.iter_rows(values_only=True)
        hdr = list(next(it))
        col = {h: k for k, h in enumerate(hdr)}
        for r in it:
            if r[col['FIRMA']] is None:
                continue
            g = lambda k: r[col[k]]
            out.append({
                'status': sheet,
                'firma': g('FIRMA'),
                'name': g('NAME'),
                'altname': g('ALTNAME'),
                'gegenstand': g('GEGENSTAND'),
                'bundesland': (g('BUNDESLAND') or '').strip(),
                'register_ort': (str(g('REGISTER_ORT')).strip() if g('REGISTER_ORT') else ''),
                'register_nr': (str(g('REGISTER_NR')).strip() if g('REGISTER_NR') else ''),
                'taetenddat': g('TAETENDDAT'),
            })
    return out


def build_index(db_path):
    con = sqlite3.connect('file:%s?mode=ro' % db_path, uri=True)
    cur = con.cursor()
    courts = sorted(set(COURTMAP.values()))
    idx = collections.defaultdict(list)
    q = ("SELECT companyId, nativeReferenceNumber, courtName FROM ReferenceNumbers "
         "WHERE courtName IN (%s)" % ",".join("?" * len(courts)))
    for cid, nat, court in cur.execute(q, tuple(courts)):
        m = NAT_RE.search(nat or '')
        if m:
            idx[(court, m.group(1).upper(), int(m.group(2)))].append(cid)
    diss = {}
    for cid, d, first, last in cur.execute(
            "SELECT companyId, dissolutionDate, firstSeenDate, lastSeenDate FROM Companies"):
        diss[cid] = (d or '', first or '', last or '')
    con.close()
    return idx, diss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default='data/raw/Treuhand')
    ap.add_argument('--out', default='data/processed/treuhand')
    a = ap.parse_args()
    xlsx = os.path.join(a.raw, 'THU_Status_BvS.xlsx')
    db = os.path.join(a.raw, 'handelsregister.db')
    for p in (xlsx, db):
        if not os.path.exists(p):
            sys.exit('missing input: %s' % p)
    os.makedirs(a.out, exist_ok=True)

    bvs = read_bvs(xlsx)
    print('bvs rows: %d' % len(bvs))
    idx, diss = build_index(db)
    print('register keys: %d   register companies: %d' % (len(idx), len(diss)))

    rows = []
    for b in bvs:
        court = COURTMAP.get(b['register_ort'])
        key = parse_nr(b['register_nr'])
        if court is None:
            outcome, cid = ('court_unmapped', '')
        elif key is None:
            outcome, cid = ('nr_unparsed', '')
        else:
            cands = idx.get((court,) + key, [])
            if not cands:
                outcome, cid = ('no_match', '')
            elif len(cands) > 1:
                outcome, cid = ('multi', '')
            else:
                outcome, cid = ('unique', cands[0])
        d, first, last = diss.get(cid, ('', '', ''))
        rows.append(dict(b, match=outcome, company_id=cid,
                         dissolution_date=d, first_seen=first, last_seen=last))

    path = os.path.join(a.out, 'bvs_register_join.csv')
    cols = ['firma', 'status', 'name', 'altname', 'bundesland', 'register_ort',
            'register_nr', 'taetenddat', 'match', 'company_id',
            'dissolution_date', 'first_seen', 'last_seen', 'gegenstand']
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('wrote %s (%d rows)' % (path, len(rows)))

    # identities and the headline table, printed rather than asserted
    by_status = collections.Counter(r['status'] for r in rows)
    print('\nsheet counts vs codebook:')
    codebook = {'L': 3314, 'IL': 66, 'V': 6929, 'GV': 247, 'R': 1946, 'F': 732, 'SP': 144}
    for s in STATUS:
        ok = 'OK' if by_status[s] == codebook[s] else 'DIFF %+d' % (by_status[s] - codebook[s])
        print('  %-3s %6d  codebook %6d  %s' % (s, by_status[s], codebook[s], ok))
    print('  total %d (codebook 13378) %s'
          % (len(rows), 'OK' if len(rows) == 13378 else 'DIFF'))

    print('\nfour-Laender join, one row per status:')
    print('%-3s %6s %8s %7s %7s %7s %9s %8s'
          % ('st', 'N', 'unique', 'rate', 'multi', 'nomatch', 'dissolved', 'diss%'))
    for s in STATUS:
        sub = [r for r in rows if r['status'] == s
               and r['match'] in ('unique', 'multi', 'no_match')]
        if not sub:
            continue
        u = [r for r in sub if r['match'] == 'unique']
        dsv = [r for r in u if r['dissolution_date']]
        print('%-3s %6d %8d %6.1f%% %7d %7d %9d %7.1f%%'
              % (s, len(sub), len(u), 100.0 * len(u) / len(sub),
                 sum(1 for r in sub if r['match'] == 'multi'),
                 sum(1 for r in sub if r['match'] == 'no_match'),
                 len(dsv), 100.0 * len(dsv) / len(u) if u else 0.0))

    print('\nnot joined here (need a name join):')
    cu = collections.Counter(r['status'] for r in rows if r['match'] == 'court_unmapped')
    for s in STATUS:
        if cu[s]:
            print('  %-3s %6d' % (s, cu[s]))
    print('  total %d' % sum(cu.values()))


if __name__ == '__main__':
    main()
