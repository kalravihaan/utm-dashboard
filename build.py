import pandas as pd
import numpy as np
import json

# ── LOAD ──────────────────────────────────────────────────────────────────────
df = pd.read_excel('data/master_sales.xlsx')
df = df[['Brand','Article Type','Style id','Cost','Total Sales Qty','Revenue',
         'Inventory','Total Return Qty','Month','Month Numbering','ROS']].copy()
df = df[df['Brand'] != 'SZN'].copy()
df['Brand'] = df['Brand'].str.strip()
df['Article Type'] = df['Article Type'].fillna('Unknown')
df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce')
df['Inventory'] = pd.to_numeric(df['Inventory'], errors='coerce').fillna(0)
df['Month Numbering'] = pd.to_numeric(df['Month Numbering'], errors='coerce')
df['Style id'] = df['Style id'].astype(str).str.strip()

MONTH_ORDER = ['April','May','June','July','August','September',
               'October','November','December','January','February','March']
TIER_ORDER  = ['Very Fast','Fast','Moderate','Slow','Dead']
TIER_RANGES = {
    'Very Fast':'ROS > 1.5 / day',
    'Fast':     'ROS 0.7 – 1.5 / day',
    'Moderate': 'ROS 0.3 – 0.7 / day',
    'Slow':     'ROS > 0 – 0.3 / day',
    'Dead':     'ROS = 0 (no sales)',
}
TIER_CFG = {
    'Very Fast': ('#065f46','#ecfdf5','#059669','#a7f3d0'),
    'Fast':      ('#14532d','#f0fdf4','#16a34a','#bbf7d0'),
    'Moderate':  ('#78350f','#fffbeb','#d97706','#fde68a'),
    'Slow':      ('#7f1d1d','#fef2f2','#dc2626','#fecaca'),
    'Dead':      ('#374151','#f9fafb','#6b7280','#e5e7eb'),
}

def tier(ros):
    if ros == 0:     return 'Dead'
    elif ros <= 0.3: return 'Slow'
    elif ros <= 0.7: return 'Moderate'
    elif ros <= 1.5: return 'Fast'
    else:            return 'Very Fast'

# ── STYLE AGG ─────────────────────────────────────────────────────────────────
style_df = df.groupby(['Brand','Style id','Article Type']).agg(
    TotalSales=('Total Sales Qty','sum'),
    TotalRevenue=('Revenue','sum'),
    TotalReturns=('Total Return Qty','sum'),
    AvgCost=('Cost','mean'),
    AvgInventory=('Inventory','mean'),
    ROS=('ROS','max'),
).reset_index()
style_df['ReturnPct'] = np.where(
    style_df['TotalSales'] > 0,
    (style_df['TotalReturns'] / style_df['TotalSales'] * 100).round(1), 0)
style_df['Tier'] = style_df['ROS'].apply(tier)
style_df['AvgCost'] = style_df['AvgCost'].fillna(0).round(0).astype(int)
style_df['AvgInventory'] = style_df['AvgInventory'].round(0).astype(int)

# ── MONTHLY AGG ───────────────────────────────────────────────────────────────
def get_monthly(brand=None):
    src = df if not brand else df[df['Brand']==brand]
    m = src.groupby(['Month','Month Numbering']).agg(
        Sales=('Total Sales Qty','sum'),
        Revenue=('Revenue','sum'),
        Returns=('Total Return Qty','sum'),
    ).reset_index().sort_values('Month Numbering')
    m['ReturnPct'] = (m['Returns']/m['Sales']*100).round(1)
    # reorder to FY26 month order
    ordered = []
    for mo in MONTH_ORDER:
        row = m[m['Month']==mo]
        if len(row):
            ordered.append(row.iloc[0])
    return pd.DataFrame(ordered) if ordered else m

# ── ARTICLE AGG ───────────────────────────────────────────────────────────────
def get_art(brand=None):
    src = df if not brand else df[df['Brand']==brand]
    a = src.groupby('Article Type').agg(
        Sales=('Total Sales Qty','sum'),
        Revenue=('Revenue','sum'),
        Returns=('Total Return Qty','sum'),
    ).reset_index().sort_values('Sales', ascending=False)
    a['ReturnPct'] = (a['Returns']/a['Sales']*100).round(1)
    return a

# ── BRAND TOTALS ──────────────────────────────────────────────────────────────
brand_totals = df.groupby('Brand').agg(
    Sales=('Total Sales Qty','sum'),
    Revenue=('Revenue','sum'),
    Returns=('Total Return Qty','sum'),
    AvgCost=('Cost','mean'),
).reset_index()
brand_totals['ReturnPct'] = (brand_totals['Returns']/brand_totals['Sales']*100).round(1)
brand_totals['AvgCost'] = brand_totals['AvgCost'].round(0).astype(int)

# Active ROS per brand (ROS > 0 styles only)
active_ros = style_df[style_df['ROS']>0].groupby('Brand')['ROS'].mean().round(3).reset_index()
active_ros.columns = ['Brand','AvgROS']
brand_totals = brand_totals.merge(active_ros, on='Brand', how='left')

# Overall active ROS
overall_active_ros = round(style_df[style_df['ROS']>0]['ROS'].mean(), 3)

# Overall totals
total_sales   = int(df['Total Sales Qty'].sum())
total_revenue = int(df['Revenue'].sum())
total_returns = int(df['Total Return Qty'].sum())
total_retpct  = round(total_returns/total_sales*100, 1)
total_styles  = int(style_df['Style id'].nunique())
overall_avg_cost = int(df['Cost'].mean())

# ── FORMAT HELPERS ─────────────────────────────────────────────────────────────
def fmt_inr(v):
    v = float(v)
    if v >= 10000000: return f'&#8377;{v/10000000:.2f}Cr'
    if v >= 100000:   return f'&#8377;{v/100000:.1f}L'
    if v >= 1000:     return f'&#8377;{v/1000:.0f}K'
    return f'&#8377;{int(v)}'

def fmt_num(v):
    v = float(v)
    if v >= 100000: return f'{v/100000:.2f}L'
    if v >= 1000:   return f'{v/1000:.1f}K'
    return str(int(v))

# JS formatter for chart y-axis (revenue)
JS_FMT_REV = """function(v){
    if(v>=10000000) return '\u20b9'+(v/10000000).toFixed(1)+'Cr';
    if(v>=100000)   return '\u20b9'+(v/100000).toFixed(1)+'L';
    if(v>=1000)     return '\u20b9'+(v/1000).toFixed(0)+'K';
    return '\u20b9'+v;
}"""

JS_FMT_QTY = """function(v){
    if(v>=100000) return (v/100000).toFixed(1)+'L';
    if(v>=1000)   return (v/1000).toFixed(1)+'K';
    return v;
}"""

JS_FMT_PCT = "function(v){ return v+'%'; }"

def ret_badge(pct):
    pct = float(pct)
    cls = 'rb-high' if pct >= 50 else ('rb-med' if pct >= 35 else 'rb-low')
    return f'<span class="rb {cls}">{pct}%</span>'

def tier_badge(t):
    cls = {'Very Fast':'tb-vf','Fast':'tb-fast','Moderate':'tb-mod','Slow':'tb-slow','Dead':'tb-dead'}
    return f'<span class="tb {cls.get(t,"tb-dead")}">{t}</span>'

BRAND_CFG = {
    'overall':          {'id':'overall', 'label':'Overall',          'hdr':'linear-gradient(135deg,#0f172a,#1e1b4b,#312e81)', 'acc':'#818cf8','kpi':'#c7d2fe','fn':'Playfair Display','hatch':False},
    'Sangria':          {'id':'sangria', 'label':'Sangria',          'hdr':'linear-gradient(135deg,#581c87,#be185d,#c2410c)', 'acc':'#db2777','kpi':'#fde68a','fn':'Playfair Display','hatch':False},
    'House of Pataudi': {'id':'hop',     'label':'House of Pataudi', 'hdr':'#1a1410',                                         'acc':'#c9973a','kpi':'#fde68a','fn':'Playfair Display','hatch':False},
    'all about you':    {'id':'aay',     'label':'All About You',    'hdr':'linear-gradient(135deg,#0f172a,#1e3a8a,#1d4ed8)', 'acc':'#2563eb','kpi':'#fbbf24','fn':'Cormorant Garamond','hatch':False},
    'Anouk Rustic':     {'id':'ar',      'label':'Anouk Rustic',     'hdr':'#1c1208',                                         'acc':'#c2510e','kpi':'#d4a574','fn':'Lora','hatch':True},
}

# ── CHART DATA ────────────────────────────────────────────────────────────────
def chart_data(brand=None):
    m = get_monthly(brand)
    a = get_art(brand).head(10)
    sales_list   = [int(m[m['Month']==mo]['Sales'].values[0]) if mo in m['Month'].values else 0 for mo in MONTH_ORDER]
    rev_list     = [int(m[m['Month']==mo]['Revenue'].values[0]) if mo in m['Month'].values else 0 for mo in MONTH_ORDER]
    retpct_list  = [float(m[m['Month']==mo]['ReturnPct'].values[0]) if mo in m['Month'].values else 0 for mo in MONTH_ORDER]
    return {
        'months':  [mo[:3] for mo in MONTH_ORDER],
        'sales':   sales_list,
        'revenue': rev_list,
        'retpct':  retpct_list,
        'art_labels': [str(x)[:20] for x in a['Article Type'].tolist()],
        'art_sales':  [int(x) for x in a['Sales'].tolist()],
        'art_ret':    [float(x) for x in a['ReturnPct'].tolist()],
    }

# ── TABLE BUILDERS ────────────────────────────────────────────────────────────
def style_table(sub, tid):
    rows = ''.join([
        f'<tr>'
        f'<td class="mono">{r["Style id"]}</td>'
        f'<td>{r["Article Type"]}</td>'
        f'<td class="num">{fmt_num(int(r["TotalSales"]))}</td>'
        f'<td class="num">{fmt_inr(int(r["TotalRevenue"]))}</td>'
        f'<td class="num">{fmt_num(int(r["TotalReturns"]))}</td>'
        f'<td class="num">{ret_badge(r["ReturnPct"])}</td>'
        f'<td class="num mono">{r["ROS"]:.3f}</td>'
        f'<td class="num">{tier_badge(r["Tier"])}</td>'
        f'<td class="num mono">&#8377;{int(r["AvgCost"])}</td>'
        f'</tr>'
        for _, r in sub.iterrows()
    ])
    return (f'<div class="search-row">'
            f'<input type="text" placeholder="Search style ID / article type..." oninput="filterTbl(\'{tid}\',this.value,\'{tid}-c\')">'
            f'<span class="ctag" id="{tid}-c">{len(sub)} styles</span></div>'
            f'<div class="tw"><table id="{tid}"><thead><tr>'
            f'<th>Style ID</th><th>Article Type</th><th class="num">Sales</th>'
            f'<th class="num">Revenue</th><th class="num">Returns</th>'
            f'<th class="num">Return %</th><th class="num">ROS</th>'
            f'<th class="num">Tier</th><th class="num">Avg Cost</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')

def dead_stock_table(brand, tid):
    src = style_df if not brand else style_df[style_df['Brand']==brand]
    dead = src[(src['TotalSales']==0)&(src['AvgInventory']>0)].sort_values('AvgInventory',ascending=False)
    b_th = '' if brand else '<th>Brand</th>'
    rows_list = []
    for _, r in dead.iterrows():
        brand_td = '' if brand else f'<td>{r["Brand"]}</td>'
        rows_list.append(
            f'<tr>{brand_td}'
            f'<td class="mono">{r["Style id"]}</td>'
            f'<td>{r["Article Type"]}</td>'
            f'<td class="num">{int(r["AvgInventory"])}</td>'
            f'<td class="num mono">&#8377;{int(r["AvgCost"])}</td>'
            f'</tr>'
        )
    rows = ''.join(rows_list)
    return (f'<div class="search-row">'
            f'<input type="text" placeholder="Search..." oninput="filterTbl(\'{tid}\',this.value,\'{tid}-c\')">'
            f'<span class="ctag" id="{tid}-c">{len(dead)} styles</span></div>'
            f'<div class="tw"><table id="{tid}"><thead><tr>{b_th}'
            f'<th>Style ID</th><th>Article Type</th>'
            f'<th class="num">Avg Inventory</th><th class="num">Avg Cost</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')

def monthly_table(brand):
    m = get_monthly(brand)
    rows = ''.join([
        f'<tr><td><b>{r["Month"]}</b></td>'
        f'<td class="num">{fmt_num(int(r["Sales"]))}</td>'
        f'<td class="num">{fmt_inr(int(r["Revenue"]))}</td>'
        f'<td class="num">{fmt_num(int(r["Returns"]))}</td>'
        f'<td class="num">{ret_badge(float(r["ReturnPct"]))}</td></tr>'
        for _, r in m.iterrows()
    ])
    return (f'<div class="tw"><table><thead><tr><th>Month</th>'
            f'<th class="num">Sales Qty</th><th class="num">Revenue</th>'
            f'<th class="num">Returns</th><th class="num">Return %</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')

def art_table(brand):
    a = get_art(brand)
    rows = ''.join([
        f'<tr><td>{r["Article Type"]}</td>'
        f'<td class="num">{fmt_num(int(r["Sales"]))}</td>'
        f'<td class="num">{fmt_inr(int(r["Revenue"]))}</td>'
        f'<td class="num">{fmt_num(int(r["Returns"]))}</td>'
        f'<td class="num">{ret_badge(float(r["ReturnPct"]))}</td></tr>'
        for _, r in a.iterrows()
    ])
    return (f'<div class="tw"><table><thead><tr><th>Article Type</th>'
            f'<th class="num">Sales Qty</th><th class="num">Revenue</th>'
            f'<th class="num">Returns</th><th class="num">Return %</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')

# ── SECTION BUILDER ───────────────────────────────────────────────────────────
def build_section(bkey, cfg, s_df):
    bid   = cfg['id']
    label = cfg['label']
    acc   = cfg['acc']
    is_ov = bkey == 'overall'

    if is_ov:
        kv_sales   = total_sales
        kv_rev     = total_revenue
        kv_ret     = total_retpct
        kv_styles  = total_styles
        kv_ros     = overall_active_ros
        kv_cost    = overall_avg_cost
    else:
        row       = brand_totals[brand_totals['Brand']==bkey].iloc[0]
        kv_sales  = int(row['Sales'])
        kv_rev    = int(row['Revenue'])
        kv_ret    = float(row['ReturnPct'])
        kv_styles = int(s_df['Style id'].nunique())
        kv_ros    = float(row['AvgROS']) if not pd.isna(row['AvgROS']) else 0
        kv_cost   = int(row['AvgCost'])

    cd  = chart_data(None if is_ov else bkey)
    cds = json.dumps(cd)

    # ROS definition tooltip text
    ros_def = 'ROS = Rate of Sale (units sold per day). Dead: ROS=0 | Slow: ROS≤0.3 | Moderate: ROS 0.3–0.7 | Fast: ROS 0.7–1.5 | Very Fast: ROS>1.5'

    # Tier overview dots
    ov_dots = ''.join([
        f'<div class="ovc" style="background:{TIER_CFG[t][1]};border-color:{TIER_CFG[t][2]}40;color:{TIER_CFG[t][0]};">'
        f'<div class="ovd" style="background:{TIER_CFG[t][2]};"></div>'
        f'<div><div class="ovn">{t}</div>'
        f'<div class="ovs2">{len(s_df[s_df["Tier"]==t])} styles · {fmt_num(int(s_df[s_df["Tier"]==t]["TotalSales"].sum()))} units · <em>{TIER_RANGES[t]}</em></div></div></div>'
        for t in TIER_ORDER
    ])

    # Tier tab buttons + panels
    tier_btns = ''
    tier_panels = ''
    for t in TIER_ORDER:
        pid = t.lower().replace(' ','-')
        tc,bg,ac2,lt = TIER_CFG[t]
        sub = s_df[s_df['Tier']==t].sort_values('ROS', ascending=False)
        cnt = len(sub)
        tier_btns += f'<button class="ib" onclick="showTab(\'{bid}\',\'{pid}\',this)">{t} ({cnt})</button>'
        tier_panels += (
            f'<div class="tp" id="{bid}-p-{pid}">'
            f'<div class="tier-hdr" style="background:{bg};border-left:4px solid {ac2};color:{tc};">'
            f'<span class="tpill" style="background:{ac2};">{t}</span>'
            f'<span class="tier-def">{TIER_RANGES[t]} &nbsp;·&nbsp; {cnt} styles &nbsp;·&nbsp; {fmt_num(int(sub["TotalSales"].sum()))} units sold</span>'
            f'</div>{style_table(sub, f"{bid}-tbl-{pid}")}</div>'
        )

    # Dead stock
    ds_count = len(s_df[(s_df['TotalSales']==0)&(s_df['AvgInventory']>0)])
    dead_panel = (
        f'<div class="tp" id="{bid}-p-deadstock">'
        f'<div class="risk-note">&#128683; Styles with <b>zero sales</b> in FY26 but positive inventory — capital locked up.</div>'
        f'{dead_stock_table(None if is_ov else bkey, f"{bid}-tbl-ds")}</div>'
    )

    # Brand comparison (overall only)
    brand_cmp = ''
    if is_ov:
        b_rows = ''.join([
            f'<tr><td><b>{r["Brand"]}</b></td>'
            f'<td class="num">{fmt_num(int(r["Sales"]))}</td>'
            f'<td class="num">{fmt_inr(int(r["Revenue"]))}</td>'
            f'<td class="num">{fmt_num(int(r["Returns"]))}</td>'
            f'<td class="num">{ret_badge(float(r["ReturnPct"]))}</td>'
            f'<td class="num mono">&#8377;{int(r["AvgCost"])}</td>'
            f'<td class="num mono">{float(r["AvgROS"]):.3f}</td></tr>'
            for _, r in brand_totals.sort_values('Revenue', ascending=False).iterrows()
        ])
        brand_cmp = (
            f'<div class="sblk"><div class="stitle">Brand Comparison — FY 2025–26</div>'
            f'<div class="tw"><table><thead><tr><th>Brand</th>'
            f'<th class="num">Sales Qty</th><th class="num">Revenue</th>'
            f'<th class="num">Returns</th><th class="num">Return %</th>'
            f'<th class="num">Avg Cost</th><th class="num">Avg ROS (active)</th>'
            f'</tr></thead><tbody>{b_rows}</tbody></table></div></div>'
        )

    # Top 10 styles
    top10 = s_df.sort_values('TotalSales', ascending=False).head(10)
    top10_rows = ''.join([
        f'<tr><td class="mono">{r["Style id"]}</td><td>{r["Article Type"]}</td>'
        f'<td class="num">{fmt_num(int(r["TotalSales"]))}</td>'
        f'<td class="num">{ret_badge(r["ReturnPct"])}</td>'
        f'<td class="num mono">{r["ROS"]:.3f}</td></tr>'
        for _, r in top10.iterrows()
    ])

    # Tier distribution
    tier_dist = ''.join([
        f'<tr><td>{tier_badge(t)}</td>'
        f'<td class="small-def">{TIER_RANGES[t]}</td>'
        f'<td class="num">{len(s_df[s_df["Tier"]==t])}</td>'
        f'<td class="num">{fmt_num(int(s_df[s_df["Tier"]==t]["TotalSales"].sum()))}</td></tr>'
        for t in TIER_ORDER
    ])

    sg_attr = 'id="sg-title"' if bkey == 'Sangria' else ''
    hatch   = '<div class="hatch"></div>' if cfg['hatch'] else ''

    return f'''
<div class="bs" id="brand-{bid}">
  <header class="bh" style="background:{cfg["hdr"]};">{hatch}
    <div class="bhi">
      <div class="bey">UTM · Myntra · FY 2025–26</div>
      <div class="bname" style="font-family:'{cfg["fn"]}',serif;" {sg_attr}>{label}</div>
      <div class="bsub">Annual Sales &amp; Returns Analysis · Apr 2025 – Mar 2026</div>
      <div class="krow">
        <div class="kpi"><div class="kv" style="color:{cfg["kpi"]};">{fmt_num(kv_sales)}</div><div class="kl">Sales Qty</div></div>
        <div class="kpi"><div class="kv" style="color:{cfg["kpi"]};">{fmt_inr(kv_rev)}</div><div class="kl">Revenue</div></div>
        <div class="kpi"><div class="kv" style="color:{cfg["kpi"]};">{kv_ret}%</div><div class="kl">Return Rate</div></div>
        <div class="kpi"><div class="kv" style="color:{cfg["kpi"]};">&#8377;{kv_cost}</div><div class="kl">Avg Cost</div></div>
        <div class="kpi"><div class="kv" style="color:{cfg["kpi"]};">{kv_ros:.2f}</div><div class="kl">Avg ROS <span class="kl-sub">(active)</span></div></div>
        <div class="kpi"><div class="kv" style="color:{cfg["kpi"]};">{kv_styles}</div><div class="kl">Style IDs</div></div>
      </div>
    </div>
  </header>

  <div class="ovs-strip">
    <span class="ovs-label">ROS Tiers <span class="ros-def-tip" title="{ros_def}">?</span></span>
    {ov_dots}
  </div>

  <nav class="inav" id="{bid}-nav">
    <button class="ib active" onclick="showTab('{bid}','overview',this)">Overview</button>
    <button class="ib" onclick="showTab('{bid}','monthly',this)">Monthly</button>
    <button class="ib" onclick="showTab('{bid}','articles',this)">Article Types</button>
    {tier_btns}
    <button class="ib riskbtn" onclick="showTab('{bid}','deadstock',this)">&#128683; Dead Stock ({ds_count})</button>
  </nav>

  <div class="tc">

    <div class="tp active" id="{bid}-p-overview">
      {brand_cmp}
      <div class="cgrid">
        <div class="cc"><div class="ct">Monthly Sales Qty</div><div class="cw"><canvas id="{bid}-c1"></canvas></div></div>
        <div class="cc"><div class="ct">Monthly Revenue</div><div class="cw"><canvas id="{bid}-c2"></canvas></div></div>
        <div class="cc"><div class="ct">Monthly Return Rate</div><div class="cw"><canvas id="{bid}-c3"></canvas></div></div>
        <div class="cc"><div class="ct">Top 10 Article Types by Sales</div><div class="ch"><canvas id="{bid}-c4"></canvas></div></div>
      </div>
      <div class="twocol">
        <div class="sblk">
          <div class="stitle">ROS Tier Distribution <span class="ros-def-tip" title="{ros_def}">?</span></div>
          <div class="tw"><table><thead><tr><th>Tier</th><th>Definition</th><th class="num">Styles</th><th class="num">Units</th></tr></thead>
          <tbody>{tier_dist}</tbody></table></div>
        </div>
        <div class="sblk">
          <div class="stitle">Top 10 Style IDs by Sales</div>
          <div class="tw"><table><thead><tr><th>Style ID</th><th>Article Type</th><th class="num">Sales</th><th class="num">Return %</th><th class="num">ROS</th></tr></thead>
          <tbody>{top10_rows}</tbody></table></div>
        </div>
      </div>
    </div>

    <div class="tp" id="{bid}-p-monthly">
      <div class="cgrid">
        <div class="cc"><div class="ct">Sales Qty — Monthly</div><div class="cw"><canvas id="{bid}-m1"></canvas></div></div>
        <div class="cc"><div class="ct">Revenue — Monthly</div><div class="cw"><canvas id="{bid}-m2"></canvas></div></div>
        <div class="cc cwide"><div class="ct">Return Rate % — Monthly</div><div class="cw"><canvas id="{bid}-m3"></canvas></div></div>
      </div>
      <div class="sblk"><div class="stitle">Monthly Breakdown</div>{monthly_table(None if is_ov else bkey)}</div>
    </div>

    <div class="tp" id="{bid}-p-articles">
      <div class="cgrid">
        <div class="cc cwide"><div class="ct">Sales by Article Type (Top 10)</div><div class="ch"><canvas id="{bid}-a1"></canvas></div></div>
        <div class="cc cwide"><div class="ct">Return Rate % by Article Type (Top 10)</div><div class="ch"><canvas id="{bid}-a2"></canvas></div></div>
      </div>
      <div class="sblk"><div class="stitle">Article Type Detail</div>{art_table(None if is_ov else bkey)}</div>
    </div>

    {tier_panels}
    {dead_panel}

  </div>

  <script>
  (function(){{
    var d={cds};
    var ac="{acc}";
    var ms=d.months;

    function fmtRev(v){{
      if(v>=10000000) return '\u20b9'+(v/10000000).toFixed(2)+'Cr';
      if(v>=100000)   return '\u20b9'+(v/100000).toFixed(1)+'L';
      if(v>=1000)     return '\u20b9'+(v/1000).toFixed(0)+'K';
      return '\u20b9'+v;
    }}
    function fmtQty(v){{
      if(v>=100000) return (v/100000).toFixed(1)+'L';
      if(v>=1000)   return (v/1000).toFixed(1)+'K';
      return String(v);
    }}
    var baseOpts={{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}}}};

    function mkBar(id,labels,data,col,yFmt){{
      var el=document.getElementById(id); if(!el)return;
      new Chart(el,{{type:'bar',
        data:{{labels:labels,datasets:[{{data:data,backgroundColor:col+'cc',borderColor:col,borderWidth:1,borderRadius:3}}]}},
        options:Object.assign({{}},baseOpts,{{
          scales:{{
            x:{{grid:{{display:false}},ticks:{{font:{{size:9}},maxRotation:45}}}},
            y:{{grid:{{color:'#f5f5f5'}},ticks:{{font:{{size:9}},callback:yFmt}}}}
          }}
        }})
      }});
    }}
    function mkLine(id,labels,data,col,yFmt){{
      var el=document.getElementById(id); if(!el)return;
      new Chart(el,{{type:'line',
        data:{{labels:labels,datasets:[{{data:data,borderColor:col,backgroundColor:col+'22',borderWidth:2,fill:true,tension:0.4,pointRadius:3,pointHoverRadius:5}}]}},
        options:Object.assign({{}},baseOpts,{{
          scales:{{
            x:{{grid:{{display:false}},ticks:{{font:{{size:9}},maxRotation:45}}}},
            y:{{grid:{{color:'#f5f5f5'}},ticks:{{font:{{size:9}},callback:yFmt}}}}
          }}
        }})
      }});
    }}
    function mkHBar(id,labels,data,col,yFmt){{
      var el=document.getElementById(id); if(!el)return;
      new Chart(el,{{type:'bar',
        data:{{labels:labels,datasets:[{{data:data,backgroundColor:col+'cc',borderColor:col,borderWidth:1,borderRadius:3}}]}},
        options:Object.assign({{}},baseOpts,{{
          indexAxis:'y',
          scales:{{
            x:{{grid:{{color:'#f5f5f5'}},ticks:{{font:{{size:9}},callback:yFmt}}}},
            y:{{grid:{{display:false}},ticks:{{font:{{size:9}}}}}}
          }}
        }})
      }});
    }}

    window.addEventListener('load',function(){{
      mkBar( '{bid}-c1', ms, d.sales,   ac,      fmtQty);
      mkLine('{bid}-c2', ms, d.revenue, ac,      fmtRev);
      mkLine('{bid}-c3', ms, d.retpct,  '#ef4444', function(v){{return v+'%';}});
      mkHBar('{bid}-c4', d.art_labels, d.art_sales, ac, fmtQty);
      mkBar( '{bid}-m1', ms, d.sales,   ac,      fmtQty);
      mkLine('{bid}-m2', ms, d.revenue, ac,      fmtRev);
      mkLine('{bid}-m3', ms, d.retpct,  '#ef4444', function(v){{return v+'%';}});
      mkHBar('{bid}-a1', d.art_labels, d.art_sales, ac, fmtQty);
      mkHBar('{bid}-a2', d.art_labels, d.art_ret,   '#ef4444', function(v){{return v+'%';}});
    }});
  }})();
  </script>

  <div class="bfoot">UTM · {label} · FY 2025–26 · Apr 2025 – Mar 2026 · Return Rate = Returns ÷ Sales · ROS: Dead=0, Slow≤0.3, Moderate≤0.7, Fast≤1.5, Very Fast&gt;1.5 · Avg ROS excludes dead styles</div>
</div>'''

# ── ASSEMBLE ──────────────────────────────────────────────────────────────────
sections = build_section('overall', BRAND_CFG['overall'], style_df)
for bk in ['Sangria','House of Pataudi','all about you','Anouk Rustic']:
    sections += build_section(bk, BRAND_CFG[bk], style_df[style_df['Brand']==bk].copy())

sw_btns = ''.join([
    f'<button class="sbn" id="sw-{cfg["id"]}" onclick="sw(\'{cfg["id"]}\')">{cfg["label"]}</button>'
    for cfg in BRAND_CFG.values()
])

html = (
'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
'<meta charset="UTF-8">\n'
'<meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
'<title>UTM Annual Dashboard FY 2025-26</title>\n'
'<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></' 'script>\n'
'''<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Cormorant+Garamond:wght@600;700&family=Lora:wght@600;700&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{font-family:'DM Sans',sans-serif;background:#f1f5f9;color:#111;font-size:13px;line-height:1.5;}

/* TOP BAR */
.topbar{position:sticky;top:0;z-index:1000;background:#0a0a14;padding:0 24px;display:flex;align-items:center;border-bottom:1px solid #1a1a2e;box-shadow:0 2px 12px rgba(0,0,0,0.5);overflow-x:auto;}
.tlogo{font-family:'Playfair Display',serif;font-size:12px;font-weight:700;color:#555;letter-spacing:0.1em;text-transform:uppercase;padding:14px 20px 14px 0;margin-right:4px;border-right:1px solid #222;white-space:nowrap;}
.sbn{padding:14px 16px;font-size:11px;font-weight:600;color:#444;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;white-space:nowrap;font-family:'DM Sans',sans-serif;transition:color 0.2s,border-color 0.2s;}
.sbn:hover{color:#aaa;}
.sbn.active[id="sw-overall"]{color:#818cf8;border-bottom-color:#818cf8;}
.sbn.active[id="sw-sangria"]{color:#f472b6;border-bottom-color:#f472b6;}
.sbn.active[id="sw-hop"]    {color:#c9973a;border-bottom-color:#c9973a;}
.sbn.active[id="sw-aay"]    {color:#60a5fa;border-bottom-color:#60a5fa;}
.sbn.active[id="sw-ar"]     {color:#fb923c;border-bottom-color:#fb923c;}

/* BRAND */
.bs{display:none;} .bs.active{display:block;}

/* HEADER */
.bh{position:relative;overflow:hidden;}
.hatch{position:absolute;inset:0;opacity:0.04;background-image:repeating-linear-gradient(45deg,#d4a574 0,#d4a574 1px,transparent 0,transparent 50%);background-size:12px 12px;}
.bhi{padding:30px 40px 22px;position:relative;}
.bey{font-size:10px;letter-spacing:0.18em;text-transform:uppercase;color:rgba(255,255,255,0.4);margin-bottom:5px;}
.bname{font-size:32px;font-weight:700;color:#fff;line-height:1.1;margin-bottom:3px;}
#sg-title{background:linear-gradient(90deg,#f9a8d4,#fde68a,#fb923c);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.bsub{font-size:10px;color:rgba(255,255,255,0.38);letter-spacing:0.06em;text-transform:uppercase;margin-bottom:22px;}
.krow{display:flex;gap:10px;flex-wrap:wrap;}
.kpi{background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:12px 16px;min-width:100px;}
.kv{font-family:'Playfair Display',serif;font-size:20px;font-weight:700;line-height:1;margin-bottom:3px;}
.kl{font-size:9px;color:rgba(255,255,255,0.4);letter-spacing:0.06em;text-transform:uppercase;}
.kl-sub{font-size:8px;color:rgba(255,255,255,0.3);}

/* OV STRIP */
.ovs-strip{background:#fff;border-bottom:1px solid #e5e5e5;padding:10px 40px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
.ovs-label{font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#999;margin-right:4px;white-space:nowrap;}
.ros-def-tip{display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;border-radius:50%;background:#e2e8f0;color:#666;font-size:9px;cursor:help;font-style:normal;font-weight:700;vertical-align:middle;}
.ovc{border-radius:8px;padding:6px 12px;display:flex;align-items:center;gap:8px;border:1px solid;}
.ovd{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
.ovn{font-size:11px;font-weight:600;}
.ovs2{font-size:10px;opacity:0.7;}
.ovs2 em{font-style:normal;opacity:0.8;}

/* INNER NAV */
.inav{position:sticky;top:50px;z-index:900;background:#fff;border-bottom:2px solid #e5e5e5;padding:0 40px;display:flex;overflow-x:auto;box-shadow:0 1px 4px rgba(0,0,0,0.04);}
.ib{padding:11px 14px;font-size:11px;font-weight:500;color:#888;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;white-space:nowrap;font-family:'DM Sans',sans-serif;transition:color 0.15s,border-color 0.15s;}
.ib:hover{color:#111;}
.riskbtn{color:#dc2626!important;font-weight:600;}
#brand-overall .ib.active{color:#818cf8;border-bottom-color:#818cf8;font-weight:600;}
#brand-sangria .ib.active{color:#db2777;border-bottom-color:#db2777;font-weight:600;}
#brand-hop     .ib.active{color:#c9973a;border-bottom-color:#c9973a;font-weight:600;}
#brand-aay     .ib.active{color:#2563eb;border-bottom-color:#2563eb;font-weight:600;}
#brand-ar      .ib.active{color:#c2510e;border-bottom-color:#c2510e;font-weight:600;}

/* CONTENT */
.tc{padding:18px 40px;max-width:1400px;margin:0 auto;}
.tp{display:none;} .tp.active{display:block;}

/* CHARTS */
.cgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px;}
.cwide{grid-column:span 2;}
.cc{background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border:1px solid #f0f0f0;}
.ct{font-size:11px;font-weight:600;color:#555;margin-bottom:10px;text-transform:uppercase;letter-spacing:0.04em;}
.cw{position:relative;height:160px;}  /* fixed height for bar/line */
.ch{position:relative;height:220px;}  /* taller for horizontal bar */

/* LAYOUT */
.twocol{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;}
.sblk{background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border:1px solid #f0f0f0;margin-bottom:14px;}
.stitle{font-size:11px;font-weight:700;color:#444;margin-bottom:10px;text-transform:uppercase;letter-spacing:0.04em;}
.tier-hdr{padding:10px 14px;display:flex;align-items:center;gap:10px;border-radius:8px 8px 0 0;margin-bottom:0;}
.tpill{font-size:10px;font-weight:700;padding:3px 9px;border-radius:20px;color:#fff;letter-spacing:0.05em;text-transform:uppercase;}
.tier-def{font-size:11px;font-weight:400;}

/* TABLES */
.tw{overflow-x:auto;background:#fff;border-radius:8px;border:1px solid #f0f0f0;margin-bottom:12px;}
.tier-hdr+.tw{border-radius:0 0 8px 8px;border-top:none;}
table{width:100%;border-collapse:collapse;font-size:12px;}
thead th{padding:7px 10px;text-align:left;font-size:10px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#999;border-bottom:1px solid #f0f0f0;background:#fafafa;white-space:nowrap;}
thead th.num{text-align:right;}
tbody tr{border-bottom:1px solid #f8f8f8;transition:background 0.1s;}
tbody tr:last-child{border-bottom:none;}
tbody tr:hover{background:#f9f9f9;}
tbody td{padding:6px 10px;vertical-align:middle;}
tbody td.num{text-align:right;font-size:11px;}
.mono{font-family:'DM Mono',monospace;font-size:11px;color:#666;}
.small-def{font-size:10px;color:#888;}

/* BADGES */
.rb{display:inline-block;font-size:10px;font-weight:600;padding:2px 6px;border-radius:8px;font-family:'DM Mono',monospace;}
.rb-high{background:#fef2f2;color:#dc2626;border:1px solid #fecaca;}
.rb-med {background:#fffbeb;color:#d97706;border:1px solid #fde68a;}
.rb-low {background:#f0fdf4;color:#16a34a;border:1px solid #bbf7d0;}
.tb{display:inline-block;font-size:10px;font-weight:600;padding:2px 7px;border-radius:8px;border:1px solid;}
.tb-vf  {background:#ecfdf5;color:#065f46;border-color:#a7f3d0;}
.tb-fast{background:#f0fdf4;color:#14532d;border-color:#bbf7d0;}
.tb-mod {background:#fffbeb;color:#78350f;border-color:#fde68a;}
.tb-slow{background:#fef2f2;color:#7f1d1d;border-color:#fecaca;}
.tb-dead{background:#f9fafb;color:#374151;border-color:#e5e7eb;}

/* SEARCH */
.search-row{display:flex;align-items:center;gap:10px;margin-bottom:10px;}
.search-row input{flex:1;max-width:300px;font-size:12px;padding:7px 12px;border:1px solid #ddd;border-radius:7px;background:#fff;color:#111;outline:none;font-family:'DM Sans',sans-serif;}
.ctag{font-size:11px;color:#999;}

/* RISK NOTE */
.risk-note{background:#fff7ed;border:1px solid #fed7aa;border-left:4px solid #ea580c;border-radius:8px;padding:10px 14px;font-size:12px;color:#7c2d12;margin-bottom:12px;font-weight:500;}

/* FOOTER */
.bfoot{text-align:center;padding:14px 40px;font-size:10px;color:#bbb;border-top:1px solid #eee;margin-top:18px;letter-spacing:0.03em;}

@media(max-width:768px){
  .cgrid,.twocol{grid-template-columns:1fr;}
  .cwide{grid-column:span 1;}
  .bhi{padding:22px 18px 16px;}
  .tc{padding:14px 16px;}
  .inav,.ovs-strip{padding-left:16px;padding-right:16px;}
}
</style>
</head>
<body>
<div class="topbar">
  <div class="tlogo">UTM · FY 25–26</div>
  ''' + sw_btns + '''
</div>
''' + sections + '''
<script>
function sw(bid){
  document.querySelectorAll('.bs').forEach(function(s){s.classList.remove('active');});
  document.querySelectorAll('.sbn').forEach(function(b){b.classList.remove('active');});
  document.getElementById('brand-'+bid).classList.add('active');
  document.getElementById('sw-'+bid).classList.add('active');
  window.scrollTo({top:0,behavior:'smooth'});
}
function showTab(bid,pid,btn){
  var sec=document.getElementById('brand-'+bid);
  sec.querySelectorAll('.tp').forEach(function(p){p.classList.remove('active');});
  sec.querySelectorAll('.ib').forEach(function(b){b.classList.remove('active');});
  var p=document.getElementById(bid+'-p-'+pid);
  if(p) p.classList.add('active');
  if(btn) btn.classList.add('active');
}
function filterTbl(tid,q,cid){
  var t=document.getElementById(tid); if(!t) return;
  var vis=0;
  t.querySelectorAll('tbody tr').forEach(function(r){
    var m=r.textContent.toLowerCase().indexOf(q.toLowerCase())!==-1;
    r.style.display=m?'':'none'; if(m)vis++;
  });
  var c=document.getElementById(cid); if(c) c.textContent=vis+' styles';
}
sw('overall');
</script>
</body>
</html>''')

with open('docs/index.html','w') as f:
    f.write(html)
print('Done. Size:', len(html), 'chars')
