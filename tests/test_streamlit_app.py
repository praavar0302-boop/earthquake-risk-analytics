"""Behavioral and data-integrity tests. No fitting and no protected-file writes.
Run from project root: python -m pytest -q tests/test_streamlit_app.py
"""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app_support as support


@pytest.fixture(scope='module')
def data():
    return support.load_project()


def metric(app,label):
    return next(item.value for item in app.metric if item.label==label)


def clean(app):
    assert not app.exception,[x.message for x in app.exception]
    assert not app.error,[x.value for x in app.error]


def test_sources_and_golden_quotes(data):
    report=data['validation']
    assert len(data['events'])==report['raw_events']==28557
    assert len(data['forecasts'])==report['regions']==722
    assert data['manifest']['source_notebook']=='earthquake_risk_analysis.ipynb'
    for city,region in support.CITIES.items():
        report_name='Santiago' if city=='Santiago de Chile' else city
        for model in ['Logistic','CART']:
            q=support.calculate_quote(data['forecasts'],data['factors'],region,model,10_000_000,.7)
            assert round(q['premium'])==report['example_premiums_at_70_percent_target'][report_name][model]
            doubled=support.calculate_quote(data['forecasts'],data['factors'],region,model,20_000_000,.7)
            assert doubled['premium']==pytest.approx(q['premium']*2)
            assert q['premium']*.7==pytest.approx(q['expected_payout'])
            assert q['rate_on_line']==pytest.approx(q['probability']/.7)
    saved=pd.read_csv(support.REVISED/'risk_forecast_2026.csv').set_index('cell_id')
    exported=data['forecasts'].set_index('cell_id').loc[saved.index]
    np.testing.assert_allclose(exported.p_logistic,saved.probability,rtol=1e-12)
    for name,col in support.PROBABILITIES.items():
        p=data['predictions'][col];y=data['predictions'].strong_quake
        x,tpr=support.roc_coordinates(y,p)
        assert np.trapezoid(tpr,x)==pytest.approx(data['metrics'].loc[name,'roc_auc'],abs=1e-12)
        assert ((p-y)**2).mean()==pytest.approx(data['metrics'].loc[name,'brier'],abs=1e-12)


def test_coordinate_tiers_invalid_and_empty_cases(data):
    assert support.cell_id(90,180)=='85_-180'
    assert support.cell_id(37.77,-122.42)=='35_-125'
    assert support.cell_id(50.11,8.68)=='50_5'
    assert [support.tier(p) for p in [0,.025,.025001,.1,.10001,.3,.30001,1]]==[
        'Low','Low','Moderate','Moderate','High','High','Very high','Very high']
    with pytest.raises(ValueError,match='Latitude'):support.cell_id(91,0)
    for model,payout,target in [('Random forest',100,.7),('Logistic',0,.7),('Logistic',100,0)]:
        with pytest.raises(ValueError):support.calculate_quote(data['forecasts'],data['factors'],'35_-125',model,payout,target)
    with pytest.raises(ValueError,match='outside'):
        support.calculate_quote(data['forecasts'],data['factors'],'50_5','Logistic',100,.7)
    empty=support.filter_events(data['events'],(1965,1965),(9.1,9.1),(700,700))
    assert empty.empty
    fig,shown=support.earthquake_figure(empty,data['boundaries']);assert shown==0
    for model in ['Logistic','CART']:
        for view in ['Probability','Risk tier']:
            fig=support.forecast_figure(data['forecasts'],data['boundaries'],model,'35_-125',view)
            assert np.isfinite(np.asarray(fig.data[0].z)).sum()==722


def test_all_sections_navigation_and_no_training(data,monkeypatch):
    # The runtime must not import training code; a new cold app run is exercised.
    original_import=__import__
    def no_training_import(name,*args,**kwargs):
        if name.startswith(('sklearn','statsmodels','scripts.export_app_artifacts')):
            raise AssertionError(f'Runtime attempted training dependency: {name}')
        return original_import(name,*args,**kwargs)
    monkeypatch.setattr('builtins.__import__',no_training_import)
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=40).run()
    clean(app);assert app.session_state['stage']==0
    assert app.button(key='previous').disabled
    for stage in range(1,10):
        app.button(key='next').click().run();clean(app)
        assert app.session_state['stage']==stage
        assert app.title[0].value==support.STAGES[stage]
        assert app.sidebar.radio(key='stage').value==stage
        assert len(app.get('progress'))==1
    assert app.button(key='next').disabled
    app.button(key='previous').click().run();clean(app);assert app.session_state['stage']==8
    for stage in [3,6,1,9,0]:
        app.sidebar.radio(key='stage').set_value(stage).run();clean(app)
        assert app.title[0].value==support.STAGES[stage]


def test_explorer_filters_and_feature_timeline(data):
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=40).run()
    app.sidebar.radio(key='stage').set_value(2).run();clean(app)
    app.slider(key='eda_years').set_range(2010,2015)
    app.slider(key='eda_magnitudes').set_range(6.0,7.0)
    app.slider(key='eda_depths').set_range(0,100).run();clean(app)
    expected=support.filter_events(data['events'],(2010,2015),(6.,7.),(0,100))
    assert metric(app,'Events matching filters')==f'{len(expected):,}'
    app.slider(key='eda_years').set_range(1965,1965)
    app.slider(key='eda_magnitudes').set_range(9.1,9.1)
    app.slider(key='eda_depths').set_range(700,700).run();clean(app)
    assert metric(app,'Events matching filters')=='0'
    assert any('No recorded events' in x.value for x in app.info)
    app.sidebar.radio(key='stage').set_value(4).run()
    app.selectbox(key='feature_region').select('35_-125')
    app.slider(key='feature_year').set_value(2025).run();clean(app)
    feature=data['features'].query('cell_id == "35_-125" and year == 2025').iloc[0]
    assert metric(app,'Events in previous 10 years')==f'{feature.n_events_prev10:.0f}'
    assert metric(app,'Observed target in year t')==str(int(feature.strong_quake))


def test_model_calibration_and_forecast_controls(data):
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=40).run()
    app.sidebar.radio(key='stage').set_value(6).run();clean(app)
    assert metric(app,'Best Brier · Random Forest')=='0.06383'
    app.multiselect(key='calibration_models').set_value([]).run();clean(app)
    app.multiselect(key='calibration_models').set_value(list(support.PROBABILITIES)).run();clean(app)
    app.sidebar.radio(key='stage').set_value(7).run();clean(app)
    app.selectbox(key='forecast_model').select('CART')
    app.radio(key='forecast_view').set_value('Risk tier')
    app.selectbox(key='forecast_region').select('35_135').run();clean(app)
    expected=data['forecasts'].set_index('cell_id').loc['35_135','p_cart']
    assert metric(app,'CART · 35_135')==f'{expected:.2%}'


def test_pricing_widgets_and_unsupported_coordinate(data):
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=40).run()
    app.sidebar.radio(key='stage').set_value(8).run();clean(app)
    assert metric(app,'Illustrative annual premium')=='€335,739'
    app.selectbox(key='pricing_model').select('CART').run();clean(app)
    assert metric(app,'Illustrative annual premium')=='€1,254,206'
    app.selectbox(key='pricing_region').select('35_135')
    app.number_input(key='payout').set_value(25_000_000.)
    app.slider(key='target_ratio').set_value(65).run();clean(app)
    assert metric(app,'Illustrative annual premium')=='€10,936,583'
    app.checkbox(key='show_adjustment').check().run();clean(app)
    assert metric(app,'Experience-adjusted premium')=='€10,365,424'
    assert any('50_5 is outside' in x.value for x in app.info)
    app.number_input(key='coordinate_lat').set_value(37.77)
    app.number_input(key='coordinate_lon').set_value(-122.42).run();clean(app)
    assert any('supported cell 35_-125' in x.value for x in app.success)


def test_missing_exports_are_clear_without_mutating_files(monkeypatch,tmp_path):
    monkeypatch.setattr(support,'ASSETS',tmp_path)
    with pytest.raises(support.ArtifactError,match='exports are missing'):support.load_project()


def test_all_preexisting_analytical_files_unchanged():
    # The one-time export records the protected source fingerprints.
    manifest=json.loads((support.ASSETS/'export_manifest.json').read_text())
    for name,sha in manifest['source_hashes'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    backup=ROOT/'GroupProject_with_CART_v0.ipynb'
    if backup.exists():
        assert hashlib.sha256(backup.read_bytes()).hexdigest()=='e426bd0a3f974a44420a7605b83f0cb25c54b83be9907d2b095781537cde5218'


def test_missing_artifact_ui(monkeypatch):
    import streamlit as st
    st.cache_data.clear()
    def missing():
        raise support.ArtifactError('App forecast exports are missing. Run the one-time export.')
    monkeypatch.setattr(support,'load_project',missing)
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=40).run()
    assert not app.exception
    assert app.title[0].value=='Research walkthrough — data unavailable'
    assert any('exports are missing' in x.value for x in app.error)
    assert any('will not download data or train models' in x.value for x in app.info)
    st.cache_data.clear()
