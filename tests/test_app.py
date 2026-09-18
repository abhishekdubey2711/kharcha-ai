"""HTTP integration tests against real SQLite files, not mocked databases."""
from datetime import date
import sqlite3
import pytest
from kharcha import create_app
from kharcha.db import get_db

@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.sqlite'),'SECRET_KEY':'test-only-key','GEMINI_API_KEY':None})

def headers(client):
    client.get('/login')
    with client.session_transaction() as session:
        return {'X-CSRF-Token':session['csrf_token']}

def register(client,email='one@example.test'):
    response=client.post('/register',data={'name':'Test User','email':email,'password':'test-password-123'},headers=headers(client))
    assert response.status_code==302
    return headers(client)

@pytest.fixture
def client(app):
    client=app.test_client()
    register(client)
    return client

def record(**changes):
    data={'kind':'expense','amount':'180.25','category_id':1,'description':'Coffee','date':date.today().isoformat(),'payment_method':'UPI','notes':''}
    data.update(changes)
    return data

def add(client,**changes):
    return client.post('/api/transactions',json=record(**changes),headers=headers(client))

def test_crud_summary(client):
    response=add(client)
    assert response.status_code==201
    transaction=response.json['transaction']
    assert transaction['amount_paise']==18025
    ident=transaction['id']
    assert client.get(f'/api/transactions/{ident}').json['transaction']['description']=='Coffee'
    response=client.put(f'/api/transactions/{ident}',json=record(amount='200.10'),headers=headers(client))
    assert response.json['transaction']['amount_paise']==20010
    assert add(client,kind='income',category_id=10,amount='500.20').status_code==201
    summary=client.get('/api/summary').json
    assert summary['net_paise']==30010 and summary['expense_paise']==20010
    assert client.delete(f'/api/transactions/{ident}',headers=headers(client)).status_code==204
    assert client.get(f'/api/transactions/{ident}').status_code==404

@pytest.mark.parametrize('change',[
    {'amount':'0'},{'amount':'-1'},{'amount':'1.001'},{'amount':'NaN'},{'amount':'Infinity'},
    {'amount':True},{'amount':'1000000000.01'},{'category_id':9},{'category_id':True},{'category_id':'1'},
    {'date':'2026-02-30'},{'date':'2026-2-3'},{'date':None},{'description':''},{'description':' '},
    {'description':'x'*121},{'notes':'x'*501},{'payment_method':'Crypto'},{'kind':'refund'}])
def test_invalid_record(client,change):
    assert add(client,**change).status_code==400
    assert client.get('/api/transactions').json['total']==0

def test_isolation(app,client):
    ident=add(client).json['transaction']['id']
    other=app.test_client()
    token=register(other,'two@example.test')
    assert other.get('/api/transactions').json['total']==0
    assert other.get('/api/summary').json['expense_paise']==0
    assert other.get(f'/api/transactions/{ident}').status_code==404
    assert other.put(f'/api/transactions/{ident}',json=record(),headers=token).status_code==404
    assert other.delete(f'/api/transactions/{ident}',headers=token).status_code==404
    assert 'Coffee' not in other.get('/api/export').text
    assert client.get(f'/api/transactions/{ident}').status_code==200

def test_auth_csrf_hash(app):
    client=app.test_client()
    assert client.get('/api/transactions').status_code==401
    assert client.get('/').location.endswith('/login')
    assert client.post('/register',data={}).status_code==403
    register(client)
    assert client.post('/api/transactions',json=record()).status_code==403
    assert client.post('/api/transactions',json=record(),headers={'X-CSRF-Token':'é'}).status_code==403
    with app.app_context():
        stored=get_db().execute('SELECT password_hash FROM users').fetchone()[0]
        assert stored.startswith('scrypt:') and stored!='test-password-123'
    assert client.post('/logout',headers=headers(client)).status_code==302
    assert client.get('/api/transactions').status_code==401
    assert client.post('/login',data={'email':'one@example.test','password':'test-password-123'},headers=headers(client)).status_code==302

def test_filters_pagination_csv(client):
    add(client,description='Lunch',amount='12.30',date='2026-01-01')
    add(client,description='Cab',category_id=2,date='2026-02-01')
    add(client,description='=HYPERLINK(1)',notes='+formula',date='2026-01-02')
    add(client,kind='income',category_id=9,description='Salary',date='2026-01-03')
    assert client.get('/api/transactions?month=2026-01').json['total']==3
    assert client.get('/api/transactions?kind=income').json['total']==1
    assert client.get('/api/transactions?category_id=2').json['total']==1
    assert client.get('/api/transactions?q=lunch').json['total']==1
    assert client.get('/api/transactions?per_page=2&page=2').json['transactions'][0]['description'].startswith('=')
    assert client.get('/api/transactions?q=%27%20OR%201=1--').json['total']==0
    csv=client.get('/api/export?month=2026-01')
    assert "'=HYPERLINK(1)" in csv.text and "'+formula" in csv.text
    assert 'Cab' not in csv.text and '12.30' in csv.text

@pytest.mark.parametrize('query',['month=bad','month=2026-13','page=0','page=x','per_page=101','kind=wrong','category_id=x'])
def test_invalid_filters(client,query):
    assert client.get('/api/transactions?'+query).status_code==400

def test_restart_persistence(app,client):
    ident=add(client).json['transaction']['id']
    restarted=create_app({'TESTING':True,'DATABASE':app.config['DATABASE'],'SECRET_KEY':'test-only-key'})
    with restarted.app_context():
        assert get_db().execute('SELECT amount_paise FROM transactions WHERE id=?',(ident,)).fetchone()[0]==18025

def test_db_constraint(app,client):
    with app.app_context():
        with pytest.raises(sqlite3.IntegrityError):
            get_db().execute("INSERT INTO transactions(user_id,kind,amount_paise,category_id,description,date,payment_method) VALUES (1,'expense',100,9,'bad','2026-01-01','UPI')")

def test_draft_only(client):
    response=client.post('/api/parse',json={'text':'Spent ₹180 on coffee yesterday'},headers=headers(client))
    assert response.status_code==200 and response.json['source']=='local'
    assert response.json['draft']['amount']=='180' and response.json['draft']['category_id']==1
    assert client.get('/api/transactions').json['total']==0
    response=client.post('/api/parse',json={'text':'Received 4500 from freelance work on 2026-09-01'},headers=headers(client))
    assert response.json['draft']['kind']=='income' and response.json['draft']['date']=='2026-09-01'

@pytest.mark.parametrize('text',['coffee','Spent 10 and 20 on lunch','Spent -50 on food','Spent 50 last week','Spent 10 on 2026-02-30'])
def test_ambiguous_parser(client,text):
    assert client.post('/api/parse',json={'text':text},headers=headers(client)).status_code==400

def test_provider_fallback(app,client,monkeypatch):
    from kharcha import smart_entry
    app.config['GEMINI_API_KEY']='fake-test-key'
    def fail(_):
        raise TimeoutError('private-provider-error')
    monkeypatch.setattr(smart_entry,'gemini_parse',fail)
    response=client.post('/api/parse',json={'text':'Paid 25 for chai'},headers=headers(client))
    assert response.status_code==200 and response.json['source']=='local'
    assert 'private-provider-error' not in response.text

def test_demo_isolation_no_provider(app,monkeypatch):
    from kharcha import smart_entry
    app.config['GEMINI_API_KEY']='fake-test-key'
    def fail(_):
        pytest.fail('Public demo must not call the paid provider')
    monkeypatch.setattr(smart_entry,'gemini_parse',fail)
    first,second=app.test_client(),app.test_client()
    for client in (first,second):
        assert client.post('/demo',headers=headers(client)).status_code==302
    ident=first.get('/api/transactions').json['transactions'][0]['id']
    assert second.get(f'/api/transactions/{ident}').status_code==404
    assert first.post('/api/parse',json={'text':'Spent 10 on chai'},headers=headers(first)).json['source']=='local'

def test_health_month_boundary(client):
    assert client.get('/health').json=={'status':'ok'}
    assert "script-src 'self'" in client.get('/').headers['Content-Security-Policy']
    add(client,amount='1',date='2025-12-31')
    add(client,amount='2',date='2026-01-01')
    assert client.get('/api/summary?month=2025-12').json['expense_paise']==100
    assert client.get('/api/summary?month=2026-01').json['expense_paise']==200
