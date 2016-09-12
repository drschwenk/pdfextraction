import jinja2
from IPython.core.display import HTML

jnjenv = jinja2.Environment()

default_page_html = """
<!DOCTYPE html>
<html>
  <head>
    <style type="text/css">
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Lesson: {{lesson}}</h1>
      <ul>
        {% for topic in topics %}
        <p>
        </p>
        <h3>{{topic.0}}</h3>
        <p>{{
        topic.1
        }}</p>
        {% endfor %}
      </ul>
    </div>
    <script src="http://code.jquery.com/jquery-1.10.2.min.js"></script>
    <script src="http://netdna.bootstrapcdn.com/bootstrap/3.0.0/js/bootstrap.min.js"></script>
  </body>
</html>
"""

def make_lesson_data(lesson_json):
    nested_text = []    
    for topic, content in sorted(lesson_json['topics'].items(), key=lambda (k,v): v['orderID']):
        nested_text.append((topic, content['content']['text']))
    return nested_text

def make_page_html(lesson_data, page_html):
    return jnjenv.from_string(page_html).render(lesson=lesson_data[0], topics=lesson_data[1])

def display_lesson_html(flexbook, lesson, page_html=default_page_html):
    lesson_json = flexbook[lesson]
    lesson_data = (lesson, make_lesson_data(lesson_json))
    lesson_html = make_page_html(lesson_data, page_html)
    return HTML(lesson_html)

default_page_html = """
<!DOCTYPE html>
<html>
  <head>
    <style type="text/css">
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Lesson: {{lesson}}</h1>
      <ul>
        {% for topic in topics %}
        <p>
        </p>
        <h3>{{topic.0}}</h3>
        <p>{{
        topic.1
        }}</p>
        {% endfor %}
      </ul>
    </div>
    <script src="http://code.jquery.com/jquery-1.10.2.min.js"></script>
    <script src="http://netdna.bootstrapcdn.com/bootstrap/3.0.0/js/bootstrap.min.js"></script>
  </body>
</html>
"""
