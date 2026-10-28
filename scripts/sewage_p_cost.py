"""Cost of recovering phosphorus from sewage, from MLIT's own figures.

Source for every number: 国土交通省 都市・地域整備局下水道部
『下水道におけるリン資源化の手引き』(2010-03), https://www.mlit.go.jp/common/000113958.pdf
  - cost functions: §3.4 (1), eq. [1]-[12]   (million yen; O&M for HAP/MAP excludes labour,
    MAP-digestate also excludes repairs, so those costs are LOW estimates)
  - annualisation: eq. [14], 15-year life, 4.0 % interest (the guide's own example)
  - phosphorus recovered: tables 16-2, 16-5(MAP), 16-7, 16-10 (inflow P 5 mg/l)
  - comparison prices, all from the same guide:
      phosphate rock import price 22,000-46,000 yen/t after 2008 (§2, trade statistics),
        at 35 % P2O5 (rock grade in the guide's process diagram for high-analysis compound);
      what buyers would pay for recovered phosphate: about 20,000 yen/t (phosphoric-acid plants,
        JA Zen-Noh, trading houses) and 30,000-50,000 yen/t (fertiliser plants) (§5.1 hearing),
        taken here for the ash-extracted calcium phosphate at 30 % P2O5 (table 16-7);
      JA retail phosphate fertiliser to farmers ~430-550 yen/kg P2O5 (table 24-8), for reference only:
        it includes manufacturing and margins.
All yen are 2008-2010 yen, so costs and prices are from the same years.
"""

P_PER_P2O5 = 0.437
CRF = 0.04 * 1.04**15 / (1.04**15 - 1)   # capital recovery factor, eq. [14]

def annual(capex, om):            # million yen / year
    return capex * CRF + om

# (method, scale label, capex, O&M, P recovered t/yr)
rows = []
for q, p1, p2 in [(10, 1.3, 2.0), (50, 6.8, 10.0), (100, 13.5, 19.9), (500, 67.8, 99.4)]:
    c, o = 6.0893 * q + 35.771, 0.1374 * q + 0.1797                 # [1][2]
    rows.append(("HAP, return water", f"{q}k m3/day", c, o, p2))     # case 2: with digestion (more P)
for q, p in [(10, 1.5), (50, 7.5), (100, 15.1), (500, 75.4)]:
    c, o = 1.4529 * q + 46.877, 0.0339 * q + 0.2515                 # [3][4], case 4
    rows.append(("HAP, dewatering filtrate", f"{q}k m3/day", c, o, p))
for q, p in [(10, 1.8), (50, 9.1), (100, 18.3), (500, 91.5)]:
    c, o = 2.2591 * q + 244.00, 0.0684 * q + 0.7022                 # [5][6], case 2
    rows.append(("MAP, dewatering filtrate", f"{q}k m3/day", c, o, p))
for q, p in [(10, 5.6), (50, 27.7), (100, 55.5), (500, 277.3)]:
    c, o = 1.9888 * q + 107.98, 0.1334 * q + 0.6595                 # [7][8], case 3
    rows.append(("MAP, digested sludge", f"{q}k m3/day", c, o, p))
for q, ash, p in [(50, 540, 35.4), (100, 1080, 70.8), (500, 5402, 353.8), (1000, 10804, 707.6)]:
    c, o = 0.2076 * ash + 167.05, 0.0192 * ash + 3.343              # [9][10]
    rows.append(("ash, alkali extraction", f"{q}k m3/day", c, o, p))
for q, ash, p in [(100, 1110, 94.5), (500, 5550, 472.5), (1000, 11100, 945.1), (5000, 55500, 4725.3)]:
    c, o = 0.1420 * ash + 979.24, 0.0352 * ash + 122.45             # [11][12]
    rows.append(("ash, partial reduction melting", f"{q}k m3/day", c, o, p))

def per_kg_p(yen_per_t, p2o5):
    return yen_per_t / (1000 * p2o5 * P_PER_P2O5)

rock = per_kg_p(22_000, 0.35), per_kg_p(46_000, 0.35)
buyer = per_kg_p(20_000, 0.30), per_kg_p(50_000, 0.30)
retail = 430 / P_PER_P2O5, 550 / P_PER_P2O5
print(f"imported phosphate rock      {rock[0]:6.0f}-{rock[1]:.0f} yen/kg P")
print(f"buyers for recovered P       {buyer[0]:6.0f}-{buyer[1]:.0f} yen/kg P")
print(f"JA retail fertiliser (ref.)  {retail[0]:6.0f}-{retail[1]:.0f} yen/kg P")
print()
print(f"{'method':32} {'plant':>12} {'P t/yr':>8} {'yen/kg P':>10} {'x rock':>10} {'x buyer':>10}")
for m, s, c, o, p in rows:
    y = annual(c, o) * 1e6 / (p * 1000)
    print(f"{m:32} {s:>12} {p:8.1f} {y:10,.0f} {y / rock[1]:5.1f}-{y / rock[0]:<4.1f} {y / buyer[1]:5.1f}-{y / buyer[0]:.1f}")
