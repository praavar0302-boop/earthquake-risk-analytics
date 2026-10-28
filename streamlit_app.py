"""Guided, read-only walkthrough of the executed earthquake research project.
Run: streamlit run streamlit_app.py
"""
from __future__ import annotations
import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from app_support import (
    ASSETS, FIGURES, ROOT, STAGES, SHORT_STAGES, COLORS, PROBABILITIES, CITIES,
    ArtifactError, load_project, tier, cell_id, filter_events, roc_coordinates,
    calculate_quote, style_figure, geographic_figure, earthquake_figure, forecast_figure,
)

st.set_page_config(page_title='Earthquake Research | Guided Walkthrough',page_icon='🌐',layout='wide',
                   initial_sidebar_state='auto')
st.markdown('''<style>
.block-container{max-width:1320px;padding-top:4rem;padding-bottom:2rem}
h1{letter-spacing:-.045em;font-size:2.8rem!important;line-height:1.12!important;font-weight:750!important}
h2,h3{letter-spacing:-.025em} p,li{line-height:1.6}
[data-testid="stSidebar"]{border-right:1px solid #dce5ed}
[data-testid="stMetric"]{background:white;border:1px solid #e1e8ee;border-radius:14px;padding:16px 18px}
[data-testid="stMetricLabel"]{font-size:.85rem;color:#53667a}
[data-testid="stMetricValue"]{letter-spacing:-.04em}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]){flex-wrap:wrap}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"]{flex:1 1 190px!important;min-width:190px!important}
[data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) > [data-testid="stColumn"]{min-width:min(100%,260px)}
.eyebrow{font-size:.76rem;font-weight:750;letter-spacing:.16em;color:#147d72;margin-bottom:10px}
.lead{font-size:1.14rem;color:#586c80;max-width:900px;margin-bottom:1.4rem}
.badge{display:inline-block;background:#e6f2ed;color:#17695e;border-radius:30px;padding:5px 12px;font-size:.75rem;font-weight:650;margin:0 6px 6px 0}
.badge.gold{background:#fff0d8;color:#8a5c15}
.insight{border-left:4px solid #147d72;background:#eaf3f0;padding:14px 18px;border-radius:0 10px 10px 0;margin:12px 0 22px;color:#24483e}
.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:18px 0 25px}
.flow div{background:white;border:1px solid #dce5ed;padding:18px 12px;border-radius:12px;font-size:.9rem}
.flow small{display:block;color:#147d72;font-weight:700;margin-bottom:8px}
.brand{font-size:1.12rem;font-weight:800;letter-spacing:-.025em;line-height:1.25;color:#15334b;margin-bottom:8px}
.muted{font-size:.84rem;color:#65788a}.formula{background:#142b3b;color:#e4f3ef;border-radius:14px;padding:22px;font-size:1.25rem;margin:16px 0}
@media(max-width:700px){h1{font-size:2rem!important}.flow{grid-template-columns:1fr 1fr}.block-container{padding-top:3.5rem}}
</style>''',unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def project_data(manifest_mtime):
    return load_project()


def chart(fig,key):
    st.plotly_chart(fig,width='stretch',theme=None,key=key,
                    config={'displaylogo':False,'scrollZoom':False})


def takeaway(text):
    st.markdown(f'<div class="insight"><b>Takeaway</b> · {html.escape(text)}</div>',unsafe_allow_html=True)


def explain(what,why,interpretation):
    left,right=st.columns(2)
    with left:st.markdown(f'**What?** {what}')
    with right:st.markdown(f'**Why?** {why}')
    takeaway(interpretation)


def region_label(region):
    city=next((name for name,value in CITIES.items() if value==region),None)
    lat,lon=map(int,region.split('_'))
    return f'{city+" · " if city else ""}{region}  |  lat {lat}…{lat+5}°, lon {lon}…{lon+5}°'


def choose_region(data,key,default='35_-125'):
    values=data['forecasts'].cell_id.tolist()
    ordered=list(dict.fromkeys([r for r in CITIES.values() if r in values]+values))
    return st.selectbox('Supported region',ordered,index=ordered.index(default),format_func=region_label,key=key)


def image(filename,caption):
    path=FIGURES/filename
    if path.exists():st.image(str(path),caption=caption,width='stretch')
    else:st.warning(f'Existing figure unavailable: {filename}. Tables and interactive results remain available.')


def overview(data):
    st.markdown('### Can earthquake history help estimate next year’s regional probability?')
    explain('Estimate the chance of at least one M ≥ 6.0 earthquake in a region during a calendar year.',
            'Regional probabilities provide a concrete setting for comparing prediction, explanation and a simple pricing decision.',
            'The project estimates occurrence in large regions. It does not predict an exact date or property damage.')
    cols=st.columns(4)
    for col,label,value in zip(cols,['Catalogue events','Modelled regions','Evaluation years','Positive region-years'],
                               [f'{len(data["events"]):,}','722','2016–2025','763 / 7,220']):col.metric(label,value)
    st.markdown('<div class="flow"><div><small>01 / OBSERVE</small>Collect & clean<br>USGS events</div>'
                '<div><small>02 / STRUCTURE</small>Build annual<br>regional histories</div>'
                '<div><small>03 / COMPARE</small>Fit models &<br>simple baselines</div>'
                '<div><small>04 / CHECK</small>Evaluate ranking<br>& probabilities</div>'
                '<div><small>05 / ILLUSTRATE</small>Forecast & price<br>a fixed payout</div></div>',unsafe_allow_html=True)
    a,b=st.columns([1.25,1])
    with a:
        st.markdown('### The headline result')
        st.markdown('**A simple historical-frequency baseline is hard to beat.** Random Forest has the lowest probability error, '
                    'but its Brier score is only about **0.96% lower** than the historical-rate baseline. '
                    'The question is how much useful information the extra complexity adds.')
    with b:
        small=data['metrics'].loc[['Random forest','Historical rate','Logistic'],['brier']].sort_values('brier')
        fig=go.Figure(go.Bar(x=small.brier,y=small.index,orientation='h',marker_color=[COLORS[x] for x in small.index],
                            text=small.brier.map(lambda x:f'{x:.5f}'),textposition='outside'))
        fig.update_xaxes(title='Brier score · lower is better',range=[0,.08]);chart(style_figure(fig,height=260),'overview_brier')
    st.warning('Exploratory historical evaluation: 2016–2025 outcomes influenced earlier development. '
               'Neither the fixed-fit comparison nor the rolling-origin analysis is an untouched holdout.')
    with st.expander('Research scope and evidence'):
        st.write('Catalogue: M ≥ 5.5, 1965–2025. Target: at least one M ≥ 6.0 event in a 5° cell-year. '
                 'History: ten previous years plus expanding rates. Forecast: 2026, using information through 2025. '
                 'The original saved run reported 28,558 events; this supplied snapshot has 28,557. The difference is disclosed, not replaced.')
        st.caption('Next: inspect what the catalogue measures and how it was cleaned.')


def dataset(data):
    explain('Check the supplied USGS catalogue, then build a traceable cleaned event table.',
            'Missing fields, duplicate events or changed measurement scales could distort histories and probabilities.',
            'All 28,557 supplied rows are retained. Six negative depths are clipped to zero, with original depths kept.')
    e=data['events'];cols=st.columns(4)
    for col,label,value in zip(cols,['Raw → clean rows','Duplicate event IDs','Core missing values','Potential default depths'],
                               ['28,557 → 28,557','0','0','9,149 · 32.0%']):col.metric(label,value)
    left,right=st.columns([1.1,1])
    with left:
        missing=data['raw_quality'].loc[lambda x:x>0].sort_values()
        fig=go.Figure(go.Bar(x=missing.values,y=missing.index,orientation='h',marker_color='#6c98af'))
        fig.update_xaxes(title='Missing values in raw metadata (%)',range=[0,100])
        chart(style_figure(fig,'Measurement metadata are often missing',370),'missing_quality')
    with right:
        st.markdown('### Cleaning decisions')
        st.markdown('- Keep core time, magnitude, location, depth and event identifiers.\n'
                    '- Check valid coordinates, threshold, core completeness and duplicate IDs.\n'
                    '- Keep original depth; clip six negative values to zero for analysis.\n'
                    '- Flag exactly 10 km / 33 km as potentially assigned depths.\n'
                    '- Create year, depth class and magnitude-family fields.')
        st.info('A flag is not proof that a particular depth was assigned. Grouping magnitude scales does not harmonize them.')
    with st.expander('Data dictionary, sample records and provenance'):
        st.dataframe(pd.DataFrame({'Field':['time','latitude / longitude','mag / magType','depth / depth_original','id','depth_fixed'],
                                  'Meaning':['UTC event origin time','Epicentre coordinates in degrees','Preferred magnitude and its measurement scale',
                                             'Analysis depth and preserved reported depth (km)','Unique event identifier','Exactly 10 or 33 km; potential default']}),hide_index=True)
        st.dataframe(e[['time','mag','depth','depth_original','magType','place']].head(8),hide_index=True)
        st.write('The combined raw CSV and 13 acquisition chunks have matching event-ID sets. Supplied processed tables '
                 'were preserved; revised tables were rebuilt. Snapshot retrieval time and the original one-record discrepancy remain unresolved.')
        st.caption(f'Raw SHA-256: {data["manifest"]["raw_sha256"]}')
    st.caption('Next: examine distributions, temporal variation and geography.')


def exploration(data):
    explain('Explore earthquake magnitude, depth, annual variation and geographic clustering.',
            'EDA identifies the patterns and measurement limitations that regional predictors need to reflect.',
            'Events cluster geographically; most are shallow, and large magnitudes are rare. These are descriptive findings.')
    a,b,c=st.columns(3)
    with a:years=st.slider('Catalogue years',1965,2025,(1965,2025),key='eda_years')
    with b:magnitudes=st.slider('Magnitude range',5.5,9.1,(5.5,9.1),.1,key='eda_magnitudes')
    with c:depths=st.slider('Analysis depth (km)',0,700,(0,700),10,key='eda_depths')
    selected=filter_events(data['events'],years,magnitudes,depths)
    cols=st.columns(3);cols[0].metric('Events matching filters',f'{len(selected):,}')
    cols[1].metric('M ≥ 6.0 events',f'{int(selected.mag.ge(6).sum()):,}')
    cols[2].metric('Shallow share',f'{selected.depth.lt(70).mean():.1%}' if len(selected) else '—')
    if selected.empty:
        st.info('No recorded events match these filters. Widen a range to explore the data.');return
    map_tab,dist_tab,time_tab=st.tabs(['Earthquake explorer','Magnitude & depth','Time & measurement'])
    with map_tab:
        fig,count=earthquake_figure(selected,data['boundaries']);chart(fig,'earthquake_explorer')
        st.caption(f'Hover for actual event details. Longitude–latitude display with local plate boundaries; no basemap downloads. '
                   f'Map shows {count:,} of {len(selected):,} events'+(' (deterministic sample for responsiveness).' if count<len(selected) else '.'))
        takeaway('Clustering motivates a regional view. Marker size encodes magnitude, not released energy or damage.')
    with dist_tab:
        left,right=st.columns(2)
        with left:
            fig=go.Figure(go.Histogram(x=selected.mag,xbins=dict(start=5.45,end=9.25,size=.1),marker_color='#3479c4'))
            fig.update_xaxes(title='Magnitude');fig.update_yaxes(title='Event count',type='log')
            chart(style_figure(fig,'Large earthquakes are much rarer',330),'eda_mag')
        with right:
            fig=go.Figure(go.Histogram(x=selected.depth,xbins=dict(start=0,end=710,size=10),marker_color='#148b79'))
            fig.update_xaxes(title='Depth (km)');fig.update_yaxes(title='Event count',type='log')
            chart(style_figure(fig,'Most recorded events are shallow',330),'eda_depth')
        takeaway('Logarithmic count axes expose rare observations; depth peaks can partly reflect default-like reported values.')
    with time_tab:
        annual=selected.groupby('year').size().reindex(range(years[0],years[1]+1),fill_value=0)
        fig=go.Figure(go.Scatter(x=annual.index,y=annual.values,mode='lines+markers',line_color='#3479c4',name='Matching events'))
        fig.update_xaxes(title='Year');fig.update_yaxes(title='Recorded events',rangemode='tozero')
        chart(style_figure(fig,'Recorded activity varies from year to year',330),'eda_time')
        st.caption('Annual counts above respect all three filters. The reference figure below uses the full verified catalogue.')
        with st.expander('Full-catalogue magnitude scales by decade'):
            image('fig4_magnitude_types.png','Executed notebook reference: changing magnitude-family composition.')
        takeaway('A time trend can reflect seismic sequences and catalogue practices. This chart does not establish a causal trend.')
    st.caption('Next: turn individual events into comparable region-year observations.')


def regions(data):
    explain('Divide locations into 5° latitude–longitude cells and assign a binary annual outcome.',
            'We need both event and zero-event years, so models learn occurrence probability rather than event counts alone.',
            'The final panel contains 722 cells × 51 target years = 36,822 rows. A positive row has at least one M ≥ 6.0 event.')
    region=choose_region(data,'grid_region',default='35_135')
    year=st.slider('Inspect target year',1975,2025,2020,key='grid_year')
    row=data['forecasts'].set_index('cell_id').loc[region]
    events=data['events'];part=events[events.cell_id.eq(region)&events.year.eq(year)]
    target=int(data['features'].query('cell_id == @region and year == @year').strong_quake.iloc[0])
    left,right=st.columns([1.7,1])
    with left:
        # Show neighboring cells to make the otherwise abstract observation unit visible.
        fig=geographic_figure(data['boundaries'])
        near=events[events.year.eq(year)&events.latitude.between(row.cell_lat-10,row.cell_lat+10)
                    &events.longitude.between(row.cell_lon-10,row.cell_lon+10)]
        fig.add_trace(go.Scattergl(x=near.longitude,y=near.latitude,mode='markers',name=f'{year} events',
                                  marker=dict(size=7,color='#3479c4'),text=near.mag,
                                  hovertemplate='M %{text:.2f}<extra></extra>'))
        for x in np.arange(row.cell_lon-12.5,row.cell_lon+15,5):fig.add_vline(x=x,line=dict(color='#c4ced8',width=1))
        for y in np.arange(row.cell_lat-12.5,row.cell_lat+15,5):fig.add_hline(y=y,line=dict(color='#c4ced8',width=1))
        fig.add_shape(type='rect',x0=row.cell_lon-2.5,x1=row.cell_lon+2.5,y0=row.cell_lat-2.5,y1=row.cell_lat+2.5,
                      fillcolor='rgba(20,139,121,.12)',line=dict(color='#148b79',width=3))
        fig.update_xaxes(range=[row.cell_lon-10,row.cell_lon+10],dtick=5)
        fig.update_yaxes(range=[max(-90,row.cell_lat-10),min(90,row.cell_lat+10)],dtick=5)
        chart(fig,'grid_example')
    with right:
        st.metric(f'{region} · {year} target',str(target),help='1 means at least one M ≥ 6.0 event; 0 means none recorded.')
        st.metric('M ≥ 5.5 events in this cell-year',len(part))
        st.metric('M ≥ 6.0 events in this cell-year',int(part.mag.ge(6).sum()))
        st.write('Multiple strong events still produce **one positive annual observation**, matching the one-payment-per-year pricing assumption.')
    takeaway('A cell’s width shrinks with latitude. Regional probability is not a precise city probability; no recorded event does not prove zero hazard.')
    with st.expander('Population, zero years and grid boundaries'):
        st.write('The final 722-cell population had at least one M ≥ 5.5 event by 2015. The exploratory full-period preview contains 759 cells. '
                 'Earlier internal fitting sets are restricted to cells known by their cutoff. No-event years are retained, and future-only cells are excluded. '
                 'Cells have unequal areas and impose artificial borders. The highlighted box, not the city name, defines the target.')
    st.caption('Next: compute predictors from history before each target year.')


def features(data):
    explain('Summarize each cell’s recorded history before its target year.',
            'Recent and long-term activity may help rank annual occurrence probability without using the outcome being predicted.',
            'Recent counts, shallow share, capped time since a strong event and expanding rates form the verified predictors.')
    region=choose_region(data,'feature_region',default='35_135')
    year=st.slider('Prediction year t',1975,2025,2025,key='feature_year')
    history=data['features'].query('cell_id == @region and year == @year').iloc[0]
    events=data['events'].query('cell_id == @region')
    annual=events.groupby('year').agg(events=('id','size'),strong=('mag',lambda values:int(values.ge(6).sum())))
    annual=annual.reindex(range(1965,2026),fill_value=0)
    fig=go.Figure()
    fig.add_trace(go.Bar(x=annual.index,y=annual.events-annual.strong,name='5.5 ≤ M < 6.0',marker_color='#a7c7d9'))
    fig.add_trace(go.Bar(x=annual.index,y=annual.strong,name='M ≥ 6.0',marker_color='#147d72'))
    fig.add_vrect(x0=year-10-.5,x1=year-.5,fillcolor='#e6b34c',opacity=.17,line_width=0,
                  annotation_text='Previous ten years: predictors',annotation_position='top left')
    fig.add_vrect(x0=year-.5,x1=2025.5,fillcolor='#9ba4af',opacity=.12,line_width=0)
    fig.add_vline(x=year-.5,line_dash='dash',line_color='#a14d36')
    fig.update_layout(barmode='stack');fig.update_xaxes(title='Year',range=[1964.5,2025.5]);fig.update_yaxes(title='Recorded events')
    chart(style_figure(fig,'History stops before the prediction year',380),'feature_timeline')
    cols=st.columns(4)
    cols[0].metric('Events in previous 10 years',f'{history.n_events_prev10:.0f}')
    cols[1].metric('Strong events in previous 10 years',f'{history.n_strong_prev10:.0f}')
    cols[2].metric('Strong events / year since 1965',f'{history.strong_rate_longterm:.3f}')
    cols[3].metric('Observed target in year t',int(history.strong_quake))
    takeaway('Only bars before the dashed boundary enter predictors. The target and later years are displayed for context and excluded from those features.')
    with st.expander('Feature values, formulas and special cases'):
        rows=[('Recent event count',history.n_events_prev10,'Sum in t−10 … t−1'),
              ('Recent strong count',history.n_strong_prev10,'M ≥ 6.0 count in t−10 … t−1'),
              ('Maximum recent magnitude',history.max_mag_prev10,'5.0 is a placeholder if there were no events'),
              ('Events in previous year',history.n_events_prev1,'Count in t−1'),
              ('Years since strong event',history.years_since_strong,'11 means none in the previous ten years; capped'),
              ('Shallow share',history.share_shallow_prev10,'Fraction below 70 km; zero also denotes an empty window'),
              ('Long-term event rate',history.events_rate_longterm,'All preceding M ≥ 5.5 events / years since 1965'),
              ('Long-term strong rate',history.strong_rate_longterm,'All preceding M ≥ 6.0 events / years since 1965')]
        st.dataframe(pd.DataFrame(rows,columns=['Feature','Value','Definition']),hide_index=True)
        st.write('Logistic/Cloglog use log(1+x) for selected counts and rates and training-based standardization. '
                 'Trees use raw predictors. Shifted rolling/expanding calculations exclude target-year outcomes. '
                 'Mutation checks verified this boundary; they do not establish historical real-time availability of revised catalogue records.')
    st.caption('Next: choose and evaluate models in chronological order.')


def methods(data):
    explain('Compare interpretable regressions, trees and simple probability baselines using earlier years before later years.',
            'The main test is whether additional complexity improves on regional history, without future outcomes influencing earlier fitting.',
            'Feature selection is frozen on 1975–2005; 2006–2015 tunes cutoffs/CART size; refitted models score 2016–2025.')
    fig=go.Figure()
    for i,(name,start,end,color) in enumerate([('Internal fit / selection',1975,2006,'#3479c4'),
            ('Validation / tuning',2006,2016,'#dba84c'),('Exploratory evaluation',2016,2026,'#147d72')]):
        fig.add_trace(go.Bar(y=[name],x=[end-start],base=[start],orientation='h',marker_color=color,
                            text=f'{start}–{end-1}',textposition='inside',showlegend=False))
    fig.update_xaxes(range=[1974,2027],dtick=10,title='Calendar year');fig.update_layout(barmode='overlay')
    chart(style_figure(fig,height=250),'method_timeline')
    descriptions=[('Logistic','Smooth probability curve','Selected historical predictors; easy to summarize associations'),
                  ('Cloglog','Alternative probability curve','Allows an asymmetric link; not automatically a physical earthquake process'),
                  ('Random forest','Average of many trees','Nonlinear comparator; 300 trees with fixed seed'),
                  ('CART','Single rule tree','Readable regional classes; size tuned on validation Brier score'),
                  ('Historical rate','Smoothed annual frequency','Earlier positive years blended with pooled earlier history'),
                  ('Constant probability','Same fitting prevalence everywhere','Separates useful regional information from a global average')]
    st.dataframe(pd.DataFrame(descriptions,columns=['Approach','Simple explanation','Purpose']),hide_index=True)
    st.warning('All 2016–2025 results are exploratory: these years influenced prior refinement. '
               'Chronological discipline does not turn already inspected data into independent confirmation.')
    with st.expander('Selection, smoothing and annual updating'):
        st.markdown('**Regression selection:** backward AIC on internal fitting rows; BIC is also reported. '
                    'Scaling uses the relevant fitting set only. The final historical refit uses 1975–2015.\n\n'
                    '**Historical baseline:** (past positive years + 10 × pooled past frequency) / (past years + 10). '
                    'The ten pseudo-years stabilize rare histories and are an explicit fixed assumption.\n\n'
                    '**Annual updating:** 2020 predictors may use 2016–2019 observations, never 2020 or later. '
                    'The fixed-fit weights stay fixed after 2015. Rolling origins 2016/2021 refit using only preceding years '
                    'and evaluate disjoint five-year blocks. Neither is a fixed ten-year forecast issued in 2015.')
    st.caption('Next: compare ranking, probability error and calibration.')


def evaluation(data):
    explain('Measure ranking, probability error and agreement between predicted and observed frequencies.',
            'Premiums depend on probability levels, so high ROC-AUC alone is not sufficient.',
            'The historical-rate baseline beats Logistic, Cloglog and CART on AUC/Brier; Random Forest adds only a small gain.')
    a,b,c=st.columns(3)
    m=data['metrics'];a.metric('Best Brier · Random Forest',f'{m.loc["Random forest","brier"]:.5f}')
    b.metric('Historical baseline Brier',f'{m.loc["Historical rate","brier"]:.5f}')
    c.metric('Relative Brier gain over history',f'{100*(1-m.loc["Random forest","brier"]/m.loc["Historical rate","brier"]):.2f}%')
    perf,cal,roll,tree=st.tabs(['Model comparison','Probability calibration','Rolling origins','CART interpretation'])
    with perf:
        left,right=st.columns([1.2,1])
        with left:
            fig=go.Figure()
            for name,col in PROBABILITIES.items():
                x,y=roc_coordinates(data['predictions'].strong_quake,data['predictions'][col])
                fig.add_trace(go.Scatter(x=x,y=y,mode='lines',name=f'{name} · {m.loc[name,"roc_auc"]:.3f}',line=dict(color=COLORS[name],width=2)))
            fig.add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',line=dict(color='#a0acb9',dash='dash'),name='Constant / random ranking'))
            fig.update_xaxes(title='False positive rate',range=[0,1]);fig.update_yaxes(title='Recall / true positive rate',range=[0,1])
            chart(style_figure(fig,'Regional histories already rank well',460),'roc_live')
        with right:
            scores=m.sort_values('brier',ascending=False)
            fig=go.Figure(go.Bar(x=scores.brier,y=scores.index,orientation='h',marker_color=[COLORS[x] for x in scores.index]))
            fig.update_xaxes(title='Brier score · lower is better',range=[0,.105])
            chart(style_figure(fig,'Probability error',460),'brier_comparison')
        st.dataframe(m[['roc_auc','brier','f1','precision','recall','accuracy','threshold']].rename_axis('Model').reset_index(),hide_index=True)
        takeaway('Random Forest’s advantage over historical frequency is small and has not been shown statistically significant. Accuracy alone favors predicting no events.')
        with st.expander('Metric definitions and original-versus-revised evidence'):
            st.markdown('**ROC-AUC:** ranking across cutoffs; higher is better. **Brier:** mean squared probability error; lower is better. '
                        '**Precision:** positives among flagged rows. **Recall:** positives caught. **F1:** balance of precision and recall. '
                        'Cutoffs were chosen on validation data; they do not change premiums. Corrected selection retained the regression features; '
                        'Logistic cutoff changed 0.20→0.21 and Random Forest 0.24→0.25. AUC/Brier remain essentially unchanged at original precision.')
    with cal:
        selected=st.multiselect('Models on calibration chart',list(PROBABILITIES),default=['Logistic','Random forest','Historical rate'],key='calibration_models')
        fig=go.Figure(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Perfect agreement',line=dict(color='#9aa6b3',dash='dash')))
        for name in selected:
            part=data['calibration'][data['calibration'].model.eq(name)]
            fig.add_trace(go.Scatter(x=part.predicted,y=part.observed,mode='lines+markers',name=name,
                line=dict(color=COLORS[name]),marker=dict(size=8),
                error_y=dict(type='data',symmetric=False,array=(part.leave_year_out_max-part.observed).clip(lower=0),
                             arrayminus=(part.observed-part.leave_year_out_min).clip(lower=0),thickness=1,width=3),
                customdata=part[['region_years','positive_years','bin']],
                hovertemplate='%{fullData.name}<br>Predicted %{x:.2%}<br>Observed %{y:.2%}<br>n=%{customdata[0]}, positives=%{customdata[1]}<extra></extra>'))
        fig.update_xaxes(title='Mean predicted probability',tickformat='.0%',range=[0,1]);fig.update_yaxes(title='Observed frequency',tickformat='.0%',range=[0,1])
        chart(style_figure(fig,'Ranking is not the same as calibration',440),'calibration_live')
        takeaway('Logistic’s lowest bin predicts 2.03% versus 1.11% observed. Historical frequency underpredicts several high-risk bins; its top bin has just 17 rows.')
        st.caption('Above diagonal = underprediction; below = overprediction. Bars show leave-one-year-out sensitivity, not confidence intervals. Observations are dependent.')
        with st.expander('Bin counts and sensitivity ranges'):
            st.dataframe(data['calibration'][data['calibration'].model.isin(selected)],hide_index=True)
    with roll:
        folds=data['rolling_folds'];fig=go.Figure()
        for name in ['Random forest','Historical rate','Logistic']:
            part=folds[folds.model.eq(name)]
            fig.add_trace(go.Scatter(x=['2016–2020','2021–2025'],y=part.brier,mode='lines+markers',name=name,
                                    line=dict(color=COLORS[name]),marker=dict(size=10)))
        fig.update_xaxes(title='Evaluation block');fig.update_yaxes(title='Brier score · lower is better')
        chart(style_figure(fig,'Do conclusions depend on the fitting origin?',330),'rolling_brier')
        st.dataframe(data['rolling_metrics'][['roc_auc','brier','f1']].rename_axis('Model').reset_index(),hide_index=True)
        takeaway('The baseline slightly beats Random Forest in 2021–2025 (0.06181 vs 0.06187 Brier). There is no consistent large gain from complexity.')
        with st.expander('Fold results and interpretation'):
            st.dataframe(folds[['origin','model','threshold','roc_auc','brier','f1']],hide_index=True)
            st.write('Each origin repeats earlier-only fitting, selection and tuning. Baseline probabilities already update annually and are identical '
                     'across the two designs; cutoffs can change. Pooled constant-baseline AUC is 0.4872 because its constant changes between blocks; '
                     'within each block it is 0.5. These previously inspected years remain exploratory.')
    with tree:
        image('fig13_cart_tree.png','Historical CART fitted through 2015. Top levels shown; grey nodes summarize deeper branches.')
        takeaway('A tree converts histories into readable rules. Its full historical fit has 16 classes; importance and splits are associations, not causes.')
        st.caption('This historical tree differs from the later 2026 refit. The final class and rule for each quoted region appear in the calculator.')
        with st.expander('Final 2026 refit classes — distinct from historical evaluation classes'):
            st.dataframe(data['cart_classes'],hide_index=True)
    st.caption('Next: inspect the actual exported 2026 regional forecasts.')


def forecasts(data):
    explain('Inspect 2026 probabilities from models refitted on target years 1975–2025.',
            'The verified outputs turn an evaluated approach into an illustrative regional forecast using history ending in 2025.',
            'There are 722 supported regions. Only Logistic and CART have verified final forecasts exported for this walkthrough.')
    a,b=st.columns(2)
    with a:model=st.selectbox('Forecast model',['Logistic','CART'],key='forecast_model')
    with b:view=st.radio('Map colour',['Probability','Risk tier'],horizontal=True,key='forecast_view')
    region=choose_region(data,'forecast_region')
    chart(forecast_figure(data['forecasts'],data['boundaries'],model,region,view),'forecast_heatmap')
    st.caption('Pan, zoom and hover over actual 5° cells. The outlined cell is selected above. '
               'Blank = outside model scope, not zero hazard. Local plate boundaries; no online tiles. Probability colour scale is fixed at 0–100%.')
    col='p_logistic' if model=='Logistic' else 'p_cart';row=data['forecasts'].set_index('cell_id').loc[region]
    a,b,c=st.columns(3);a.metric(f'{model} · {region}',f'{row[col]:.2%}');b.metric('Regional probability tier',tier(row[col]))
    c.metric('Strong events / year since 1965',f'{row.strong_rate_longterm:.3f}')
    takeaway('The city name is a locator for a large region. A higher estimate from one model does not establish that it is more accurate.')
    with st.expander('Forecast scope, tiers and source'):
        st.write('Low: 0–2.5%; Moderate: >2.5–10%; High: >10–30%; Very high: >30%. '
                 'Models are refitted through 2025 and differ from historical evaluation fits. These are estimates as if issued at the start of 2026; '
                 'no 2026 outcome verification is included. Random Forest and the historical baseline have no exported final 2026 forecasts here; '
                 'historical evaluation probabilities are never substituted for forecasts.')
        st.dataframe(data['forecasts'][['cell_id','cell_lat','cell_lon','p_logistic','p_cart','cart_class']]
                     .sort_values(col,ascending=False),hide_index=True)
    st.caption('Next: convert a chosen regional probability into an illustrative fixed-payout premium.')


def insurance(data):
    explain('Price one fixed annual payout if at least one M ≥ 6.0 event occurs in the selected region.',
            'This makes the consequence of probability estimates transparent, including model disagreement.',
            'Premium = probability × payout ÷ target loss ratio. Changing cover or target changes price, not the earthquake probability.')
    region=choose_region(data,'pricing_region')
    a,b,c=st.columns([1,1.2,1.2])
    with a:model=st.selectbox('Pricing model',['Logistic','CART'],key='pricing_model')
    with b:payout=st.number_input('Fixed annual payout (EUR)',min_value=100.0,max_value=1_000_000_000.0,value=10_000_000.0,step=100_000.0,key='payout')
    with c:target=st.slider('Target loss ratio (%)',5,100,70,key='target_ratio')/100
    q=calculate_quote(data['forecasts'],data['factors'],region,model,payout,target)
    a,b,c,d=st.columns(4)
    a.metric('Annual regional probability',f'{q["probability"]:.2%}')
    b.metric('Expected fixed payout',f'€{q["expected_payout"]:,.0f}')
    c.metric('Illustrative annual premium',f'€{q["premium"]:,.0f}')
    d.metric('Premium / payout',f'{q["rate_on_line"]:.2%}')
    st.markdown(f'<div class="formula">{q["probability"]:.4%} × €{payout:,.0f} ÷ {target:.0%} ≈ '
                f'<b>€{q["premium"]:,.0f}</b> per year</div>',unsafe_allow_html=True)
    st.caption('Calculations use the full exported probability; displayed percentages and euros are rounded.')
    comparison=[calculate_quote(data['forecasts'],data['factors'],region,m,payout,target) for m in ['Logistic','CART']]
    a,b=st.columns([1,1])
    with a:
        fig=go.Figure(go.Bar(x=[x['model'] for x in comparison],y=[x['premium'] for x in comparison],
                            marker_color=[COLORS[x['model']] for x in comparison],text=[f'€{x["premium"]:,.0f}' for x in comparison],textposition='outside'))
        fig.update_yaxes(title='Illustrative premium (EUR)',range=[0,max(x['premium'] for x in comparison)*1.25])
        chart(style_figure(fig,'Same payout and target, different estimates',310),'premium_comparison')
    with b:
        st.markdown(f'### {q["risk_tier"]} regional tier')
        st.write(f'Target loss ratio **{target:.0%}** implies a loading of **{q["loading"]:.1%}** above expected payout.')
        if q['within_ceiling']:st.info('Within the project’s assumed 30% premium-to-payout ceiling. This does not establish commercial insurability.')
        else:st.warning('Above the project’s assumed 30% premium-to-payout ceiling. This is an illustrative design screen, not a market decision.')
        if model=='CART':st.markdown(f'**Final CART class {q["cart_class"]}**');st.caption(q['cart_rule'])
        diff=100*(comparison[1]['premium']/comparison[0]['premium']-1) if comparison[0]['premium'] else None
        if diff is not None:st.write(f'CART premium difference relative to Logistic: **{diff:+.1f}%**.')
    with st.expander('Historical tier diagnostic and optional experience adjustment'):
        st.write(f'The selected model’s historical tier loss ratio at this target is **{q["historical_tier_ratio"]:.1%}**. '
                 'It is a tier-level 2016–2025 diagnostic, not a location-specific backtest of this 2026 price.')
        adjusted=st.checkbox('Show illustrative experience-adjusted premium',key='show_adjustment')
        if adjusted:
            st.metric('Experience-adjusted premium',f'€{q["adjusted_premium"]:,.0f}')
            st.caption(f'Tier factor {q["factor"]:.3f}; credibility weight {q["credibility"]:.3f}. '
                       'Adjustment uses 2016–2025 outcomes, so those years cannot independently validate it.')
        st.markdown('Adjustment: `min(probability × tier factor, 0.999) × payout / target`. '
                    'The factor blends observed/predicted tier frequency toward 1 using `Z=min(1, √(positive years / 1082))`. '
                    'The credibility assumption is illustrative for dependent binary region-year data.')
    with st.expander('Check a coordinate — including unsupported regions'):
        a,b=st.columns(2)
        lat=a.number_input('Latitude',min_value=-90.,max_value=90.,value=50.11,key='coordinate_lat')
        lon=b.number_input('Longitude',min_value=-180.,max_value=180.,value=8.68,key='coordinate_lon')
        located=cell_id(lat,lon)
        if located in set(data['forecasts'].cell_id):
            st.success(f'Coordinate belongs to supported cell {located}. Choose that cell above to price it.')
        else:st.info(f'Cell {located} is outside model scope. No probability or premium is assigned; absent records do not establish zero hazard.')
    takeaway('One annual trigger, one fixed payment. Property damage, exposure, vulnerability, expenses, capital and correlated portfolio losses are not modeled.')
    st.caption('Next: return to the research question and what the evidence can support.')


def conclusions(data):
    explain('Bring together prediction, calibration and the pricing illustration.',
            'An academically defensible conclusion must reflect both the useful signal and the limits of the evidence.',
            'Regional history helps; extra model complexity adds little over the historical baseline, and probability estimates remain uncertain.')
    a,b=st.columns(2)
    with a:
        st.markdown('### What the results support')
        st.markdown('1. **Regional history provides useful ranking.** All fitted approaches beat a global constant on Brier score.\n'
                    '2. **The historical baseline is competitive.** Random Forest’s relative Brier gain is only 0.96%.\n'
                    '3. **Two rolling origins give broadly similar results.** The baseline slightly wins the second block.\n'
                    '4. **Calibration needs qualification.** Low-risk overprediction and sparse high-risk bins matter for prices.\n'
                    '5. **Pricing makes disagreement visible.** San Francisco: 2.35% Logistic vs 8.78% CART; neither is validated as correct.')
    with b:
        st.markdown('### What remains unresolved')
        st.markdown('- No untouched independent holdout; outcomes influenced earlier development.\n'
                    '- Catalogue revisions, mixed magnitude scales and unknown historical real-time availability.\n'
                    '- Spatial/temporal dependence; descriptive differences are not significance tests.\n'
                    '- Unequal-area 5° cells, arbitrary borders and excluded regions.\n'
                    '- Sparse rare-event evidence and unvalidated pricing/credibility assumptions.')
    image('fig12_loss_ratios.png','Existing notebook illustration: flat pricing hides large differences between tiers. Blue is the Logistic pricing example, not the best-scoring model.')
    takeaway('The useful result is a qualified research comparison, not exact earthquake prediction or a commercially validated premium.')
    with st.expander('Verified sources, run status and reproducibility'):
        st.write(f'Source notebook: **{data["manifest"]["source_notebook"]}**, with all {data["manifest"].get("executed_code_cells", data["validation"]["code_cells_executed"])} active code cells executed. '
                 'The supplied catalogue has 28,557 events rather than the original saved count of 28,558. '
                 'The one-record difference cannot be reconstructed from original summaries. '
                 'App exports reproduce all five golden location quotes for both models. The app never fits or retrains a model.')
        st.json({'raw_events':data['validation']['raw_events'],'regions':data['validation']['regions'],
                 'evaluation_rows':data['validation']['evaluation_rows'],'status':data['validation']['status'],
                 'golden_quote_check':data['manifest']['golden_quote_check']})
        st.caption('A future frozen protocol and genuinely unseen outcomes would be needed for independent confirmation. '
                   'The archived original analysis is preserved but is not used as current app evidence.')
        st.download_button('Download verified model comparison',data['metrics'].to_csv().encode(),
                           file_name='verified_model_comparison.csv',mime='text/csv')


RENDERERS=[overview,dataset,exploration,regions,features,methods,evaluation,forecasts,insurance,conclusions]


def move_stage(delta):
    st.session_state['stage']=max(0,min(9,st.session_state['stage']+delta))


def main():
    try:
        manifest=ASSETS/'export_manifest.json'
        data=project_data(manifest.stat().st_mtime_ns if manifest.exists() else 0)
    except (ArtifactError,FileNotFoundError,KeyError,ValueError) as error:
        st.title('Research walkthrough — data unavailable')
        st.error(str(error))
        st.info('Restore the supplied verified analysis artifacts. If only app exports are missing, run '
                '`python scripts/export_app_artifacts.py` once in the analysis environment. The app will not download data or train models automatically.')
        st.stop()
    if 'stage' not in st.session_state:st.session_state['stage']=0
    with st.sidebar:
        st.markdown('<div class="eyebrow">DATA ANALYTICS · GROUP PROJECT</div><div class="brand">Earthquake<br>Research Walkthrough</div>',unsafe_allow_html=True)
        st.caption('From recorded history to a qualified decision.')
        st.divider()
        st.radio('Research path',range(10),format_func=lambda i:f'{i+1:02d}  {SHORT_STAGES[i]}',key='stage')
        st.divider()
        st.markdown('**Verified results. Read-only app.**')
        st.caption('28,557 events · 722 regions\n\nExploratory evaluation, not independent confirmation.')
        with st.expander('Evidence source'):
            st.caption(data['manifest']['source_notebook'])
            st.caption('Revised analytical outputs + one-time verified forecast exports. No model fitting during app use.')
    stage=st.session_state['stage']
    st.markdown(f'<div class="eyebrow">RESEARCH WALKTHROUGH / STAGE {stage+1:02d}</div>',unsafe_allow_html=True)
    st.title(STAGES[stage])
    st.markdown('<span class="badge">M ≥ 6.0 annual target</span><span class="badge">5° regional grid</span>'
                '<span class="badge gold">Exploratory evidence</span>',unsafe_allow_html=True)
    st.progress((stage+1)/10,text=f'Stage {stage+1} of 10 · {SHORT_STAGES[stage]}')
    st.write('')
    RENDERERS[stage](data)
    st.divider()
    left,center,right=st.columns([1,2,1])
    left.button('← Previous',key='previous',disabled=stage==0,on_click=move_stage,args=(-1,),width='stretch')
    center.caption(f'{stage+1:02d} / 10'+(f'  ·  Next: {SHORT_STAGES[stage+1]}' if stage<9 else '  ·  Research walkthrough complete'))
    right.button('Next →',key='next',disabled=stage==9,on_click=move_stage,args=(1,),type='primary',width='stretch')


if __name__=='__main__':
    main()
