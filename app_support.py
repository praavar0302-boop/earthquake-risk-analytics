"""Read-only data access and pure calculations for the research walkthrough.

No notebook execution, network requests or model fitting occur in this module.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
REVISED = ROOT / 'data/processed/revised'
ASSETS = ROOT / 'app_assets'
FIGURES = ROOT / 'figures/revised'
COLORS = {'Logistic':'#3479c4','Cloglog':'#e27746','Random forest':'#148b79',
          'CART':'#c89527','Historical rate':'#8263aa','Constant probability':'#8895a7'}
PROBABILITIES = {'Logistic':'p_logistic','Cloglog':'p_cloglog','Random forest':'p_random_forest',
                 'CART':'p_cart','Historical rate':'p_historical_rate'}
CITIES = {'San Francisco':'35_-125','Tokyo':'35_135','Istanbul':'40_25',
          'Santiago de Chile':'-35_-75','Kathmandu':'25_85'}
STAGES = ['Research Question & Overview','Dataset & Cleaning','Exploratory Data Analysis',
          'Regional Grid & Target','Feature Engineering','Models & Methodology',
          'Model Evaluation & Calibration','2026 Regional Forecasts',
          'Interactive Insurance Pricing','Findings & Limitations']
SHORT_STAGES = ['Research question','Dataset & cleaning','Explore the data','Regions & target',
                'History → features','Models & methodology','Evaluate & calibrate',
                '2026 forecasts','Insurance calculator','Findings & limitations']


class ArtifactError(ValueError):
    """Missing, mismatched or unsupported experiment artifacts."""


def load_project():
    manifest_path = ASSETS / 'export_manifest.json'
    if not manifest_path.exists():
        raise ArtifactError('App forecast exports are missing. Run: python scripts/export_app_artifacts.py')
    manifest = json.loads(manifest_path.read_text())
    for name, sha in manifest['source_hashes'].items():
        path = ROOT / name
        if not path.exists():
            raise ArtifactError(f'Required verified source is missing: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ArtifactError(f'Source changed since export: {name}. Review the analysis before regenerating exports.')
    for name, sha in manifest['export_hashes'].items():
        path = ASSETS / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ArtifactError(f'App export is missing or changed: app_assets/{name}. Regenerate the one-time export.')
    files = {'events':'earthquakes_clean.csv','features':'region_year_features.csv',
             'metrics':'fixed_fit_metrics_with_cart.csv','predictions':'test_predictions.csv',
             'calibration':'calibration_fixed_fit.csv','rolling_metrics':'rolling_origin_metrics.csv',
             'rolling_folds':'rolling_origin_fold_metrics.csv','rolling_calibration':'calibration_rolling_origin.csv'}
    data = {}
    for key, filename in files.items():
        path = REVISED / filename
        if not path.exists():
            raise ArtifactError(f'Required analysis artifact missing: {path.relative_to(ROOT)}')
        data[key] = pd.read_csv(path, index_col=0 if key in ['metrics','rolling_metrics'] else None)
    data['events']['time'] = pd.to_datetime(data['events']['time'],utc=True,format='ISO8601')
    data['events'] = assign_cells(data['events'])
    data['forecasts'] = pd.read_csv(ASSETS/'forecasts_2026.csv')
    data['factors'] = pd.read_csv(ASSETS/'experience_factors.csv')
    data['cart_classes'] = pd.read_csv(ASSETS/'cart_classes_2026.csv')
    data['manifest'] = manifest
    data['validation'] = json.loads((REVISED/'real_data_validation_report.json').read_text())
    data['raw_quality'] = (pd.read_csv(ROOT/'data/raw/usgs_earthquakes_1965_2025_m5.5.csv')
                           .isna().mean().mul(100).sort_values(ascending=False))
    geo = json.loads((ROOT/'data/external/plate_boundaries_pb2002.json').read_text())
    xs,ys=[],[]
    for feature in geo['features']:
        coords=np.asarray(feature['geometry']['coordinates'],dtype=float)
        for i,(x,y) in enumerate(coords):
            if i and abs(x-coords[i-1,0])>180:
                xs.append(None);ys.append(None)
            xs.append(float(x));ys.append(float(y))
        xs.append(None);ys.append(None)
    data['boundaries']=(xs,ys)
    f=data['forecasts']
    if len(f)!=data['validation']['regions'] or f.cell_id.duplicated().any():
        raise ArtifactError('Forecast population does not match the validation report.')
    if not f[['p_logistic','p_cart']].apply(lambda col:col.between(0,1).all()).all():
        raise ArtifactError('Invalid forecast probability; app stopped.')
    return data


def assign_cells(events):
    result=events.copy()
    lat=np.floor(result.latitude.astype(float).clip(upper=np.nextafter(90.,-np.inf))/5)*5
    lon=np.floor(((result.longitude+180)%360-180)/5)*5
    result['cell_id']=lat.astype(int).astype(str)+'_'+lon.astype(int).astype(str)
    return result


def cell_id(latitude,longitude):
    if not (-90<=latitude<=90 and -180<=longitude<=180):
        raise ValueError('Latitude must be in [−90,90] and longitude in [−180,180].')
    latitude=min(latitude,np.nextafter(90.,-np.inf));longitude=(longitude+180)%360-180
    return f'{int(np.floor(latitude/5)*5)}_{int(np.floor(longitude/5)*5)}'


def tier(probability):
    return ['Low','Moderate','High','Very high'][int(np.searchsorted([.025,.10,.30],probability,side='left'))]


def filter_events(events,years,magnitudes,depths):
    return events[events.year.between(*years)&events.mag.between(*magnitudes)&events.depth.between(*depths)]


def roc_coordinates(target,probability):
    target=np.asarray(target,dtype=int);probability=np.asarray(probability,dtype=float)
    if len(target)==0 or len(np.unique(target))!=2:
        raise ValueError('ROC requires both outcome classes.')
    order=np.argsort(-probability,kind='stable');y=target[order];p=probability[order]
    ends=np.r_[np.flatnonzero(np.diff(p)),len(p)-1]
    tp=np.cumsum(y)[ends];fp=(ends+1)-tp
    return np.r_[0,fp/(len(y)-y.sum())],np.r_[0,tp/y.sum()]


def calculate_quote(forecasts,factors,region,model,payout,target_loss_ratio):
    if model not in ['Logistic','CART']:
        raise ValueError('Only verified Logistic and CART 2026 forecasts are exported.')
    if not np.isfinite(payout) or payout<=0 or not 0<target_loss_ratio<=1:
        raise ValueError('Payout must be positive and target loss ratio must be in (0,1].')
    match=forecasts[forecasts.cell_id.eq(region)]
    if match.empty:
        raise ValueError('Region is outside the verified forecast population; no probability or price is assigned.')
    row=match.iloc[0];p=float(row['p_logistic' if model=='Logistic' else 'p_cart'])
    risk=tier(p)
    experience=factors[factors.model.eq(model)&factors.risk_tier.eq(risk)].iloc[0]
    expected=p*payout;premium=expected/target_loss_ratio
    return {'region':region,'model':model,'probability':p,'risk_tier':risk,
            'expected_payout':expected,'premium':premium,'rate_on_line':premium/payout,
            'target_loss_ratio':target_loss_ratio,'loading':1/target_loss_ratio-1,
            'within_ceiling':premium/payout<=.30,'factor':float(experience.factor),
            'credibility':float(experience.credibility),
            'adjusted_premium':min(p*experience.factor,.999)*payout/target_loss_ratio,
            'historical_tier_ratio':target_loss_ratio*experience.observed_to_predicted,
            'cart_class':row.cart_class if model=='CART' else '',
            'cart_rule':row.cart_rule if model=='CART' else ''}


def style_figure(fig,title=None,height=420):
    fig.update_layout(template='plotly_white',height=height,margin=dict(l=25,r=25,t=55 if title else 20,b=35),
                      title=dict(text=title,font=dict(size=18,color='#14283e')) if title else None,
                      font=dict(family='Arial, sans-serif',size=13,color='#34465a'),
                      paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='#ffffff',
                      legend=dict(orientation='h',y=-.20,x=0,title=None),
                      hoverlabel=dict(bgcolor='white',font_size=13))
    fig.update_xaxes(gridcolor='#e9edf2',zeroline=False)
    fig.update_yaxes(gridcolor='#e9edf2',zeroline=False)
    return fig


def geographic_figure(boundaries):
    fig=go.Figure(go.Scattergl(x=boundaries[0],y=boundaries[1],mode='lines',
          line=dict(color='#c8d4dd',width=1),hoverinfo='skip',showlegend=False))
    style_figure(fig,height=440)
    fig.update_xaxes(title='Longitude',range=[-180,180],dtick=60)
    fig.update_yaxes(title='Latitude',range=[-90,90],dtick=30)
    return fig


def earthquake_figure(events,boundaries,max_points=8000):
    displayed=events.sample(max_points,random_state=42) if len(events)>max_points else events
    fig=geographic_figure(boundaries)
    colors={'shallow':'#54a1cb','intermediate':'#2375a0','deep':'#123d68'}
    for depth in ['shallow','intermediate','deep']:
        part=displayed[displayed.depth_class.eq(depth)]
        fig.add_trace(go.Scattergl(x=part.longitude,y=part.latitude,mode='markers',name=depth.title(),
            marker=dict(color=colors[depth],size=3+(part.mag-5.5)*3,opacity=.65),
            customdata=np.column_stack([part.mag,part.depth,part.time.dt.strftime('%Y-%m-%d'),part.place]),
            hovertemplate='%{customdata[3]}<br>%{customdata[2]} · M %{customdata[0]:.2f}<br>Depth %{customdata[1]:.1f} km<extra></extra>'))
    return fig,len(displayed)


def forecast_figure(forecasts,boundaries,model,selected,view='Probability'):
    col='p_logistic' if model=='Logistic' else 'p_cart'
    lat=np.arange(-87.5,90,5);lon=np.arange(-177.5,180,5)
    z=np.full((36,72),np.nan);custom=np.full((36,72,3),'',dtype=object)
    for row in forecasts.itertuples():
        y=int((row.cell_lat+87.5)/5);x=int((row.cell_lon+177.5)/5);p=getattr(row,col)
        z[y,x]=p if view=='Probability' else ['Low','Moderate','High','Very high'].index(tier(p))
        custom[y,x]=[row.cell_id,f'{p:.2%}',tier(p)]
    fig=go.Figure()
    if view=='Probability':
        colorscale=[[0,'#eaf5f0'],[.15,'#9dcfbe'],[.45,'#3c9b89'],[1,'#104c49']]
        colorbar=dict(title='Annual P',tickformat='.0%');maximum=1
    else:
        colorscale=[[0,'#e3efe8'],[.2499,'#e3efe8'],[.25,'#8bc6b4'],[.4999,'#8bc6b4'],
                    [.5,'#e6ad61'],[.7499,'#e6ad61'],[.75,'#b25842'],[1,'#b25842']]
        colorbar=dict(title='Tier',tickvals=[0,1,2,3],ticktext=['Low','Moderate','High','Very high']);maximum=3
    fig.add_trace(go.Heatmap(x=lon,y=lat,z=z,customdata=custom,zmin=0,zmax=maximum,
        colorscale=colorscale,colorbar=colorbar,xgap=1,ygap=1,hoverongaps=False,
        hovertemplate='Cell %{customdata[0]}<br>%{customdata[1]} annual probability<br>%{customdata[2]} tier<extra></extra>'))
    fig.add_trace(go.Scattergl(x=boundaries[0],y=boundaries[1],mode='lines',
        line=dict(color='rgba(87,111,132,.35)',width=.7),hoverinfo='skip',showlegend=False))
    row=forecasts[forecasts.cell_id.eq(selected)].iloc[0]
    fig.add_shape(type='rect',x0=row.cell_lon-2.5,x1=row.cell_lon+2.5,
                  y0=row.cell_lat-2.5,y1=row.cell_lat+2.5,line=dict(color='#162c43',width=3))
    fig.add_trace(go.Scattergl(x=[row.cell_lon],y=[row.cell_lat],mode='markers',
        marker=dict(size=7,color='#162c43',symbol='x'),hoverinfo='skip',showlegend=False))
    style_figure(fig,height=480)
    fig.update_xaxes(title='Longitude',range=[-180,180],dtick=60)
    fig.update_yaxes(title='Latitude',range=[-90,90],dtick=30)
    return fig
