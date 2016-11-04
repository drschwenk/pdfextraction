import jinja2
import os

j2env = jinja2.Environment()

default_page_html = """
<!DOCTYPE html>
<html>
  <head>
    <style type="text/css">
       .container {
            max-width: 800px;
          }
    </style>
  </head>
  <body style=max-width: 100px>
    <div class="container">
      <h1>Lesson: {{lesson}}</h1>
      <ul>
        {% for topic in topics %}
        <p>
        </p>
        <h3>{{topic.0}}</h3>
        <p>{{topic.1}}</p>
        {% endfor %}
      </ul>
    </div>
    <script src="http://code.jquery.com/jquery-1.10.2.min.js"></script>
    <script src="http://netdna.bootstrapcdn.com/bootstrap/3.0.0/js/bootstrap.min.js"></script>
  </body>
</html>
"""

diagram_page_html = """
<!DOCTYPE html>
<html>
  <head>
    <style type="text/css">
       .container {
          }
    </style>
  </head>
  <body style=max-width: 100px>
    <div class="container">
      <h1>Lesson: {{lesson}}</h1>
      <ul>
        {% for topic in topics %}
        <p>
        </p>
        <p>{{topic}}</p>
        {% endfor %}
      </ul>
    </div>
    <script src="http://code.jquery.com/jquery-1.10.2.min.js"></script>
    <script src="http://netdna.bootstrapcdn.com/bootstrap/3.0.0/js/bootstrap.min.js"></script>
  </body>
</html>
"""


def make_lesson_data(lesson_json, rel_html_out_path=None):
    nested_text = []
    for topic, content in sorted(lesson_json['topics'].items(), key=lambda (k, v): v['globalID']):
        nested_text.append((content['topicName'], content['content']['text']))
        if content['content']['figures']:
            for figure in content['content']['figures']:
                image_link = '<img src="' + '../../' + figure['imagePath'] + '" width=500px>'
                image_caption = figure['caption']
                nested_text.append(('', image_link))
                nested_text.append(('', image_caption))
    return nested_text


def make_lesson_wq_data(lesson_json, rel_html_out_path):
    nested_text = []
    for question in sorted(lesson_json['questions']['diagramQuestions'].values(), key=lambda x: x['globalID']):
        image_link = '<img src="' + '../../' + question['imagePath'] + '" width=500px>'
        nested_text.append(image_link)
        nested_text.append(question['globalID'])
        being_asked = question['beingAsked']['processedText']
        nested_text.append(being_asked)
        for ac in sorted(question['answerChoices'].values(), key=lambda x: x['idStructural']):
            if ac['processedText'] == question['correctAnswer']['processedText']:
                nested_text.append('<font color="red"> ' + ' '.join([' ', ac['idStructural'], ac['processedText']]) + '</font>')
            else:
                nested_text.append(' '.join([' ', ac['idStructural'], ac['processedText']]))
        nested_text.append('')
    return nested_text


def make_lesson_diagram_description_data(lesson_json, rel_html_out_path):
    nested_text = []
    for description in sorted(lesson_json['instructionalDiagrams'].values()):
        image_link = '<img src="' + '../../' + description['imagePath'] + '" width=500px>'
        nested_text.append(image_link)
        nested_text.append(description['imageName'])
        being_asked = description['processedText']
        nested_text.append(being_asked)
        nested_text.append('')
    return nested_text


def make_page_html(lesson_data, page_html):
    return j2env.from_string(page_html).render(lesson=lesson_data[0], topics=lesson_data[1])


def display_lesson_html(lesson_json, lesson, page_type=None, html_output_dir=None):
    if not page_type or page_type == 'lessons':
        lesson_data = (lesson, make_lesson_data(lesson_json, html_output_dir))
        page_html = default_page_html
    elif page_type == 'questions':
        lesson_data = (lesson, make_lesson_wq_data(lesson_json, html_output_dir))
        page_html = diagram_page_html
    elif page_type == 'descriptions':
        lesson_data = (lesson, make_lesson_diagram_description_data(lesson_json, html_output_dir))
        page_html = diagram_page_html
    lesson_html = make_page_html(lesson_data, page_html)
    return lesson_html
    # return HTML(lesson_html)


def make_lesson_html(flexbook, lesson, page_html=default_page_html):
    lesson_json = flexbook[lesson]
    lesson_data = (lesson, make_lesson_data(lesson_json))
    lesson_html = make_page_html(lesson_data, page_html)
    return lesson_html

