"""Small check for directory grouping, scoped selection and private downloads."""
from reportlab.pdfgen import canvas
from test_v4 import env, headers
from test_v41 import own_import


def test_directory_topic_filter_and_private_resource_isolation(env):
    app, client, _, temp = env
    path = temp / 'contents.pdf'
    pdf = canvas.Canvas(str(path))
    pdf.drawString(40, 760, 'Contents')
    pdf.drawString(40, 720, '2.1 Systems and Center of Mass (questions 1-1) .... 1')
    pdf.drawString(40, 690, '2.2 Forces and Free-Body Diagrams (questions 2-2) .... 2')
    pdf.showPage()
    pdf.drawString(40, 760, 'Unit 2: Force and Translational Dynamics')
    for n in [1, 2]:
        y = 710 - (n - 1) * 240
        pdf.drawString(40, y, f'{n}. Choose the object described in the source.')
        for i, label in enumerate('ABCD'):
            pdf.drawString(40, y - 30 - i * 30, f'({label}) Object {i + 1}')
    pdf.save()
    paper = own_import(env, path)
    assert paper['summary']['mcq'] == 2
    assert paper['summary']['unclassified'] == 0
    course = app.state.bank.catalog['course_id']
    r = client.get('/api/v4/questions', headers=headers(), params={'course_id': course, 'unit_id': '2', 'topics': '2.2'})
    assert len(r.json()) == 1
    assert r.json()[0]['topics']['tag_source'] == 'source-directory'
    assert client.get('/api/v4/questions', headers=headers('other')).json() == []
    s = client.post('/api/v4/sessions', headers=headers(), json={'mode': 'practice', 'request_id': 'directory', 'course_id': course, 'unit_id': '2', 'topics': ['2.2'], 'count': 10})
    assert s.status_code == 200, s.text
    assert len(s.json()['questions']) == 1
    inventory = client.get('/api/v4/library', headers=headers()).json()
    other = client.get('/api/v4/library', headers=headers('other')).json()
    assert other['libraries'] == [] and inventory['namespace'] != other['namespace']
    book = inventory['libraries'][0]
    assert book['classified'] == 2 and book['question_count'] == 2
    assert 'correct_answer' not in str(inventory)
    for resource in book['resources']:
        assert client.get(resource['url'], headers=headers()).status_code == 200
        assert client.get(resource['url'], headers=headers('other')).status_code == 404
    assert client.get('/api/v4/library').status_code == 401
