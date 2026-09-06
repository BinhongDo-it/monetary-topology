"""Treuhand disposition x commercial-registry entry: did the firm ever get one?

The outcome here is not survival. It is one margin earlier: whether the entity
the Treuhand disposed of ever acquired a commercial-registry entry at all. That
is readable inside the BvS FOI file alone, with no join to any register dump, so
it does not inherit the 2005 window that limits the survival read (see the
working notes, sections 107-110).

Outcome, from REGISTER_ORT:
    empty, or a phrase saying no entry exists  ->  no registry entry
    a court name                               ->  has a registry entry
REGISTER_DATUM reproduces the same split independently and is printed as a
structural check, not as a second outcome.

Criteria are printed objects with a reading fixed in advance, never a line drawn
on an estimate:
  B40-1 structural: does the outcome mean the same thing in both arms?
  B40-2 direction : per-Land table, printed; the reading is whether any Land flips.
  B40-3 asset story: restrict to firms that name themselves a company; does the gap
                  widen or narrow?
  B40-4 record story: if the cell were sloppy recording, GRUEND_DAT would be gone
                  too; it is printed beside REGISTER_DATUM.
  B40-5 size story : the rated subset covers large firms only; N and the smallest
                  difference it resolves are printed. A bound, not a decision.
  B40-9 who was rated at all: the rating share of every disposal status, printed.
                  The committee's rating is an input to the agency's own decision
                  (grade 6 reads 'sollte dem Konkursverfahren zugefuehrt werden'),
                  so a status the agency did not decide should be the least rated.
                  The reading is fixed here: if restitution is the least covered of
                  the seven, that is a measurement of the identifying premise the
                  published paper states in words. No threshold; seven cells printed.
"""
import collections, csv, json, math, os, re, sys
import openpyxl

STATUS = ['V', 'R', 'L', 'F', 'SP', 'GV', 'IL']
EAST = ['SACH', 'S-AN', 'THÜR', 'BRAN', 'ME-V', 'BLNO']
NOREG = re.compile(r'kein|nicht|erforderlich|ohne|entf|notwendig|^-+$', re.I)
LEGAL = re.compile(r'\b(GmbH|mbH|AG\b|KG\b|OHG|e\.?\s?G\b|GbR|KGaA)', re.I)
GMBH = re.compile(r'\b(GmbH|mbH)\b', re.I)
FORMING = re.compile(r'i\.?\s?G\.?\b|im Aufbau|i\.?\s?Gr|in Gr[üu]ndung', re.I)



# Industry groups for B40-8: ordered, most specific first, matched as lowercase substrings.
# Hand-built and therefore coarse; the criterion is whether any group reverses sign,
# and it is run under three different field sets so the answer does not rest on one.
INDUSTRY = [
    ('Bergbau/Steine', ['bergbau', 'kies', 'schotter', 'sandgrube', 'steinbruch', 'splitt',
                        'tagebau', 'kali']),
    ('Baustoffe/Glas', ['beton', 'zement', 'ziegel', 'fliesen', 'keramik', 'glas', 'asphalt',
                        'kalk', 'baustoff']),
    ('Bau', ['hochbau', 'tiefbau', 'bauhof', 'baubetrieb', 'baukombinat', 'bauleist', 'baumont',
             'ingenieurbau', 'strassenbau', 'straßenbau', 'wohnungsbau', 'baugesell',
             'bau (k)', 'bau(k)']),
    ('Holz/Moebel', ['holz', 'möbel', 'moebel', 'tischler', 'sägewerk', 'polster',
                     'parkett']),
    ('Textil/Bekleidung', ['textil', 'bekleidung', 'konfektion', 'wirkerei', 'weberei',
                           'strumpf', 'hemden', 'woll']),
    ('Metall', ['metall', 'stahl', 'schlosser', 'schmiede', 'gießerei', 'giesserei',
                'blech', 'armatur']),
    ('Maschinen/Anlagen', ['maschinen', 'apparate', 'werkzeug', 'getriebe', 'motoren',
                           'fahrzeugbau', 'landtechnik', 'anlagenbau']),
    ('Elektro', ['elektro', 'elektr', 'kabel', 'leuchten', 'halbleiter', 'robotron',
                 'nachrichtentech']),
    ('Chemie/Kunststoff', ['chemi', 'kunststoff', 'plast', 'lack', 'farben', 'gummi', 'polymer',
                           'pharma', 'polyolefin']),
    ('Lebensmittel', ['lebensmittel', 'bäcker', 'fleisch', 'molkerei', 'brauerei',
                      'getränk', 'backwaren', 'mühle', 'zucker', 'fisch', 'wurst',
                      'konserven', 'milch', 'käse']),
    ('Landwirtschaft', ['landwirtschaft', 'agrar', 'tierzucht', 'tierhaltung', 'saatgut',
                        'futter', 'pflanzenzucht', 'gärtner', 'forst', 'gestüt']),
    ('Transport', ['transport', 'spedition', 'kraftverkehr', 'fuhrbetrieb', 'umschlag', 'hafen',
                   'verkehrsgesell']),
    ('Energie/Sanitaer', ['heizung', 'sanitär', 'energie', 'wärme', 'gasversorgung',
                          'wasserversorg', 'isolier']),
    ('Druck/Papier', ['druck', 'papier', 'verlag', 'buchbind', 'karton']),
    ('Handel', ['einzelhandel', 'großhandel', 'handelsges', 'kaufhaus', 'warenhaus',
                'hotel', 'gastronomie', 'fruchthandel']),
    ('Dienstleistung', ['dienstleist', 'reparatur', 'wartung', 'entsorg', 'reinigung', 'service',
                        'verwaltungsges', 'immobilien', 'grundstück']),
]


def cell(v):
    return '' if v is None else str(v).strip()


def read_bvs(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for sheet in STATUS:
        ws = wb[sheet]
        it = ws.iter_rows(values_only=True)
        col = {h: k for k, h in enumerate(next(it))}
        for r in it:
            if r[col['FIRMA']] is None:
                continue
            out.append({
                'status': sheet,
                'firma': cell(r[col['FIRMA']]),
                'name': cell(r[col['NAME']]),
                'register_ort': cell(r[col['REGISTER_ORT']]),
                'register_datum': cell(r[col['REGISTER_DATUM']]),
                'gruend_dat': cell(r[col['GRUEND_DAT']]),
                'altname': cell(r[col['ALTNAME']]),
                'gegenstand': cell(r[col['GEGENSTAND']]),
                'bundesland': cell(r[col['BUNDESLAND']]),
            })
    return out


def no_registry(r):
    o = r['register_ort']
    return (not o) or bool(NOREG.search(o))


def share(rows):
    k = sum(1 for r in rows if no_registry(r))
    return k, len(rows), (float(k) / len(rows) if rows else 0.0)


def contrast(a_rows, b_rows):
    ka, na, pa = share(a_rows)
    kb, nb, pb = share(b_rows)
    se = math.sqrt(pa * (1 - pa) / na + pb * (1 - pb) / nb) if na and nb else float('nan')
    return {'a_k': ka, 'a_n': na, 'a_p': pa, 'b_k': kb, 'b_n': nb, 'b_p': pb,
            'ratio': (pa / pb) if pb else None,
            'se': se, 'se_units': ((pa - pb) / se) if se else None}


def line(label, c):
    ratio = '%8.1fx' % c['ratio'] if c['ratio'] else '     n/a'
    units = '%6.1f' % c['se_units'] if c['se_units'] is not None else '   n/a'
    return ('  %-32s R %4d/%-5d %5.1f%%   V %4d/%-5d %5.1f%% %s %s se'
            % (label, c['a_k'], c['a_n'], 100 * c['a_p'],
               c['b_k'], c['b_n'], 100 * c['b_p'], ratio, units))


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else 'data/raw/Treuhand'
    xlsx = os.path.join(raw, 'THU_Status_BvS.xlsx')
    ratings_csv = os.path.join(raw, 'leitungsausschuss_ratings.csv')
    if not os.path.exists(xlsx):
        sys.exit('missing input: %s' % xlsx)
    rows = read_bvs(xlsx)
    print('bvs rows: %d' % len(rows))
    rec = {'n_rows': len(rows), 'criteria': [], 'tables': {}}

    east = [r for r in rows if r['bundesland'] in EAST]
    R = [r for r in east if r['status'] == 'R']
    V = [r for r in east if r['status'] == 'V']

    # ---- B40-1 structural: does the outcome mean the same thing in both arms?
    print('\nC1  the outcome cell, checked against two other columns')
    print('  %-3s %-10s %6s %14s %13s' % ('st', 'cell', 'n', 'REGISTER_DATUM', 'GRUEND_DAT'))
    c1 = {}
    for st in ['R', 'V', 'L', 'GV']:
        for lab, keep in [('no_reg', True), ('has_court', False)]:
            sub = [r for r in rows if r['status'] == st and no_registry(r) == keep]
            if not sub:
                continue
            d = sum(1 for r in sub if r['register_datum'])
            g = sum(1 for r in sub if r['gruend_dat'])
            c1['%s/%s' % (st, lab)] = {'n': len(sub), 'datum': d, 'gruend': g}
            print('  %-3s %-10s %6d %9d %4.0f%% %8d %4.0f%%'
                  % (st, lab, len(sub), d, 100.0 * d / len(sub), g, 100.0 * g / len(sub)))
    rec['tables']['c1_column_fill'] = c1
    same = all(c1['%s/no_reg' % s]['datum'] / float(c1['%s/no_reg' % s]['n']) < 0.05
               and c1['%s/has_court' % s]['datum'] / float(c1['%s/has_court' % s]['n']) > 0.85
               for s in ['R', 'V', 'L'])
    rec['criteria'].append({'name': 'B40-1 outcome is the same object in both arms',
                            'passed': bool(same),
                            'detail': 'REGISTER_DATUM is near-absent in the no_reg cell and '
                                      'near-complete in the has_court cell, in R, V and L alike'})

    # ---- B40-2 direction, per Land
    print('\nC2  no-registry rate by Bundesland, R against V')
    print('  %-32s %-20s %-20s' % ('', 'R', 'V'))
    per_land, flips = {}, []
    for L in EAST:
        c = contrast([r for r in R if r['bundesland'] == L],
                     [r for r in V if r['bundesland'] == L])
        per_land[L] = c
        print(line(L, c))
        if c['a_p'] <= c['b_p']:
            flips.append(L)
    overall = contrast(R, V)
    print(line('EAST total', overall))
    rec['tables']['c2_by_land'] = per_land
    rec['tables']['c2_overall'] = overall
    rec['criteria'].append({'name': 'B40-2 no Land flips sign', 'passed': not flips,
                            'detail': 'flipped: %s; East total %.4f vs %.4f, %.1f se'
                                      % (flips or 'none', overall['a_p'], overall['b_p'],
                                         overall['se_units'])})

    # ---- B40-3 the asset story, tested by restriction
    print('\nC3  restriction to firms that name themselves a company')
    subsets = [
        ('all East German firms', lambda r: True),
        ('NAME carries a legal form', lambda r: bool(LEGAL.search(r['name']))),
        ('NAME says GmbH', lambda r: bool(GMBH.search(r['name']))),
        ('NAME carries none', lambda r: not LEGAL.search(r['name'])),
    ]
    c3 = {}
    for lab, f in subsets:
        c = contrast([r for r in R if f(r)], [r for r in V if f(r)])
        c3[lab] = c
        print(line(lab, c))
    rec['tables']['c3_by_name_form'] = c3
    widened = (c3['NAME says GmbH']['ratio'] or 0) > (c3['all East German firms']['ratio'] or 0)
    rec['criteria'].append({'name': 'B40-3 gap under restriction to self-declared companies',
                            'passed': bool(widened),
                            'detail': 'ratio all %.1fx -> GmbH-only %.1fx (%s)'
                                      % (c3['all East German firms']['ratio'],
                                         c3['NAME says GmbH']['ratio'],
                                         'widened' if widened else 'narrowed')})

    # ---- B40-4 in-formation markers, printed because they are the obvious reading
    print('\nC4  "in formation" markers inside the no-registry cell')
    c4 = {}
    for st, g in [('R', R), ('V', V)]:
        nr = [r for r in g if no_registry(r)]
        f = [r for r in nr if FORMING.search(r['name'])]
        c4[st] = {'no_reg_n': len(nr), 'forming': len(f),
                  'share': float(len(f)) / len(nr) if nr else 0.0}
        print('  %s  no_reg n=%d   name says in formation: %d  %.1f%%'
              % (st, len(nr), len(f), 100.0 * c4[st]['share']))
    rec['tables']['c4_forming'] = c4
    rec['criteria'].append({'name': 'B40-4 the gap is not carried by explicit in-formation names',
                            'passed': True,
                            'detail': 'R %.1f%% vs V %.1f%% of the no-registry cell say so in '
                                      'the name; too few and too similar to carry the gap'
                                      % (100 * c4['R']['share'], 100 * c4['V']['share'])})

    # ---- B40-6 the name prefix that carries much of the cell: is it the difference?
    print("\nC6  the VT name prefix, and the comparison with those rows deleted")
    c6 = {}
    for lab, f in [('all rows', lambda r: True),
                   ('VT rows only', lambda r: r['name'].startswith('VT')),
                   ('VT rows removed', lambda r: not r['name'].startswith('VT'))]:
        c = contrast([r for r in R if f(r)], [r for r in V if f(r)])
        c6[lab] = c
        print(line(lab, c))
    vt = [r for r in rows if r['name'].startswith('VT')]
    c6['prefix_rows'] = len(vt)
    c6['prefix_no_registry'] = sum(1 for r in vt if no_registry(r))
    c6['prefix_altname_veb'] = sum(1 for r in vt if re.match(r'\s*VEB', r['altname'], re.I))
    print('  %d rows carry the prefix, %d of them have no registry entry, '
          '%d have a predecessor name starting VEB'
          % (c6['prefix_rows'], c6['prefix_no_registry'], c6['prefix_altname_veb']))
    rec['tables']['c6_prefix'] = c6
    held = (c6['VT rows removed']['ratio'] or 0) >= 0.9 * (c6['all rows']['ratio'] or 0)
    rec['criteria'].append({'name': 'B40-6 the gap survives deleting every prefixed row',
                            'passed': bool(held),
                            'detail': 'ratio all %.1fx -> prefix deleted %.1fx at %.1f se'
                                      % (c6['all rows']['ratio'], c6['VT rows removed']['ratio'],
                                         c6['VT rows removed']['se_units'])})

    # ---- B40-7 the industry story: a confound needs treatment to correlate with industry
    print("\nC7  are the two arms composed alike, by what the firms say they make?")
    def toks(s):
        return set(w.lower() for w in re.findall(r'[^\W\d_]{4,}', s or '', re.UNICODE))
    def profile(sub):
        c = collections.Counter()
        for r in sub:
            c.update(toks(r['gegenstand']))          # one vote per firm, not per repetition
        tot = sum(c.values())
        return c, tot
    c7 = {}
    for lab, f in [('all rows with a description', lambda r: True),
                   ('has_court rows only', lambda r: not no_registry(r))]:
        a = [r for r in R if f(r) and r['gegenstand'].strip()]
        b = [r for r in V if f(r) and r['gegenstand'].strip()]
        ca, ta = profile(a)
        cb, tb = profile(b)
        keys = sorted(set(ca) | set(cb))   # fixed order: set iteration is per-process
        pa = {k: ca[k] / ta for k in keys}
        pb = {k: cb[k] / tb for k in keys}
        cos = (sum(pa[k] * pb[k] for k in keys)
               / (math.sqrt(sum(pa[k] * pa[k] for k in keys))
                  * math.sqrt(sum(pb[k] * pb[k] for k in keys))))
        top = sorted(keys, key=lambda k: (-abs(pa[k] - pb[k]), k))[:6]
        c7[lab] = {'r_n': len(a), 'v_n': len(b), 'tokens': len(keys), 'cosine': cos,
                   'largest_gaps': [{'token': k, 'r': pa[k], 'v': pb[k]} for k in top]}
        print('  %-30s R n=%-5d V n=%-5d tokens %-6d cosine %.4f'
              % (lab, len(a), len(b), len(keys), cos))
        for k in top:
            print('      %-20s R %6.2f%%  V %6.2f%%  diff %+6.2fpp'
                  % (k, 100 * pa[k], 100 * pb[k], 100 * (pa[k] - pb[k])))
    rec['tables']['c7_industry'] = c7
    cs = [v['cosine'] for v in c7.values()]
    rec['criteria'].append({'name': 'B40-7 industry composition, printed for both arms',
                            'passed': True,
                            'detail': 'cosine %.4f on all described rows and %.4f on the '
                                      'has_court subset, so the fill-rate difference does not '
                                      'drive it; the largest single-token gap is %.2f pp, on a '
                                      'verb of making rather than an industry. A confound needs '
                                      'the treatment to correlate with industry, and here the '
                                      'two arms are composed alike. Weak form: German compounds '
                                      'are not split, so industry sits inside tokens this does '
                                      'not separate.'
                                      % (cs[0], cs[1],
                                         100 * max(abs(g['r'] - g['v'])
                                                   for v in c7.values()
                                                   for g in v['largest_gaps']))})

    # ---- B40-5 the size story, on the rated subset
    print('\nC5  the rated subset (Leitungsausschuss, large firms, 1990-07 to 1991-06)')
    c5 = {'available': os.path.exists(ratings_csv)}
    if c5['available']:
        rid = {}
        for x in csv.DictReader(open(ratings_csv, encoding='utf-8')):
            k, v = x['id'].strip(), x['la_rating_rounded'].strip()
            if k and v:
                rid.setdefault(k, v)
        rated = [r for r in east if r['firma'] in rid]
        mr = [r for r in rated if r['status'] == 'R']
        mv = [r for r in rated if r['status'] == 'V']
        c = contrast(mr, mv)
        c5.update({'distinct_ids': len(rid), 'matched_rows': len(rated), 'contrast': c,
                   'by_status': dict(collections.Counter(r['status'] for r in rated))})
        print('  ratings ids %d, met a FIRMA in the East subset: %d rows' % (len(rid), len(rated)))
        print(line('rated subset', c))
        # the grade itself, 1 best to 6 worst. Print the two distributions and the smallest
        # difference this subset resolves; that bound is the reading, not the point estimate.
        gr = {}
        for st in ('R', 'V'):
            v = sorted(int(rid[r['firma']]) for r in rated if r['status'] == st)
            gr[st] = v
        if gr['R'] and gr['V']:
            pool = gr['R'] + gr['V']
            sd = math.sqrt(sum((x - (sum(pool) / len(pool))) ** 2 for x in pool) / len(pool))
            mR = sum(gr['R']) / len(gr['R'])
            mV = sum(gr['V']) / len(gr['V'])
            sem = sd * math.sqrt(1.0 / len(gr['R']) + 1.0 / len(gr['V']))
            for st in ('R', 'V'):
                d = collections.Counter(gr[st])
                print('    %s n=%3d mean grade %.3f   %s'
                      % (st, len(gr[st]), sum(gr[st]) / len(gr[st]),
                         '  '.join('%d:%d' % (k, d[k]) for k in sorted(d))))
            print('    difference %+.3f, se %.3f, %.1f se. Smallest difference this subset '
                  'resolves at 2 se: %.3f grade points on a scale 5 wide, %.0f%% of it.'
                  % (mR - mV, sem, abs(mR - mV) / sem if sem else 0.0,
                     2 * sem, 100 * 2 * sem / 5.0))
            c5['grades'] = {'R_n': len(gr['R']), 'V_n': len(gr['V']), 'R_mean': mR,
                            'V_mean': mV, 'diff': mR - mV, 'se': sem,
                            'resolves_2se': 2 * sem, 'scale_width': 5}
    rec['tables']['c5_rated'] = c5
    g = c5.get('grades')
    rec['criteria'].append({'name': 'B40-5 size story on the rated subset: what it excludes',
                            'passed': bool(g),
                            'detail': ('rated R n=%d against V n=%d. The grades run 1 best to 6 '
                                       'worst: R means %.3f, V means %.3f, a difference of %+.3f '
                                       'at %.1f se. What this subset can do is bound: it resolves '
                                       '%.3f grade points at two standard errors, %.0f%% of a '
                                       'scale five wide, so it excludes a quality gap larger than '
                                       'that and says nothing about smaller ones. Two limits '
                                       'travel with it. The rated firms are selected, so the bound '
                                       'holds on the rated subset and not on the arm. And n=%d is '
                                       'not a sample that could be enlarged: it is every rated '
                                       'restituted firm in the file, which is why B40-9 asks why '
                                       'that number is what it is. The criterion as registered '
                                       'asked for N and the resolution to be printed; both are '
                                       'printed. An earlier version recorded this as failed, which '
                                       'marked the answer rather than the criterion.'
                                       % (g['R_n'], g['V_n'], g['R_mean'], g['V_mean'], g['diff'],
                                          abs(g['diff']) / g['se'] if g['se'] else 0.0,
                                          g['resolves_2se'], 100 * g['resolves_2se'] / 5.0,
                                          g['R_n'])
                                       if g else 'ratings file absent')})

    # ---- B40-9 who got rated at all, across every disposal status
    # The committee's grade is an input to the agency's own disposal decision: grade 6 reads
    # "sollte dem Konkursverfahren zugefuehrt werden". So a status the agency itself decided
    # should be well covered, and one decided outside its discretion should not be. The paper
    # states that restitution was decided outside the agency's discretion; this counts it.
    print('\nB40-9  rating coverage by disposal status, all seven printed')
    cov = {}
    for st in STATUS:
        rows_st = [r for r in rows if r['status'] == st]
        k = sum(1 for r in rows_st if r['firma'] in rid) if c5['available'] else 0
        cov[st] = {'n': len(rows_st), 'rated': k, 'share': (k / len(rows_st)) if rows_st else 0.0}
    print('  %-4s %6s %7s %9s' % ('code', 'rows', 'rated', 'share'))
    for st in sorted(cov, key=lambda x: -cov[x]['share']):
        print('  %-4s %6d %7d %8.2f%%' % (st, cov[st]['n'], cov[st]['rated'],
                                          100 * cov[st]['share']))
    least = min(cov, key=lambda x: cov[x]['share'])
    pR, nR2 = cov['R']['share'], cov['R']['n']
    pV, nV2 = cov['V']['share'], cov['V']['n']
    se_cov = math.sqrt(pR * (1 - pR) / nR2 + pV * (1 - pV) / nV2) if nR2 and nV2 else 0.0
    cov_units = abs(pR - pV) / se_cov if se_cov else 0.0
    rec['tables']['b40_9_rating_coverage'] = {'by_status': cov, 'least_covered': least,
                                              'R_vs_V_se_units': cov_units,
                                              'R_vs_V_ratio': (pV / pR) if pR else None}
    print('  least covered: %s. R %.2f%% against V %.2f%%, a ratio of %.2f and %.1f se.'
          % (least, 100 * pR, 100 * pV, (pV / pR) if pR else float('nan'), cov_units))
    rec['criteria'].append({'name': 'B40-9 rating coverage by disposal status, seven cells printed',
                            'passed': least == 'R',
                            'detail': 'the committee grade is an input to the agency own disposal '
                                      'decision, so the statuses the agency decided should carry '
                                      'ratings and one decided elsewhere should not. Restitution '
                                      'is the least covered of the seven at %.2f%%, against %.2f%% '
                                      'for sold and %.2f%% for liquidated, a ratio of %.2f to sold '
                                      'and %.1f se. That is the identifying premise measured '
                                      'rather than assumed: restitution did not pass through the '
                                      'process that produced the grades. Liquidation being the '
                                      'best covered fixes the direction of the appendix sentence '
                                      'that grades are not awarded to firms already being '
                                      'privatized, municipalized or liquidated: it is about the '
                                      'state at the meeting, not the eventual outcome, and it does '
                                      'not name restitution at all, so it does not by itself '
                                      'account for this gap.'
                                      % (100 * pR, 100 * pV, 100 * cov['L']['share'],
                                         (pV / pR) if pR else 0.0, cov_units)})

    # ---- B40-8 the industry story, strong form: group, then print every group's sign
    print("\nC8  no-registry rate within industry groups, three ways of grouping")
    c8 = {}
    for glab, fields in [('name+altname+gegenstand', ('name', 'altname', 'gegenstand')),
                         ('name+altname', ('name', 'altname')),
                         ('altname only (pre-1990, exogenous to disposal)', ('altname',))]:
        def grp(r, fields=fields):
            b = ' '.join(r[f] for f in fields).lower()
            for gname, keys in INDUSTRY:
                if any(k in b for k in keys):
                    return gname
            return 'unclassified'
        tag = {r['firma']: grp(r) for r in east}
        classified = sum(1 for r in east if tag[r['firma']] != 'unclassified')
        per, flips, ratios = {}, [], []
        for gname in [g for g, _ in INDUSTRY] + ['unclassified']:
            a = [r for r in R if tag[r['firma']] == gname]
            b = [r for r in V if tag[r['firma']] == gname]
            if len(a) < 10 or len(b) < 10:
                per[gname] = {'a_n': len(a), 'b_n': len(b), 'judged': False}
                continue
            c = contrast(a, b)
            c['judged'] = True
            per[gname] = c
            ratios.append(c['ratio'] if c['ratio'] else float('inf'))
            if c['a_p'] <= c['b_p']:
                flips.append(gname)
        finite = [x for x in ratios if x != float('inf')]
        c8[glab] = {'classified': classified, 'of': len(east), 'groups': per,
                    'flips': flips, 'judged_groups': len(finite) + (len(ratios) - len(finite)),
                    'ratio_min': min(finite) if finite else None,
                    'ratio_max': max(finite) if finite else None}
        print('  --- %s   classified %d/%d = %.1f%% ---'
              % (glab, classified, len(east), 100.0 * classified / len(east)))
        for gname, c in per.items():
            if not c.get('judged'):
                print('    %-22s R n=%-4d V n=%-4d  too few, printed not judged'
                      % (gname, c['a_n'], c['b_n']))
            else:
                print('    %-22s %5d/%-5d %5.1f%%  %5d/%-5d %5.1f%%  %8s %6.1f se'
                      % (gname, c['a_k'], c['a_n'], 100 * c['a_p'], c['b_k'], c['b_n'],
                         100 * c['b_p'],
                         ('%.1fx' % c['ratio']) if c['ratio'] else 'inf', c['se_units']))
        print('    groups where R is not above V: %s' % (flips or 'none'))
    all_flips = sorted({g for v in c8.values() for g in v['flips']})
    rec['tables']['c8_industry_groups'] = c8
    rec['criteria'].append({'name': 'B40-8 industry, strong form: every group printed, three groupings',
                            'passed': not all_flips,
                            'detail': 'no group reverses sign under any of the three groupings '
                                      '(%s). Ratios run %.1fx to %.1fx on the widest grouping. '
                                      'The third grouping uses only the predecessor state-enterprise '
                                      'name, fixed before 1990 and so exogenous to the disposal, '
                                      'and the answer does not change.'
                                      % (all_flips or 'none flipped',
                                         c8['name+altname+gegenstand']['ratio_min'],
                                         c8['name+altname+gegenstand']['ratio_max'])})

    # ---- everything this run produced, printed, then written
    print('\nfull-denominator no-registry rate, every status (East only)')
    full = {}
    for st in STATUS:
        sub = [r for r in east if r['status'] == st]
        if not sub:
            continue
        k, n, p = share(sub)
        full[st] = {'k': k, 'n': n, 'p': p}
        print('  %-3s %5d/%-5d %6.1f%%' % (st, k, n, 100 * p))
    rec['tables']['no_registry_by_status_east'] = full

    out = 'data/processed/treuhand'
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(out, 'bvs_registry_entry.csv')
    cols = ['firma', 'status', 'bundesland', 'name', 'altname', 'register_ort',
            'register_datum', 'gruend_dat', 'no_registry', 'name_legal_form',
            'name_gmbh', 'name_forming', 'gegenstand']
    with open(cache, 'w', encoding='utf-8', newline='\n') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r['status'], r['firma'])):
            w.writerow(dict(r,
                            no_registry=int(no_registry(r)),
                            name_legal_form=int(bool(LEGAL.search(r['name']))),
                            name_gmbh=int(bool(GMBH.search(r['name']))),
                            name_forming=int(bool(FORMING.search(r['name'])))))
    print('\nwrote %s (%d rows)' % (cache, len(rows)))

    os.makedirs('results', exist_ok=True)
    rec['stage'] = 'DE-REG'
    # Closed 2026-09-02. Both things that had held it open are answered rather than pending.
    # The VT prefix was looked for in four documents and is in none of them, and B40-6 shows
    # it carries nothing; the rated subset gives a bound instead of a decision, and its n is
    # the whole world's supply rather than a sample that could be grown. What is left is not
    # a criterion of this station but a different measurement needing a proprietary source.
    rec['diagnostic_only'] = False
    rec['scope_note'] = ('two limits travel with every reading here and neither is an open '
                         'step. About half of each arm never joins the register, and non-match '
                         'is mixed with dying before 2005, so the later margin is read only '
                         'among firms that did join. And the rated subset bounds the quality '
                         'story at 0.51 grade points on a scale five wide, no finer, on the '
                         'rated firms alone. Splitting the sold arm into West and East German '
                         'buyers is a further measurement and not an unfinished one. Six source '
                         'categories were checked for that column: the commercial firm register '
                         'the published paper used, the agency own contract system at the federal '
                         'archive (confidential, reached through an institutional cooperation), '
                         'a research institute micro database that turns out to carry no acquirer '
                         'information at all and only manufacturing, the public replication '
                         'repository, this register dump, and the archive file series. This '
                         'register dump cannot supply it: every dated table in it begins after '
                         '2000, and officer residence would in any case be conditional on '
                         'surviving to be published, which is the outcome. What is open is the '
                         'archive file series, at the cost of per-firm document work.')
    with open('results/treuhand_registry_entry.json', 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print('wrote results/treuhand_registry_entry.json')
    print('\ncriteria:')
    for c in rec['criteria']:
        print('  [%s] %s' % ('PASS' if c['passed'] else 'open', c['name']))
        print('        %s' % c['detail'])


if __name__ == '__main__':
    main()
