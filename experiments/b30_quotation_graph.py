"""B30-1 / B30-5 chunk one: the quotation graph, built only from published edges.

The hard condition, added to the design after B29-3: who watches whose price must
be WRITTEN DOWN by a party, not inferred by the analyst. One class of carrier
prints it: a retailer's price-match policy names the competitors it will match.
That is a directed edge authored by the source node itself.

Edge direction: A -> B means A has published that it watches B's price. So B is
upstream and A is downstream, and a price move travels along the arrow backwards.

Tier is recorded per node. An out-edge list from the retailer's own policy page is
official. A claim that a retailer has NO policy rests on third-party guides plus
the absence of an official page, which is weaker, and is marked.
"""
import itertools

# node -> (out-edges, tier, note)
GRAPH = {
    "Best Buy": (["Abt", "Amazon", "Apple", "B&H Photo Video", "BJ's Wholesale Club",
                  "BrandsMart USA", "Costco", "Crutchfield", "Dick's Sporting Goods",
                  "Home Depot", "Lowe's", "Menards", "Micro Center",
                  "Nebraska Furniture Mart", "P.C. Richard", "RC Willey",
                  "Sam's Club", "Target", "Walmart"],
                 "official", "qualified competitors page, read 2026-08-30"),
    "Home Depot": (["Lowe's", "Menards", "Amazon", "Walmart", "Best Buy", "Target"],
                 "archived official page",
                 "named in a bulleted list; also an unnamed set of local stores; "
                 "excludes eBay, Wayfair, Costco, Sam's Club as auction, marketplace "
                 "or membership sites. Snapshot supplied by hand and dated by "
                 "them to 2025-08-22; the captured HTML carries an embedded Wayback "
                 "rewrite stamp of 2025-12-07, and the two are not reconciled here. "
                 "The live page did not serve the policy body on 2026-08-30."),
    "Lowe's":   (["Amazon"], "official",
                 "names Amazon first-party only; also an unnamed set of local "
                 "retailers; excludes membership wholesalers and marketplaces"),
    "Target":   ([], "official + trade press",
                 "matched Amazon and Walmart from 2013; ended 2025-07-28"),
    "Amazon":   ([], "official, user-verified",
                 "\"We do not offer price matching for items sold on Amazon.com\""),
    "Walmart":  ([], "official, dated 2023-06-07",
                 "policy lists what it does NOT match, first item \"Competitors' prices\""),
    "Costco":   ([], "official",
                 "\"Costco does not price match with other businesses or retailers.\""),
}

# The self edge: does the seller reconcile its own channels' prices? Published,
# and it varies. This is a dimension the external edge lists do not carry.
SELF_EDGE = {
    "Best Buy":   (True,  "matches its online and app prices on in-store purchases "
                          "and its in-store prices on online and app purchases"),
    "Home Depot": (True,  "matches homedepot.com, plus a 30-day price adjustment there"),
    "Target":     (True,  "after 2025-07-28 this is the ONLY edge it keeps: "
                          "\"only match prices for items sold in-store at Target or "
                          "on Target.com\""),
    "Lowe's":     (False, "excludes \"Prices from one Lowe's store location to another\""),
    "Costco":     (False, "\"Costco does not price match Costco warehouse prices for "
                          "Costco.com purchases\", with the stated reason that "
                          "Costco.com prices embed shipping and handling that "
                          "warehouse prices do not"),
    "Walmart":    (False, "excludes both \"Items purchased from Walmart.com that later "
                          "decrease in price\" and \"Items offered in Walmart stores\""),
    "Amazon":     (False, "no policy at all"),
}
TARGET_PRE = ["Amazon", "Walmart"]        # Target's out-edges before 2025-07-28

# Dated withdrawals of the out-edge, that is, a node ceasing to watch anyone.
# Source: Modern Retail, Mitchell Parton, 2025-08-07, plus each party's own policy.
# The pre-period edge LISTS are not recovered; only the fact and date of removal.
WITHDRAWALS = [
    (2016, "Amazon",
     "discontinued post-purchase price adjustments against other retailers, "
     "televisions excepted"),
    (2017, "Walmart", "stopped matching competitors at checkout"),
    (2019, "Walmart",
     "discontinued Savings Catcher, the automatic post-purchase comparison; "
     "stated reason: \"Walmart's prices win most often when you submit your "
     "receipts, which tells us that the program's intent has been met\""),
    (2025, "Target",
     "ended competitor matching on 07-28, keeping only its own two channels; "
     "stated reason: \"We've found our guests overwhelmingly price match Target "
     "and not other retailers, which reflects the great value and trust in "
     "pricing consumers see across our assortment and deals\""),
]
UNCOLLECTED = ["Micro Center", "B&H Photo Video", "Abt", "Menards",
               "P.C. Richard", "Crutchfield", "Apple", "Dick's Sporting Goods",
               "BrandsMart USA", "Nebraska Furniture Mart", "RC Willey",
               "BJ's Wholesale Club", "Sam's Club"]


def edges(state="now"):
    E = []
    for a, (outs, _, _) in GRAPH.items():
        o = TARGET_PRE if (a == "Target" and state == "pre") else outs
        E += [(a, b) for b in o]
    return E


def degrees(E, nodes):
    out = {n: 0 for n in nodes}
    ind = {n: 0 for n in nodes}
    for a, b in E:
        out[a] = out.get(a, 0) + 1
        ind[b] = ind.get(b, 0) + 1
    return out, ind


def find_cycle(E):
    adj = {}
    for a, b in E:
        adj.setdefault(a, []).append(b)
    colour, stack = {}, []
    def dfs(u):
        colour[u] = 1; stack.append(u)
        for v in adj.get(u, []):
            if colour.get(v) == 1:
                return stack[stack.index(v):] + [v]
            if colour.get(v, 0) == 0:
                c = dfs(v)
                if c: return c
        colour[u] = 2; stack.pop()
        return None
    for u in list(adj):
        if colour.get(u, 0) == 0:
            c = dfs(u)
            if c: return c
    return None


def main():
    for state in ("pre", "now"):
        E = edges(state)
        nodes = sorted({x for e in E for x in e} | set(GRAPH))
        out, ind = degrees(E, nodes)
        label = "before 2025-07-28" if state == "pre" else "after 2025-07-28"
        print(f"\n=== quotation graph, {label}: {len(nodes)} nodes, {len(E)} published edges")
        print(f"  {'node':26} {'out':>4} {'in':>3}  role")
        for n in sorted(nodes, key=lambda x: (-ind[x], -out[x], x)):
            role = ("SINK, watched and watching nobody" if ind[n] > 0 and out[n] == 0
                    else "source, watches and is unwatched" if out[n] > 0 and ind[n] == 0
                    else "interior" if out[n] and ind[n] else "isolated")
            print(f"  {n:26} {out[n]:4d} {ind[n]:3d}  {role}")
        c = find_cycle(E)
        print(f"  cycle present: {c if c else 'NONE, the graph is a DAG'}")
        print(f"  b1 on the published edges = E - V + C = "
              f"{len(E)} - {len(nodes)} + components, and it is 0 for a DAG that is "
              f"a forest; here E > V so b1 counts undirected cycles, none of which "
              f"are directed")

    E = edges("now")
    adj = {}
    for a, b in E: adj.setdefault(a, set()).add(b)
    two = sorted({tuple(sorted((a, b))) for a in adj for b in adj[a]
                  if b in adj and a in adj[b]})
    print(f"\ndirected 2-cycles (each is a closable loop, b1 contribution 1 each):")
    for a, b in two: print(f"  {a} <-> {b}")
    print(f"  count {len(two)}")
    nodes = sorted({x for e in E for x in e} | set(GRAPH))
    on_cycle = {x for p in two for x in p}
    print(f"  nodes on some closable loop: {len(on_cycle)} of {len(nodes)}")
    print(f"  nodes on no loop at all:     {len(nodes)-len(on_cycle)}")
    # eccentricity from the sink
    print("\nhop distance to Amazon along published edges:")
    from collections import deque
    rev = {}
    for a, b in E: rev.setdefault(b, set()).add(a)
    dist = {"Amazon": 0}; q = deque(["Amazon"])
    while q:
        u = q.popleft()
        for v in rev.get(u, ()):
            if v not in dist:
                dist[v] = dist[u] + 1; q.append(v)
    for n in sorted(nodes, key=lambda x: (dist.get(x, 99), x)):
        d = dist.get(n)
        print(f"  {n:26} {'unreachable' if d is None else d}")
    print(f"  max finite hop distance: {max(v for v in dist.values())}")

    print("\nthe self edge: does the seller reconcile its own two channels?")
    yes = [k for k, v in SELF_EDGE.items() if v[0]]
    no = [k for k, v in SELF_EDGE.items() if not v[0]]
    for k, (v, note) in SELF_EDGE.items():
        print(f"  {k:12} {'CLOSES' if v else 'REFUSES':8} {note[:88]}")
    print(f"  closes {len(yes)}, refuses {len(no)}, every one of them published")
    print("  note: this is independent of the external out-degree. Costco and Walmart")
    print("  have out-degree 0 AND refuse the self edge. Target has out-degree 0 and")
    print("  keeps only the self edge. Best Buy has out-degree 19 and closes it.")

    print("\nhow the sinks were made: dated withdrawals of the out-edge")
    for yr, who, why in WITHDRAWALS:
        print(f"  {yr}  {who:9} {why[:96]}")
    print("  every one of these three parties is now a top-in-degree node in the")
    print("  graph above. They became anchors by ceasing to watch while continuing")
    print("  to be watched, and the sequence runs over nine years.")
    print("\n  the shape of the stated reasons, which is the same in both cases on")
    print("  record: the party removing the check cites the check's own past results")
    print("  as the reason it is no longer needed. Once the edge is gone that claim")
    print("  cannot be tested, so the justification is self sealing.")

    print("\nuncollected out-edge lists:")
    for n in UNCOLLECTED:
        print(f"  {n}")
    print("\n  Resolved 2026-08-30 from an archived Home Depot page: it names six")
    print("  competitors outright, Best Buy among them, so Best Buy <-> Home Depot")
    print("  closes and the DAG reading is dead. Lowe's still does not name Home Depot.")


if __name__ == "__main__":
    main()
